# app/services/experiment.py
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..models.experiment import ExperimentCreate, ExperimentUpdate, ExperimentStatus
from ..db.dynamodb import dynamodb_client
from ..db.redis import redis_client
from ..services.statistics import statistics_service

logger = logging.getLogger(__name__)

class ExperimentService:
    @staticmethod
    async def create_experiment(experiment_data: Dict) -> Dict:
        """Create a new experiment using name as the primary identifier"""
        # Add timestamps
        now = datetime.utcnow()
        experiment = {
            **experiment_data,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        # Save to database
        created_experiment = await dynamodb_client.create_experiment(experiment)
        
        # Add to cache
        await redis_client.set_experiment(experiment_data["name"], created_experiment)
        
        return created_experiment
    
    @staticmethod
    async def get_experiment(name: str) -> Optional[Dict]:
        """Get experiment by name with caching"""
        # Try to get from cache first
        cached_experiment = await redis_client.get_experiment(name)
        if cached_experiment:
            logger.debug(f"Cache hit for experiment: {name}")
            return cached_experiment
            
        # If not in cache, try to get from database
        db_experiment = await dynamodb_client.get_experiment(name)
        if db_experiment:
            logger.debug(f"Database hit for experiment: {name}")
            # Refresh cache
            await redis_client.set_experiment(name, db_experiment)
            return db_experiment
            
        # No experiment exists
        return None
    
    @staticmethod
    async def update_experiment(name: str, update_data: Dict) -> Dict:
        """Update an experiment"""
        # Check if the experiment exists
        existing = await ExperimentService.get_experiment(name)
        if not existing:
            raise ValueError(f"Experiment '{name}' not found")
            
        # Update the experiment
        updated_experiment = await dynamodb_client.update_experiment(name, update_data)
        
        # Clear from cache to force a refresh
        await redis_client.delete_experiment_cache(name)
        
        return updated_experiment
    
    @staticmethod
    async def delete_experiment(name: str) -> bool:
        """Delete an experiment"""
        # Delete from database
        success = await dynamodb_client.delete_experiment(name)
        
        # Clear from cache
        await redis_client.delete_experiment_cache(name)
        
        return success
    
    @staticmethod
    async def list_experiments(status: Optional[str] = None) -> List[Dict]:
        """List all experiments, optionally filtered by status"""
        return await dynamodb_client.list_experiments(status)
    
    @staticmethod
    async def update_experiment_status(name: str, status: ExperimentStatus) -> Dict:
        """Update experiment status (consolidated status endpoint)"""
        return await ExperimentService.update_experiment(
            name, 
            {"status": status.value}
        )
    
    @staticmethod
    async def get_experiment_stats(
        experiment_name: str,
        event_types: Optional[List[str]] = None,
        include_assignments: bool = True,
        include_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        Get comprehensive experiment statistics by variant with statistical analysis
        
        Parameters:
            experiment_name: The experiment name (which is also the experiment_id)
            event_types: Optional list of event types to include
            include_assignments: Whether to include assignment counts (default: True)
            include_analysis: Whether to include statistical analysis (default: True)
        """
        # Get the experiment to know the variants
        experiment = await ExperimentService.get_experiment(experiment_name)
        if not experiment:
            raise ValueError(f"Experiment '{experiment_name}' not found")
            
        variants = experiment.get("variants", [])
        variant_names = [v["name"] for v in variants]
        
        # Find control variant
        control_variant = next((v["name"] for v in variants if v.get("is_control", False)), variant_names[0] if variant_names else None)
        
        # Initialize result structure
        results = {
            "variants": {variant: {} for variant in variant_names},
            "control_variant": control_variant,
            "metadata": {
                "base_rate": experiment.get("base_rate"),
                "min_detectable_effect": experiment.get("min_detectable_effect"),
                "min_sample_size_per_group": experiment.get("min_sample_size_per_group"),
                "confidence_level": experiment.get("confidence_level", 0.95)
            }
        }
        
        # Default event types if not specified
        if event_types is None:
            event_types = ["impression", "conversion"]
            
        # Get counts for each event type
        for event_type in event_types:
            counts = await dynamodb_client.get_event_counts_by_variant(
                experiment_id=experiment_name,
                event_type=event_type
            )
            
            # Update results with actual counts (not zeros for empty counts)
            for variant, count in counts.items():
                if variant in results["variants"]:
                    results["variants"][variant][event_type] = count
        
        # Add assignment counts if requested
        if include_assignments:
            assignment_counts = await dynamodb_client.get_assignment_counts_by_variant(experiment_name)
            
            # Update results with assignment counts
            for variant, count in assignment_counts.items():
                if variant in results["variants"]:
                    results["variants"][variant]["assignments"] = count
                    
        # Add population info if available in the experiment
        if "total_population" in experiment and experiment["total_population"]:
            total_population = experiment["total_population"]
            results["metadata"]["total_population"] = total_population
        
        # Ensure all variants have at least zero counts for all event types
        for variant in results["variants"]:
            for event_type in event_types:
                if event_type not in results["variants"][variant]:
                    results["variants"][variant][event_type] = 0
            if include_assignments and "assignments" not in results["variants"][variant]:
                results["variants"][variant]["assignments"] = 0
        
        # Calculate statistical significance if requested
        if include_analysis:
            # We need at least conversions and impressions to do statistical analysis
            if "conversion" in event_types and "impression" in event_types:
                try:
                    # Calculate confidence level
                    confidence_level = experiment.get("confidence_level", 0.95)
                    
                    # Run statistical analysis
                    analysis = statistics_service.analyze_experiment_results(
                        {name: data for name, data in results["variants"].items()},
                        confidence_level=confidence_level
                    )
                    
                    # Add statistical data to results
                    results["analysis"] = analysis
                    
                    # Calculate sample size recommendation if base_rate and min_detectable_effect are provided
                    if experiment.get("base_rate") is not None and experiment.get("min_detectable_effect") is not None:
                        try:
                            results["metadata"]["recommended_sample_size"] = statistics_service.calculate_sample_size(
                                base_rate=experiment["base_rate"],
                                min_detectable_effect=experiment["min_detectable_effect"],
                                confidence_level=confidence_level
                            )
                        except Exception as e:
                            logger.warning(f"Failed to calculate recommended sample size: {str(e)}")
                except Exception as e:
                    logger.warning(f"Statistical analysis failed: {str(e)}")
        
        return results

# Initialize the global service
experiment_service = ExperimentService()
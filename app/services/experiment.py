import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..models.experiment import ExperimentCreate, ExperimentUpdate, ExperimentStatus
from ..db.dynamodb import dynamodb_client
from ..db.redis import redis_client

logger = logging.getLogger(__name__)

class ExperimentService:
    @staticmethod
    async def create_experiment(experiment_data: Dict) -> Dict:
        """Create a new experiment"""
        # Generate a unique ID
        experiment_id = str(uuid.uuid4())
        
        # Add timestamps and ID
        now = datetime.utcnow()
        experiment = {
            **experiment_data,
            "experiment_id": experiment_id,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        # Save to database
        created_experiment = await dynamodb_client.create_experiment(experiment)
        
        # Add to cache
        await redis_client.set_experiment(experiment_id, created_experiment)
        
        return created_experiment
    
    @staticmethod
    async def get_experiment(experiment_id: str) -> Optional[Dict]:
        """Get experiment by ID with caching"""
        # Try to get from cache first
        cached_experiment = await redis_client.get_experiment(experiment_id)
        if cached_experiment:
            logger.debug(f"Cache hit for experiment: {experiment_id}")
            return cached_experiment
            
        # If not in cache, try to get from database
        db_experiment = await dynamodb_client.get_experiment(experiment_id)
        if db_experiment:
            logger.debug(f"Database hit for experiment: {experiment_id}")
            # Refresh cache
            await redis_client.set_experiment(experiment_id, db_experiment)
            return db_experiment
            
        # No experiment exists
        return None
    
    @staticmethod
    async def update_experiment(experiment_id: str, update_data: Dict) -> Dict:
        """Update an experiment"""
        # Check if the experiment exists
        existing = await ExperimentService.get_experiment(experiment_id)
        if not existing:
            raise ValueError(f"Experiment {experiment_id} not found")
            
        # Update the experiment
        updated_experiment = await dynamodb_client.update_experiment(experiment_id, update_data)
        
        # Clear from cache to force a refresh
        await redis_client.delete_experiment_cache(experiment_id)
        
        return updated_experiment
    
    @staticmethod
    async def delete_experiment(experiment_id: str) -> bool:
        """Delete an experiment"""
        # Delete from database
        success = await dynamodb_client.delete_experiment(experiment_id)
        
        # Clear from cache
        await redis_client.delete_experiment_cache(experiment_id)
        
        return success
    
    @staticmethod
    async def list_experiments(status: Optional[str] = None) -> List[Dict]:
        """List all experiments, optionally filtered by status"""
        return await dynamodb_client.list_experiments(status)
    
    @staticmethod
    async def activate_experiment(experiment_id: str) -> Dict:
        """Activate an experiment"""
        return await ExperimentService.update_experiment(
            experiment_id, 
            {"status": ExperimentStatus.ACTIVE.value}
        )
    
    @staticmethod
    async def pause_experiment(experiment_id: str) -> Dict:
        """Pause an experiment"""
        return await ExperimentService.update_experiment(
            experiment_id, 
            {"status": ExperimentStatus.PAUSED.value}
        )
    
    @staticmethod
    async def complete_experiment(experiment_id: str) -> Dict:
        """Mark an experiment as completed"""
        return await ExperimentService.update_experiment(
            experiment_id, 
            {"status": ExperimentStatus.COMPLETED.value}
        )
    
    @staticmethod
    async def archive_experiment(experiment_id: str) -> Dict:
        """Archive an experiment"""
        return await ExperimentService.update_experiment(
            experiment_id, 
            {"status": ExperimentStatus.ARCHIVED.value}
        )
    
    @staticmethod
    async def get_experiment_stats(
        experiment_id: str,
        event_types: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, int]]:
        """
        Get experiment statistics by variant
        Returns a dictionary mapping variants to event counts by type
        """
        # Get the experiment to know the variants
        experiment = await ExperimentService.get_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
            
        variants = [v["name"] for v in experiment.get("variants", [])]
        
        # Default event types if not specified
        if not event_types:
            event_types = ["impression", "conversion"]
            
        # Initialize result structure
        results = {variant: {event_type: 0 for event_type in event_types} for variant in variants}
        
        # Get counts for each event type
        for event_type in event_types:
            counts = await dynamodb_client.get_event_counts_by_variant(
                experiment_id=experiment_id,
                event_type=event_type
            )
            
            # Update results
            for variant, count in counts.items():
                if variant in results:
                    results[variant][event_type] = count
                    
        return results

# Initialize the global service
experiment_service = ExperimentService()
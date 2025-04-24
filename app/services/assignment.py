# app/services/assignment.py
import hashlib
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from ..db.dynamodb import dynamodb_client
from ..db.redis import redis_client
from ..config import settings

logger = logging.getLogger(__name__)

class AssignmentService:
    @staticmethod
    async def get_assignment(subid: str, experiment_id: str) -> Optional[Dict]:
        """
        Get a user's variant assignment for an experiment
        Checks cache first, then database, with a cache refresh if found
        """
        # Try to get from cache first
        cached_assignment = await redis_client.get_assignment(subid, experiment_id)
        if cached_assignment:
            logger.debug(f"Cache hit for assignment: {subid}:{experiment_id}")
            return cached_assignment
            
        # If not in cache, try to get from database
        db_assignment = await dynamodb_client.get_assignment(subid, experiment_id)
        if db_assignment:
            logger.debug(f"Database hit for assignment: {subid}:{experiment_id}")
            # Refresh cache
            await redis_client.set_assignment(subid, experiment_id, db_assignment)
            return db_assignment
            
        # No assignment exists
        return None
    
    @staticmethod
    async def create_assignment(
        subid: str, 
        experiment_id: str, 
        experiment: Optional[Dict] = None
    ) -> Tuple[Dict, bool]:
        """
        Create a new assignment for a user in an experiment
        Uses a deterministic algorithm to ensure consistency
        
        Returns:
            Tuple of (assignment_data, is_experiment_full)
            If is_experiment_full is True, the assignment is a default variant
        """
        # Get experiment if not provided
        if experiment is None:
            # Try cache first
            experiment = await redis_client.get_experiment(experiment_id)
            
            # If not in cache, get from database
            if not experiment:
                experiment = await dynamodb_client.get_experiment(experiment_id)
                if experiment:
                    # Refresh cache
                    await redis_client.set_experiment(experiment_id, experiment)
                    
            if not experiment:
                raise ValueError(f"Experiment '{experiment_id}' not found")
                
        # Check if experiment is active
        if experiment.get("status") != "active":
            raise ValueError(f"Experiment '{experiment_id}' is not active")
            
        # Get variants from experiment
        variants = experiment.get("variants", [])
        if not variants:
            raise ValueError(f"Experiment '{experiment_id}' has no variants")
        
        # Check if experiment has reached population limit
        experiment_full = False
        default_variant = variants[0]["name"]  # Use first variant as default
        
        # Only check population limit if total_population is set
        if experiment.get("total_population"):
            # Get current assignment count, excluding default assignments
            assignment_counts = await dynamodb_client.get_assignment_counts_by_variant(
                experiment_id, 
                include_default_assignments=False
            )
            
            # Sum up all non-default assignments
            real_assignment_count = sum(assignment_counts.values())
            
            # Check if limit reached
            if real_assignment_count >= experiment.get("total_population", 0):
                experiment_full = True
                
                # Create assignment record with default variant and special flag
                assignment = {
                    "subid": subid,
                    "experiment_id": experiment_id,
                    "variant": default_variant,
                    "created_at": datetime.utcnow().isoformat(),
                    "is_default_assignment": True,
                    "reason": "experiment_population_limit_reached"
                }
                
                # Save to database (we still save these to keep track of overflow)
                await dynamodb_client.create_assignment(assignment)
                
                # Update cache
                await redis_client.set_assignment(subid, experiment_id, assignment)
                
                return assignment, experiment_full
        
        # If not full, proceed with normal assignment
        # Determine which variant to assign using a deterministic algorithm
        variant = await AssignmentService._get_variant_for_user(subid, experiment_id, variants)
        
        # Create assignment record
        assignment = {
            "subid": subid,
            "experiment_id": experiment_id,
            "variant": variant,
            "created_at": datetime.utcnow().isoformat(),
            "is_default_assignment": False
        }
        
        # Save to database
        await dynamodb_client.create_assignment(assignment)
        
        # Update cache
        await redis_client.set_assignment(subid, experiment_id, assignment)
        
        return assignment, experiment_full
    
    @staticmethod
    async def get_or_create_assignment(subid: str, experiment_id: str) -> Dict:
        """
        Get an existing assignment or create a new one if not found
        
        Returns assignment data with additional status info if experiment is full
        """
        # Try to get existing assignment
        existing = await AssignmentService.get_assignment(subid, experiment_id)
        if existing:
            return existing
            
        # Create new assignment if not found
        assignment, is_experiment_full = await AssignmentService.create_assignment(subid, experiment_id)
        
        # If the experiment is full, add a special status to the response
        if is_experiment_full:
            assignment["status"] = "experiment_population_limit_reached"
            
        return assignment
    
    @staticmethod
    async def get_user_assignments(subid: str) -> List[Dict]:
        """
        Get all assignments for a user across all experiments
        """
        return await dynamodb_client.get_user_assignments(subid)
    
    @staticmethod
    async def _get_variant_for_user(
        subid: str, 
        experiment_id: str, 
        variants: List[Dict]
    ) -> str:
        """
        Deterministic variant assignment algorithm
        Uses a hash of the user ID and experiment ID to ensure consistent assignments
        Respects variant weights for proper distribution
        
        Uses integer weights for simplicity and efficiency
        """
        # Create a hash of the user ID, experiment ID, and salt
        hash_input = f"{subid}:{experiment_id}:{settings.ASSIGNMENT_HASH_SALT}"
        hash_obj = hashlib.sha256(hash_input.encode())
        hash_hex = hash_obj.hexdigest()
        
        # Convert first 8 characters of hash to an integer
        hash_int = int(hash_hex[:8], 16)
        
        # Get integer weights
        weights = [int(variant.get("weight", 1)) for variant in variants]
        
        # Calculate the total weight
        total_weight = sum(weights)
        
        # Avoid division by zero
        if total_weight <= 0:
            logger.warning(f"Total weight for experiment {experiment_id} is zero or negative. Defaulting to first variant.")
            return variants[0]["name"]
        
        # Get a value between 0 and total_weight-1
        target = hash_int % total_weight
        
        # Select the variant based on the target value
        running_total = 0
        for i, variant in enumerate(variants):
            running_total += weights[i]
            if target < running_total:
                return variant["name"]

        # Fallback (should never happen unless there's a rounding error)
        return variants[-1]["name"]

# Initialize the global service
assignment_service = AssignmentService()
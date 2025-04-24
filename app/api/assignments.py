from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import JSONResponse
from typing import List, Dict

from ..models.assignment import (
    AssignmentResponse, 
    AssignmentRequest,
    BulkAssignmentRequest
)
from ..services.assignment import assignment_service

router = APIRouter(prefix="/assignments", tags=["assignments"])

@router.post("/get", response_model=AssignmentResponse)
async def get_or_create_assignment(request: AssignmentRequest):
    """Get a user's variant assignment for an experiment, creating one if it doesn't exist"""
    try:
        assignment = await assignment_service.get_or_create_assignment(
            request.subid, 
            request.experiment_id
        )
        
        # Check if experiment is full and this is a default assignment
        if assignment.get("is_default_assignment") and assignment.get("status") == "experiment_population_limit_reached":
            # Return 422 Unprocessable Entity to indicate the experiment is full
            # This is a client error indicating that the server understood the request but
            # could not process it due to semantic errors (in this case, experiment being full)
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    **assignment,
                    "detail": "Experiment population limit reached. User assigned to default variant."
                }
            )
        
        return assignment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get or create assignment: {str(e)}")

@router.post("/bulk", response_model=Dict[str, AssignmentResponse])
async def get_or_create_bulk_assignments(request: BulkAssignmentRequest):
    """
    Get a user's variant assignments for multiple experiments at once,
    creating assignments as needed
    """
    try:
        results = {}
        full_experiments = []
        
        for experiment_id in request.experiment_ids:
            assignment = await assignment_service.get_or_create_assignment(
                request.subid, 
                experiment_id
            )
            results[experiment_id] = assignment
            
            # Track experiments that are full
            if assignment.get("is_default_assignment") and assignment.get("status") == "experiment_population_limit_reached":
                full_experiments.append(experiment_id)
        
        # If any experiments are full, return a special response with 422 status
        if full_experiments:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "assignments": results,
                    "full_experiments": full_experiments,
                    "detail": "Some experiments have reached their population limits. Default variants assigned."
                }
            )
        
        return results
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get or create bulk assignments: {str(e)}")

@router.get("/user/{subid}", response_model=List[AssignmentResponse])
async def get_user_assignments(subid: str):
    """Get all assignments for a user across all experiments"""
    try:
        assignments = await assignment_service.get_user_assignments(subid)
        return assignments
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user assignments: {str(e)}")

@router.get("/{subid}/{experiment_id}", response_model=AssignmentResponse)
async def get_specific_assignment(subid: str, experiment_id: str):
    """Get a specific assignment by user ID and experiment ID"""
    try:
        assignment = await assignment_service.get_assignment(subid, experiment_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assignment for user {subid} in experiment {experiment_id} not found"
            )
            
        # Check if experiment is full and this is a default assignment
        if assignment.get("is_default_assignment") and assignment.get("status") == "experiment_population_limit_reached":
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    **assignment,
                    "detail": "Experiment population limit reached. User assigned to default variant."
                }
            )
            
        return assignment
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get assignment: {str(e)}")
# app/api/experiments.py
from fastapi import APIRouter, HTTPException, Depends, Query, status, Body
from typing import List, Optional

from ..models.experiment import (
    ExperimentCreate, 
    ExperimentUpdate, 
    ExperimentResponse, 
    ExperimentStatus,
    ExperimentStats
)
from ..services.experiment import experiment_service

router = APIRouter(prefix="/experiments", tags=["experiments"])

@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_experiment(experiment: ExperimentCreate):
    """Create a new AB testing experiment using experiment name as identifier"""
    try:
        created = await experiment_service.create_experiment(experiment.dict())
        return created
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create experiment: {str(e)}")

@router.get("", response_model=List[ExperimentResponse])
async def list_experiments(
    status: Optional[ExperimentStatus] = Query(None, description="Filter by experiment status")
):
    """List all experiments, optionally filtered by status"""
    try:
        status_value = status.value if status else None
        experiments = await experiment_service.list_experiments(status_value)
        return experiments
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list experiments: {str(e)}")

@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(experiment_id: str):
    """Get experiment details by ID (which is the experiment name)"""
    experiment = await experiment_service.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment '{experiment_id}' not found"
        )
    return experiment

@router.patch("/{experiment_id}", response_model=ExperimentResponse)
async def update_experiment(experiment_id: str, update_data: ExperimentUpdate):
    """Update an experiment"""
    try:
        # Convert to dict and remove None values
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        if not update_dict:
            raise HTTPException(status_code=400, detail="No valid update fields provided")
            
        updated = await experiment_service.update_experiment(experiment_id, update_dict)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update experiment: {str(e)}")

@router.delete("/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experiment(experiment_id: str):
    """Delete an experiment"""
    try:
        success = await experiment_service.delete_experiment(experiment_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete experiment: {str(e)}")

@router.post("/{experiment_id}/status", response_model=ExperimentResponse)
async def update_experiment_status(
    experiment_id: str, 
    status: ExperimentStatus = Body(..., embed=True)
):
    """
    Update experiment status
    
    This consolidated endpoint replaces the separate activate/pause/complete/archive endpoints
    """
    try:
        updated = await experiment_service.update_experiment_status(experiment_id, status)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update experiment status: {str(e)}")

@router.get("/{experiment_id}/stats", response_model=ExperimentStats)
async def get_experiment_stats(
    experiment_id: str, 
    event_types: Optional[List[str]] = Query(None),
    include_assignments: bool = Query(True, description="Include assignment counts in statistics"),
    include_analysis: bool = Query(True, description="Include statistical analysis")
):
    """
    Get experiment statistics by variant with statistical analysis
    
    By default includes:
    - Assignment counts
    - Event counts (impressions, conversions)
    - Statistical analysis (conversion rates, confidence intervals, p-values)
    - Significance determination (winning, losing, inconclusive)
    """
    try:
        stats = await experiment_service.get_experiment_stats(
            experiment_id, 
            event_types,
            include_assignments,
            include_analysis
        )
        
        # Add experiment_id to the response for backward compatibility
        stats["experiment_id"] = experiment_id
        
        return stats
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get experiment stats: {str(e)}")
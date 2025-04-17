from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, status
from typing import List, Optional
from datetime import datetime
import uuid

from ..models.events import (
    EventCreate, 
    EventResponse, 
    EventsQueryParams
)
from ..db.dynamodb import dynamodb_client
from ..services.assignment import assignment_service
from ..services.experiment import experiment_service

router = APIRouter(prefix="/events", tags=["events"])

# Helper function to track events in the background
async def track_event_async(event_data: dict):
    """Process event tracking in the background"""
    try:
        # Add event_id and timestamp if not provided
        if "event_id" not in event_data:
            event_data["event_id"] = str(uuid.uuid4())
        
        if "timestamp" not in event_data:
            event_data["timestamp"] = datetime.utcnow()
            
        # Store the event
        await dynamodb_client.create_event(event_data)
    except Exception as e:
        # Log the error but don't fail the request
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to track event: {str(e)}")


@router.post("", response_model=EventResponse, status_code=status.HTTP_202_ACCEPTED)
async def track_event(event: EventCreate, background_tasks: BackgroundTasks):
    """
    Track an event for a user in an experiment
    
    This endpoint processes events asynchronously to minimize latency
    """
    try:
        # Validate that the experiment exists
        experiment = await experiment_service.get_experiment(event.experiment_id)
        if not experiment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment with ID {event.experiment_id} not found"
            )
            
        # Validate that the variant exists in the experiment
        valid_variants = [v["name"] for v in experiment.get("variants", [])]
        if event.variant not in valid_variants:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Variant '{event.variant}' is not valid for experiment {event.experiment_id}"
            )
        
        # Convert to dict for background processing
        event_dict = event.dict()
        
        # Add event_id and timestamp
        event_dict["event_id"] = str(uuid.uuid4())
        event_dict["timestamp"] = datetime.utcnow()
        
        # Process in background
        background_tasks.add_task(track_event_async, event_dict)
        
        # Return the event data immediately
        return event_dict
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track event: {str(e)}")


@router.get("", response_model=List[EventResponse])
async def query_events(
    experiment_id: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    event_type: Optional[str] = Query(None),
    variant: Optional[str] = Query(None),
    subid: Optional[str] = Query(None)
):
    """
    Query events with optional filtering
    """
    try:
        events = await dynamodb_client.query_events(
            experiment_id=experiment_id,
            start_date=start_date,
            end_date=end_date,
            event_type=event_type,
            variant=variant,
            subid=subid
        )
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query events: {str(e)}")


@router.post("/impression", response_model=EventResponse, status_code=status.HTTP_202_ACCEPTED)
async def track_impression(
    subid: str = Query(...),
    experiment_id: str = Query(...),
    background_tasks: BackgroundTasks = None
):
    """
    Specialized endpoint for tracking impressions
    Automatically determines the correct variant from the user's assignment
    """
    try:
        # Get the user's assignment
        assignment = await assignment_service.get_or_create_assignment(subid, experiment_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not determine variant for user {subid} in experiment {experiment_id}"
            )
            
        # Create impression event
        event_data = {
            "experiment_id": experiment_id,
            "subid": subid,
            "event_type": "impression",
            "variant": assignment["variant"],
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow(),
            "metadata": {"auto_tracked": True}
        }
        
        # Process in background
        if background_tasks:
            background_tasks.add_task(track_event_async, event_data)
        else:
            await track_event_async(event_data)
        
        return event_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track impression: {str(e)}")


@router.post("/conversion", response_model=EventResponse, status_code=status.HTTP_202_ACCEPTED)
async def track_conversion(
    subid: str = Query(...),
    experiment_id: str = Query(...),
    conversion_type: Optional[str] = Query("default"),
    background_tasks: BackgroundTasks = None
):
    """
    Specialized endpoint for tracking conversions
    Automatically determines the correct variant from the user's assignment
    """
    try:
        # Get the user's assignment
        assignment = await assignment_service.get_or_create_assignment(subid, experiment_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not determine variant for user {subid} in experiment {experiment_id}"
            )
            
        # Create conversion event
        event_data = {
            "experiment_id": experiment_id,
            "subid": subid,
            "event_type": "conversion",
            "variant": assignment["variant"],
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow(),
            "metadata": {"conversion_type": conversion_type, "auto_tracked": True}
        }
        
        # Process in background
        if background_tasks:
            background_tasks.add_task(track_event_async, event_data)
        else:
            await track_event_async(event_data)
        
        return event_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track conversion: {str(e)}")
from pydantic import BaseModel, Field
from typing import Dict, Optional, Any
from datetime import datetime
import uuid

class EventBase(BaseModel):
    experiment_id: str
    subid: str
    event_type: str
    variant: str
    metadata: Optional[Dict[str, Any]] = None

class EventCreate(EventBase):
    pass

class EventInDB(EventBase):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        orm_mode = True

class EventResponse(EventInDB):
    pass

class EventsQueryParams(BaseModel):
    experiment_id: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    event_type: Optional[str] = None
    variant: Optional[str] = None
    subid: Optional[str] = None
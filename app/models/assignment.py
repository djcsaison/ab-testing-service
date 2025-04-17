from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class AssignmentBase(BaseModel):
    subid: str
    experiment_id: str
    variant: str

class AssignmentCreate(AssignmentBase):
    pass

class AssignmentInDB(AssignmentBase):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        orm_mode = True

class AssignmentResponse(AssignmentInDB):
    pass

class AssignmentRequest(BaseModel):
    subid: str
    experiment_id: str
    
class BulkAssignmentRequest(BaseModel):
    subid: str
    experiment_ids: list[str]
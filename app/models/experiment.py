from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum

class ExperimentStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class Variant(BaseModel):
    name: str
    description: Optional[str] = None
    weight: int = 1  # Integer weight with default of 1
    
    @validator('weight')
    def weight_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Weight must be positive')
        return v

class ExperimentBase(BaseModel):
    name: str
    description: Optional[str] = None
    variants: List[Variant]
    status: ExperimentStatus = ExperimentStatus.DRAFT
    
    @validator('variants')
    def validate_variants(cls, variants):
        if len(variants) < 2:
            raise ValueError('An experiment must have at least 2 variants')
        
        # Check for duplicate variant names
        variant_names = [variant.name for variant in variants]
        if len(variant_names) != len(set(variant_names)):
            raise ValueError('Variant names must be unique')
            
        return variants

class ExperimentCreate(ExperimentBase):
    pass

class ExperimentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    variants: Optional[List[Variant]] = None
    status: Optional[ExperimentStatus] = None

class ExperimentInDB(ExperimentBase):
    experiment_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        orm_mode = True

class ExperimentResponse(ExperimentInDB):
    pass

class ExperimentStats(BaseModel):
    experiment_id: str
    variant_stats: Dict[str, Dict[str, int]]  # variant_name -> {event_type -> count}
    
    class Config:
        orm_mode = True
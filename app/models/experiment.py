# app/models/experiment.py
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
import re

class ExperimentStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"

class Variant(BaseModel):
    name: str
    description: Optional[str] = None
    weight: int = 1  # Integer weight with default of 1
    
    @validator('weight')
    def weight_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Weight must be positive')
        return v

    @validator('name')
    def name_must_be_valid(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Variant name must contain only alphanumeric characters, hyphens, and underscores')
        return v

class ExperimentBase(BaseModel):
    name: str
    description: Optional[str] = None
    variants: List[Variant]
    status: ExperimentStatus = ExperimentStatus.DRAFT
    total_population: Optional[int] = None  # Add optional total population field
    
    @validator('name')
    def name_must_be_valid(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Experiment name must contain only alphanumeric characters, hyphens, and underscores')
        return v
    
    @validator('variants')
    def validate_variants(cls, variants):
        if len(variants) < 2:
            raise ValueError('An experiment must have at least 2 variants')
        
        # Check for duplicate variant names
        variant_names = [variant.name for variant in variants]
        if len(variant_names) != len(set(variant_names)):
            raise ValueError('Variant names must be unique')
            
        return variants
        
    @validator('total_population')
    def total_population_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Total population must be positive')
        return v

class ExperimentCreate(ExperimentBase):
    pass

class ExperimentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    variants: Optional[List[Variant]] = None
    status: Optional[ExperimentStatus] = None
    total_population: Optional[int] = None

class ExperimentInDB(ExperimentBase):
    experiment_id: str  # Keep this to maintain compatibility with existing schema
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        orm_mode = True

class ExperimentResponse(ExperimentInDB):
    pass

class ExperimentStats(BaseModel):
    experiment_id: str  # Keep this for compatibility
    variant_stats: Dict[str, Dict[str, int]]  # variant_name -> stats
    
    class Config:
        orm_mode = True
# app/models/experiment.py
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
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
    is_control: bool = False  # Flag to identify the control variant
    
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
    total_population: Optional[int] = None  # Total population limit for the experiment
    
    # New statistical parameters
    base_rate: Optional[float] = None  # The baseline/control conversion rate (e.g., 0.2 for 20%)
    min_detectable_effect: Optional[float] = None  # The minimum effect size to detect (e.g., 0.05 for 5%)
    min_sample_size_per_group: Optional[int] = None  # The minimum sample size needed per variant
    confidence_level: Optional[float] = Field(None, ge=0.8, le=0.99)  # Statistical confidence level (typically 0.95)
    additional_features: Optional[Dict[str, Any]] = None  # Additional metadata for the experiment
    
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
            
        # Check that only one variant is marked as control
        control_variants = [v for v in variants if v.is_control]
        if len(control_variants) > 1:
            raise ValueError('Only one variant can be marked as the control')
            
        # If no control variant is specified, set the first one as control
        if len(control_variants) == 0 and len(variants) > 0:
            variants[0].is_control = True
            
        return variants
        
    @validator('total_population')
    def total_population_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Total population must be positive')
        return v
        
    @validator('base_rate')
    def base_rate_must_be_valid(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError('Base rate must be between 0 and 1')
        return v
        
    @validator('min_detectable_effect')
    def min_detectable_effect_must_be_valid(cls, v):
        if v is not None and (v <= 0 or v > 1):
            raise ValueError('Minimum detectable effect must be greater than 0 and less than or equal to 1')
        return v

class ExperimentCreate(ExperimentBase):
    pass

class ExperimentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    variants: Optional[List[Variant]] = None
    status: Optional[ExperimentStatus] = None
    total_population: Optional[int] = None
    base_rate: Optional[float] = None
    min_detectable_effect: Optional[float] = None
    min_sample_size_per_group: Optional[int] = None
    confidence_level: Optional[float] = None
    additional_features: Optional[Dict[str, Any]] = None

class ExperimentInDB(ExperimentBase):
    experiment_id: str  # Keep this to maintain compatibility with existing schema
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        orm_mode = True

class ExperimentResponse(ExperimentInDB):
    pass

class ExperimentStats(BaseModel):
    experiment_id: str
    variants: Dict[str, Dict[str, int]]
    variant_stats: Optional[Dict[str, Dict[str, int]]] = None
    control_variant: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    analysis: Optional[Dict[str, Any]] = None
    
    class Config:
        orm_mode = True
        extra = "allow"  # Allow extra fields for forward compatibility

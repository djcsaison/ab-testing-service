import os
from enum import Enum
from typing import List
from pydantic import BaseSettings, Field

class Environment(str, Enum):
    DEVELOPMENT = "dev"
    INT = "int" 
    QA = "qa"
    QA2 = "qa2"
    PRODUCTION = "production"

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "AB Testing Service"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    ENVIRONMENT: Environment = Field(
        default_factory=lambda: Environment(os.getenv("ENVIRONMENT", "development"))
    )
    
    # Authentication settings
    ENABLE_BASIC_AUTH: bool = os.getenv("ENABLE_BASIC_AUTH", "true").lower() in ("true", "1", "t")
    BASIC_AUTH_USERNAME: str = os.getenv("BASIC_AUTH_USERNAME", "admin")
    BASIC_AUTH_PASSWORD: str = os.getenv("BASIC_AUTH_PASSWORD", "password")
    
    # AWS DynamoDB settings
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    DYNAMODB_ENDPOINT: str = os.getenv("DYNAMODB_ENDPOINT", "")  # Only for local development
    
    # DynamoDB table names - allow override with environment variables
    EXPERIMENTS_TABLE: str = os.getenv("EXPERIMENTS_TABLE", "ab-testing-experiments")
    ASSIGNMENTS_TABLE: str = os.getenv("ASSIGNMENTS_TABLE", "ab-testing-assignments")
    EVENTS_TABLE: str = os.getenv("EVENTS_TABLE", "ab-testing-events")
    
    # Redis settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_SSL: bool = os.getenv("REDIS_SSL", "False").lower() in ("true", "1", "t")
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    # Cache settings
    ASSIGNMENT_CACHE_TTL: int = int(os.getenv("ASSIGNMENT_CACHE_TTL", "3600"))  # 1 hour
    EXPERIMENT_CACHE_TTL: int = int(os.getenv("EXPERIMENT_CACHE_TTL", "300"))   # 5 minutes
    
    # Algorithm settings
    ASSIGNMENT_HASH_SALT: str = os.getenv("ASSIGNMENT_HASH_SALT", "ab-testing-salt")
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = [
        x.strip() for x in os.getenv("ALLOWED_ORIGINS", "*").split(",") if x.strip()
    ]
    
    # Get environment-specific table name prefixes
    @property
    def table_prefix(self) -> str:
        if self.ENVIRONMENT == Environment.PRODUCTION:
            return ""
        return f"{self.ENVIRONMENT.value}-"
    
    @property
    def full_experiments_table(self) -> str:
        return f"{self.table_prefix}{self.EXPERIMENTS_TABLE}"
        
    @property
    def full_assignments_table(self) -> str:
        return f"{self.table_prefix}{self.ASSIGNMENTS_TABLE}"
        
    @property
    def full_events_table(self) -> str:
        return f"{self.table_prefix}{self.EVENTS_TABLE}"
        
    def should_authenticate(self) -> bool:
        """
        Helper method to determine if authentication should be enabled
        """
        # Always disable auth for development unless explicitly enabled
        if self.ENVIRONMENT == Environment.DEVELOPMENT and not os.getenv("ENABLE_BASIC_AUTH"):
            return False
        return self.ENABLE_BASIC_AUTH
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Initialize settings once
settings = Settings()
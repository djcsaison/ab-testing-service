import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "AB Testing Service"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    
    # AWS DynamoDB settings
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    DYNAMODB_ENDPOINT: str = os.getenv("DYNAMODB_ENDPOINT", "")  # for local testing
    
    # DynamoDB table names
    EXPERIMENTS_TABLE: str = os.getenv("EXPERIMENTS_TABLE", "ab-testing-experiments")
    ASSIGNMENTS_TABLE: str = os.getenv("ASSIGNMENTS_TABLE", "ab-testing-assignments")
    EVENTS_TABLE: str = os.getenv("EVENTS_TABLE", "ab-testing-events")
    
    # Redis settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    # Cache settings
    ASSIGNMENT_CACHE_TTL: int = int(os.getenv("ASSIGNMENT_CACHE_TTL", "3600"))  # 1 hour
    EXPERIMENT_CACHE_TTL: int = int(os.getenv("EXPERIMENT_CACHE_TTL", "300"))   # 5 minutes
    
    # Algorithm settings
    ASSIGNMENT_HASH_SALT: str = os.getenv("ASSIGNMENT_HASH_SALT", "ab-testing-salt")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
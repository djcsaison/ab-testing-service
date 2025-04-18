from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from contextlib import asynccontextmanager

from .config import settings
from .api import experiments, assignments, events
from .db.redis import redis_client

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Startup and shutdown event handlers
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize connections
    logger.info("Starting up AB Testing Service")
    try:
        await redis_client.connect()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {str(e)}")
        
    yield
    
    # Shutdown: Close connections
    logger.info("Shutting down AB Testing Service")
    try:
        await redis_client.close()
        logger.info("Redis connection closed")
    except Exception as e:
        logger.error(f"Error closing Redis connection: {str(e)}")

# Create the FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="A/B Testing service with FastAPI and DynamoDB",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request ID and logging middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    
    # Generate a request ID for tracking
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Log the incoming request
    logger.info(f"Request {request_id}: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        
        # Add custom headers
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = request_id
        
        # Log the response time
        logger.info(f"Request {request_id} completed in {process_time:.4f}s with status {response.status_code}")
        
        return response
    except Exception as e:
        # Log exceptions
        logger.error(f"Request {request_id} failed: {str(e)}")
        
        # Return a 500 error
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"}
        )

# Include routers
app.include_router(experiments.router, prefix="/api")
app.include_router(assignments.router, prefix="/api")
app.include_router(events.router, prefix="/api")

# Add a health check endpoint
@app.get("/api/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    # Check Redis connection
    redis_ok = False
    try:
        redis_ping = await redis_client.redis.ping()
        redis_ok = redis_ping is True
    except Exception:
        redis_ok = False
    
    # Overall health status
    is_healthy = redis_ok
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "version": settings.APP_VERSION,
        "dependencies": {
            "redis": "ok" if redis_ok else "error"
        }
    }

# Root route for info
@app.get("/", tags=["root"])
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "A/B Testing Service API",
        "docs": "/api/docs"
    }

# Start the application with Uvicorn when run directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
from fastapi import FastAPI, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from .config import settings
from .api import experiments, assignments, events
from .db.redis import redis_client
from .middleware.basic_auth import BasicAuthMiddleware, authenticate_swagger

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
    logger.info(f"Starting up AB Testing Service in {settings.ENVIRONMENT.value} environment")
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
    allow_origins=settings.ALLOWED_ORIGINS,
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

# Mount static files directory
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
else:
    logger.warning(f"Static files directory {static_dir} does not exist")


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
        "environment": settings.ENVIRONMENT.value,
        "dependencies": {
            "redis": "ok" if redis_ok else "error"
        }
    }

# Serve admin dashboard at root
@app.get("/", response_class=HTMLResponse, tags=["dashboard"])
async def admin_dashboard():
    static_dir = Path(__file__).parent / "static"
    index_path = static_dir / "index.html"
    
    if index_path.exists():
        with open(index_path, "r") as f:
            return f.read()
    else:
        return """
        <html>
            <head>
                <title>A/B Testing Service</title>
            </head>
            <body>
                <h1>A/B Testing Service</h1>
                <p>Admin dashboard not found. Please check the static files directory.</p>
                <p>API is available at <a href="/api/docs">/api/docs</a></p>
            </body>
        </html>
        """


# Return API info for /api endpoint
@app.get("/api", tags=["root"])
async def api_root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "A/B Testing Service API",
        "docs": "/api/docs",
        "environment": settings.ENVIRONMENT.value
    }


# Add Basic Auth middleware if enabled
app.add_middleware(BasicAuthMiddleware)

# Start the application with Uvicorn when run directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
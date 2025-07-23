"""
LeadFactory FastAPI Application Entry Point
Implements PRP-001: Lead Data Model & API with FastAPI and SQLAlchemy
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
import logging
import sys
from contextlib import asynccontextmanager

from src.core.config import settings
from src.core.database import engine, create_tables
from src.core.logging import setup_logging
from src.api.v1.router import api_router

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting LeadFactory application...")
    
    # Create database tables
    await create_tables()
    logger.info("Database tables created/verified")
    
    # Initialize Celery (if needed)
    # from src.core.celery_app import celery_app
    
    logger.info("LeadFactory started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down LeadFactory...")
    # Cleanup code here
    logger.info("LeadFactory shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="LeadFactory - Business Lead Assessment and Revenue Optimization System",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else [settings.BASE_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint"""
    return {
        "message": "LeadFactory API",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "operational"
    }


@app.get("/health", include_in_schema=False)
async def health_check():
    """Health check endpoint for Docker and load balancers"""
    try:
        # Test database connection
        from src.core.database import get_db_session
        async with get_db_session() as session:
            await session.execute("SELECT 1")
        
        # Test Redis connection
        from src.core.cache import get_redis
        redis = await get_redis()
        await redis.ping()
        
        return {
            "status": "healthy",
            "version": settings.APP_VERSION,
            "database": "connected",
            "cache": "connected",
            "timestamp": "now"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": "now"
            }
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    if settings.ENVIRONMENT == "development":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "detail": str(exc),
                "type": type(exc).__name__
            }
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal Server Error"}
        )


# Development server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
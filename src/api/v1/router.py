"""
PRP-001: Main API Router
Combines all v1 API endpoints for the LeadFactory application
"""

from fastapi import APIRouter

from src.api.v1 import leads, assessments, campaigns, sales, assessments_orchestrator

# Create the main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(leads.router)
api_router.include_router(assessments.router)  
api_router.include_router(campaigns.router)
api_router.include_router(sales.router)
api_router.include_router(assessments_orchestrator.router, prefix="/orchestrator", tags=["assessment-orchestrator"])

# Health check for API v1
@api_router.get("/health", tags=["health"])
async def api_health():
    """API v1 health check endpoint"""
    return {
        "status": "healthy",
        "version": "v1",
        "endpoints": [
            "/leads - Lead management CRUD operations",
            "/assessments - Assessment data and pipeline integration",
            "/campaigns - Email campaign tracking and metrics",
            "/sales - Revenue attribution and transaction management",
            "/orchestrator - Assessment orchestrator task management (PRP-002)"
        ]
    }
"""
PRP-002: Assessment Orchestrator API Endpoints
FastAPI routes for assessment task management and monitoring
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, Field
from datetime import datetime

from src.core.database import get_db
from src.assessment.orchestrator import submit_assessment, get_assessment_status
from src.assessment.tasks import celery_app
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Pydantic models for request/response
class AssessmentSubmitRequest(BaseModel):
    lead_id: int = Field(..., description="Database ID of the lead to assess")
    priority: Optional[str] = Field("normal", description="Task priority: high, normal, low")

class AssessmentSubmitResponse(BaseModel):
    task_id: str = Field(..., description="Celery task ID for tracking")
    lead_id: int = Field(..., description="Lead ID being assessed")
    status: str = Field(..., description="Initial task status")
    submitted_at: str = Field(..., description="Task submission timestamp")
    estimated_completion: str = Field(..., description="Estimated completion time")

class AssessmentStatusResponse(BaseModel):
    task_id: str = Field(..., description="Celery task ID")
    lead_id: Optional[int] = Field(None, description="Lead ID if available")
    status: str = Field(..., description="Current task status")
    progress: Optional[Dict[str, Any]] = Field(None, description="Progress information")
    result: Optional[Dict[str, Any]] = Field(None, description="Task result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    submitted_at: Optional[str] = Field(None, description="Task submission timestamp")
    completed_at: Optional[str] = Field(None, description="Task completion timestamp")

class WorkerStatsResponse(BaseModel):
    active_workers: int = Field(..., description="Number of active workers")
    active_tasks: int = Field(..., description="Number of active tasks")
    queued_tasks: Dict[str, int] = Field(..., description="Tasks queued by queue name")
    worker_details: Dict[str, Any] = Field(..., description="Detailed worker information")

@router.post(
    "/submit",
    response_model=AssessmentSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit Assessment Task",
    description="Submit a new assessment task for a business lead"
)
async def submit_assessment_task(
    request: AssessmentSubmitRequest,
    background_tasks: BackgroundTasks
) -> AssessmentSubmitResponse:
    """
    Submit a new assessment task for parallel execution.
    
    This endpoint initiates the complete assessment pipeline including:
    - PageSpeed Insights analysis
    - Security header analysis  
    - Google Business Profile data collection
    - SEMrush SEO analysis
    - Visual website analysis
    - LLM-powered insights generation
    """
    try:
        logger.info(f"Submitting assessment task for lead {request.lead_id}")
        
        # Submit the assessment task
        task_id = submit_assessment(request.lead_id)
        
        # Calculate estimated completion (90 seconds per PRP-002 requirements)
        from datetime import datetime, timezone, timedelta
        estimated_completion = (datetime.now(timezone.utc) + timedelta(seconds=90)).isoformat()
        
        response = AssessmentSubmitResponse(
            task_id=task_id,
            lead_id=request.lead_id,
            status="submitted",
            submitted_at=datetime.now(timezone.utc).isoformat(),
            estimated_completion=estimated_completion
        )
        
        logger.info(f"Assessment task submitted for lead {request.lead_id}: {task_id}")
        return response
        
    except Exception as exc:
        logger.error(f"Failed to submit assessment task for lead {request.lead_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Assessment submission failed: {str(exc)}"
        )

@router.get(
    "/status/{task_id}",
    response_model=AssessmentStatusResponse,
    summary="Get Assessment Status",
    description="Get current status and progress of an assessment task"
)
async def get_assessment_task_status(task_id: str) -> AssessmentStatusResponse:
    """
    Get the current status of an assessment task.
    
    Returns detailed information about task progress, completion status,
    and results if available.
    """
    try:
        logger.info(f"Getting status for assessment task {task_id}")
        
        # Get task status from Celery
        status_info = get_assessment_status(task_id)
        
        response = AssessmentStatusResponse(
            task_id=task_id,
            status=status_info.get("status", "UNKNOWN"),
            progress=status_info.get("info"),
            result=status_info.get("result") if status_info.get("successful") else None,
            error=status_info.get("error") if status_info.get("failed") else None,
            lead_id=status_info.get("result", {}).get("lead_id") if status_info.get("result") else None
        )
        
        logger.info(f"Retrieved status for task {task_id}: {response.status}")
        return response
        
    except Exception as exc:
        logger.error(f"Failed to get status for task {task_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status retrieval failed: {str(exc)}"
        )

@router.post(
    "/cancel/{task_id}",
    summary="Cancel Assessment Task",
    description="Cancel a running assessment task"
)
async def cancel_assessment_task(task_id: str) -> Dict[str, Any]:
    """
    Cancel a running assessment task.
    
    Note: Tasks already in progress may not be immediately cancelled.
    """
    try:
        logger.info(f"Cancelling assessment task {task_id}")
        
        # Revoke the task
        celery_app.control.revoke(task_id, terminate=True)
        
        response = {
            "task_id": task_id,
            "status": "cancelled",
            "cancelled_at": datetime.now().isoformat(),
            "message": "Task cancellation requested"
        }
        
        logger.info(f"Cancelled assessment task {task_id}")
        return response
        
    except Exception as exc:
        logger.error(f"Failed to cancel task {task_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task cancellation failed: {str(exc)}"
        )

@router.get(
    "/workers/stats",
    response_model=WorkerStatsResponse,
    summary="Get Worker Statistics",
    description="Get current worker and queue statistics"
)
async def get_worker_stats() -> WorkerStatsResponse:
    """
    Get current Celery worker statistics and queue information.
    
    Useful for monitoring system health and capacity.
    """
    try:
        logger.info("Getting worker statistics")
        
        # Get worker statistics from Celery
        inspect = celery_app.control.inspect()
        
        # Get active workers and tasks
        active_tasks = inspect.active()
        active_workers = len(active_tasks) if active_tasks else 0
        total_active_tasks = sum(len(tasks) for tasks in active_tasks.values()) if active_tasks else 0
        
        # Get queue lengths (requires Redis inspection)
        try:
            from src.core.celery_config import REDIS_URL
            import redis
            
            redis_client = redis.from_url(REDIS_URL)
            queued_tasks = {
                "high_priority": redis_client.llen("high_priority"),
                "assessment": redis_client.llen("assessment"), 
                "llm": redis_client.llen("llm"),
                "default": redis_client.llen("default")
            }
        except Exception as redis_exc:
            logger.warning(f"Could not get queue lengths from Redis: {redis_exc}")
            queued_tasks = {"error": "Redis connection failed"}
        
        # Get detailed worker information
        worker_details = {
            "active": active_tasks or {},
            "registered": inspect.registered() or {},
            "scheduled": inspect.scheduled() or {},
            "reserved": inspect.reserved() or {}
        }
        
        response = WorkerStatsResponse(
            active_workers=active_workers,
            active_tasks=total_active_tasks,
            queued_tasks=queued_tasks,
            worker_details=worker_details
        )
        
        logger.info(f"Retrieved worker stats: {active_workers} workers, {total_active_tasks} active tasks")
        return response
        
    except Exception as exc:
        logger.error(f"Failed to get worker statistics: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Worker stats retrieval failed: {str(exc)}"
        )

@router.post(
    "/workers/scale",
    summary="Scale Workers",
    description="Request worker scaling (Docker Compose deployment)"
)
async def scale_workers(worker_count: int = Field(..., description="Desired number of workers")) -> Dict[str, Any]:
    """
    Request worker scaling for Docker Compose deployment.
    
    Note: This requires Docker Compose orchestration to be configured.
    """
    try:
        logger.info(f"Requesting worker scaling to {worker_count} workers")
        
        # This would typically trigger Docker Compose scaling
        # For now, return a response indicating the request was received
        
        response = {
            "requested_workers": worker_count,
            "status": "scaling_requested",
            "message": "Worker scaling request submitted. Check Docker Compose logs for progress.",
            "requested_at": datetime.now().isoformat()
        }
        
        logger.info(f"Worker scaling requested: {worker_count} workers")
        return response
        
    except Exception as exc:
        logger.error(f"Failed to request worker scaling: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Worker scaling request failed: {str(exc)}"
        )

@router.get(
    "/health",
    summary="Health Check",
    description="Check assessment orchestrator health"
)
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for assessment orchestrator.
    
    Verifies Celery workers and Redis connectivity.
    """
    try:
        logger.info("Performing health check")
        
        # Check Celery worker connectivity
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        worker_health = "healthy" if active_workers else "no_workers"
        
        # Check Redis connectivity
        try:
            from src.core.celery_config import REDIS_URL
            import redis
            
            redis_client = redis.from_url(REDIS_URL)
            redis_client.ping()
            redis_health = "healthy"
        except Exception:
            redis_health = "unhealthy"
        
        overall_health = "healthy" if worker_health == "healthy" and redis_health == "healthy" else "degraded"
        
        response = {
            "status": overall_health,
            "timestamp": datetime.now().isoformat(),
            "components": {
                "celery_workers": worker_health,
                "redis_broker": redis_health
            },
            "active_workers": len(active_workers) if active_workers else 0
        }
        
        logger.info(f"Health check completed: {overall_health}")
        return response
        
    except Exception as exc:
        logger.error(f"Health check failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(exc)}"
        )
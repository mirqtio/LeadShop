"""
Assessment UI and Authentication Endpoints
Serves the assessment interface and handles Google OAuth authentication
"""

from fastapi import APIRouter, Request, HTTPException, status, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any, Optional
import logging
import os
from pathlib import Path

from src.auth import google_auth, get_current_user, optional_user
from src.assessments.assessment_orchestrator import execute_full_assessment
from src.assessment.tasks import full_assessment_orchestrator_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assessment", tags=["assessment-ui"])

# Template configuration
template_dir = Path(__file__).parent.parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))

class GoogleAuthRequest(BaseModel):
    """Google OAuth token request"""
    google_token: str

class AssessmentRequest(BaseModel):
    """Assessment execution request"""
    url: HttpUrl
    business_name: Optional[str] = None

class AssessmentResponse(BaseModel):
    """Assessment execution response"""
    task_id: str
    status: str
    message: str

@router.post("/auth/google", response_model=Dict[str, Any])
async def authenticate_with_google(auth_request: GoogleAuthRequest):
    """
    Authenticate user with Google OAuth token
    Returns JWT access token for subsequent API calls
    """
    try:
        # Verify Google token and get user info
        user_data = google_auth.verify_google_token(auth_request.google_token)
        
        # Create JWT access token
        access_token = google_auth.create_access_token(user_data)
        
        logger.info(f"User authenticated: {user_data['email']}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 24 * 3600,  # 24 hours
            "user": {
                "email": user_data['email'],
                "name": user_data['name'],
                "picture": user_data['picture']
            }
        }
        
    except Exception as e:
        logger.error(f"Google authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google authentication failed"
        )

@router.post("/execute", response_model=AssessmentResponse)
async def execute_assessment(
    assessment_request: AssessmentRequest,
    # current_user: Dict[str, Any] = Depends(get_current_user)  # Auth disabled for testing
):
    """
    Execute website assessment (authenticated endpoint)
    Returns task ID for tracking assessment progress
    """
    try:
        url = str(assessment_request.url)
        business_name = assessment_request.business_name
        
        # Auth disabled - use test user data
        test_user = {
            'email': 'test@example.com',
            'name': 'Test User'
        }
        
        logger.info(f"Starting assessment for {url} (auth disabled - test mode)")
        
        # Create lead data from request
        lead_data = {
            'company': business_name or 'Unknown Business',
            'url': url,
            'email': test_user['email'],  # Required field for Lead model
            'source': 'assessment_ui'  # Required field for Lead model
        }
        
        # Execute assessment via Celery task
        task = full_assessment_orchestrator_task.delay(
            lead_id=None,  # Will be created in the task
            lead_data=lead_data
        )
        
        return AssessmentResponse(
            task_id=task.id,
            status="started",
            message=f"Assessment started for {url}. Use task ID to check progress."
        )
        
    except Exception as e:
        logger.error(f"Assessment execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Assessment execution failed: {str(e)}"
        )

@router.get("/status/{task_id}")
async def get_assessment_status(
    task_id: str,
    # current_user: Dict[str, Any] = Depends(get_current_user)  # Auth disabled for testing
):
    """
    Get assessment task status and results
    """
    try:
        from celery.result import AsyncResult
        
        task_result = AsyncResult(task_id)
        
        if task_result.state == 'PENDING':
            return {
                "task_id": task_id,
                "status": "pending",
                "message": "Assessment is queued for execution"
            }
        elif task_result.state == 'PROGRESS':
            return {
                "task_id": task_id,
                "status": "in_progress",
                "message": "Assessment is currently running",
                "progress": task_result.info
            }
        elif task_result.state == 'SUCCESS':
            result = task_result.get()
            return {
                "task_id": task_id,
                "status": "completed",
                "message": "Assessment completed successfully",
                "result": result
            }
        elif task_result.state == 'FAILURE':
            return {
                "task_id": task_id,
                "status": "failed",
                "message": "Assessment failed",
                "error": str(task_result.info)
            }
        else:
            return {
                "task_id": task_id,
                "status": task_result.state.lower(),
                "message": f"Assessment status: {task_result.state}"
            }
            
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve assessment status"
        )

@router.get("", response_class=HTMLResponse)
async def serve_assessment_ui(request: Request):
    """
    Serve the assessment UI HTML page
    Available at /assessment (no authentication required for UI)
    """
    try:
        # Read the comprehensive assessment UI HTML file
        ui_file_path = Path(__file__).parent.parent.parent.parent / "assessment_ui_comprehensive.html"
        
        if not ui_file_path.exists():
            # Fallback to original UI if comprehensive version not found
            ui_file_path = Path(__file__).parent.parent.parent.parent / "assessment_ui.html"
        
        if not ui_file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment UI file not found"
            )
        
        with open(ui_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Replace API base URL with current server
        base_url = str(request.base_url).rstrip('/')
        html_content = html_content.replace(
            '// TODO: Replace mock data with actual API call',
            f'// API Base URL: {base_url}/api/v1/assessment'
        )
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Failed to serve assessment UI: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load assessment interface"
        )

@router.get("/config")
async def get_ui_config(request: Request):
    """
    Get configuration for the assessment UI
    Returns Google OAuth client ID and API endpoints
    """
    base_url = str(request.base_url).rstrip('/')
    
    return {
        "google_client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "api_base_url": f"{base_url}/api/v1/assessment",
        "auth_endpoint": f"{base_url}/api/v1/assessment/auth/google",
        "execute_endpoint": f"{base_url}/api/v1/assessment/execute",
        "status_endpoint": f"{base_url}/api/v1/assessment/status"
    }
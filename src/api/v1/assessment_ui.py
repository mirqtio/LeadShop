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

@router.get("/", response_class=HTMLResponse)
async def serve_assessment_ui(request: Request):
    """
    Serve the main assessment UI
    """
    try:
        # Read the assessment UI HTML file
        # In Docker, the working directory is /app
        assessment_ui_path = Path("/app/assessment_ui_comprehensive.html")
        
        if assessment_ui_path.exists():
            with open(assessment_ui_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
        else:
            # Fallback to inline HTML if file doesn't exist
            html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Lead Assessment - Comprehensive UI</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .error { color: red; }
        .success { color: green; }
    </style>
</head>
<body>
    <h1>Lead Assessment UI</h1>
    <p class="error">Assessment UI file not found. Please use the Simple Assessment UI at <a href="/api/v1/simple-assessment">/api/v1/simple-assessment</a></p>
</body>
</html>"""
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Failed to serve assessment UI: {e}")
        # Return a simple fallback UI
        return HTMLResponse(content=f"""<!DOCTYPE html>
<html>
<head>
    <title>Assessment UI Error</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .error {{ color: red; }}
    </style>
</head>
<body>
    <h1>Assessment UI Error</h1>
    <p class="error">Failed to load assessment UI: {str(e)}</p>
    <p>Please try the <a href="/api/v1/simple-assessment">Simple Assessment UI</a> instead.</p>
</body>
</html>""")

@router.get("/test/{assessment_id}")
async def get_test_assessment_result(assessment_id: int):
    """
    Test endpoint to return assessment result for a specific assessment ID
    """
    from src.core.database import AsyncSessionLocal
    from src.models.lead import Assessment
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as session:
        assessment_result = await session.execute(
            select(Assessment).where(Assessment.id == assessment_id)
        )
        assessment = assessment_result.scalar_one_or_none()
        
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assessment {assessment_id} not found"
            )
        
        # Get decomposed metrics from assessment_results table
        from src.models.assessment_results import AssessmentResults
        from src.api.v1.pagespeed_helpers import get_pagespeed_data_for_assessment
        
        assessment_results_query = await session.execute(
            select(AssessmentResults).where(AssessmentResults.assessment_id == assessment.id)
        )
        assessment_results = assessment_results_query.scalar_one_or_none()
        
        # Get all 53 decomposed metrics if available
        decomposed_metrics = {}
        if assessment_results:
            decomposed_metrics = assessment_results.get_all_metrics()
        
        # Get PageSpeed data from new tables
        pagespeed_data = await get_pagespeed_data_for_assessment(session, assessment.id)
        
        # Build execution object with all component results
        execution = {
            "lead_id": assessment.lead_id,
            "assessment_id": assessment.id,
            "status": "completed",
            "success_rate": 0.8,
            "successful_components": 6,
            "total_components": 8,
            "total_duration_ms": 10000,
            "total_cost_cents": 170,
            "overall_score": assessment.total_score or 75,
            "decomposed_metrics": decomposed_metrics,  # Add all 53 metrics
            
            # Component results with proper status based on data presence
            "pagespeed_result": {
                "status": {"value": "success" if pagespeed_data.get("has_data") else "failed"},
                "data": pagespeed_data if pagespeed_data.get("has_data") else assessment.pagespeed_data
            },
            "security_result": {
                "status": {"value": "success" if assessment.security_headers else "failed"},
                "data": assessment.security_headers
            },
            "gbp_result": {
                "status": {"value": "success" if assessment.gbp_data else "failed"},
                "data": assessment.gbp_data
            },
            "screenshots_result": {
                "status": {"value": "failed"},
                "data": {
                    "desktop_screenshot": None,
                    "mobile_screenshot": None
                }
            },
            "semrush_result": {
                "status": {"value": "success" if assessment.semrush_data else "failed"},
                "data": assessment.semrush_data
            },
            "visual_analysis_result": {
                "status": {"value": "success" if assessment.visual_analysis else "failed"},
                "data": assessment.visual_analysis
            },
            "score_calculation_result": {
                "status": {"value": "success" if assessment.llm_insights else "failed"},
                "data": assessment.llm_insights
            },
            "content_generation_result": {
                "status": {"value": "success" if assessment.llm_insights else "failed"},
                "data": assessment.llm_insights
            }
        }
        
        # Count actual successful components
        successful = sum(1 for comp in [
            assessment.pagespeed_data,
            assessment.security_headers,
            assessment.gbp_data,
            assessment.semrush_data,
            assessment.visual_analysis,
            assessment.llm_insights
        ] if comp is not None)
        
        execution["successful_components"] = successful
        execution["total_components"] = 8
        execution["success_rate"] = successful / 8
        
        return {
            "task_id": f"test-{assessment_id}",
            "status": "completed",
            "message": "Test assessment result",
            "result": {
                "execution": execution
            }
        }

@router.get("/config")
async def get_assessment_config():
    """
    Get configuration for the assessment UI
    """
    return {
        "google_client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
        "assessment_endpoint": "/api/v1/assessment/execute",
        "status_endpoint": "/api/v1/assessment/status",
        "auth_endpoint": "/api/v1/assessment/auth/google",
        "auth_required": False  # Disabled for testing
    }

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
        
        # Create the lead in the database
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy import select
        from src.core.database import get_db
        from src.models.lead import Lead
        from src.schemas.lead import LeadCreate
        import time
        
        # Get database session
        async for db in get_db():
            # Check if lead exists
            existing_lead_result = await db.execute(
                select(Lead).where(Lead.url == url).order_by(Lead.created_at.desc()).limit(1)
            )
            existing_lead = existing_lead_result.scalar_one_or_none()
            
            if existing_lead:
                lead_id = existing_lead.id
            else:
                # Create new lead
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                domain = parsed_url.netloc or parsed_url.path
                test_email = f"assessment{int(time.time())}@{domain.replace('www.', '').replace('/', '').replace(':', '')}"
                
                lead_create = LeadCreate(
                    company=business_name or "Unknown Business",
                    email=test_email,
                    url=url,
                    source="assessment_ui",
                    description=f"Lead created for assessment from {url}"
                )
                
                db_lead = Lead(**lead_create.model_dump())
                db.add(db_lead)
                await db.commit()
                await db.refresh(db_lead)
                lead_id = db_lead.id
            
            # Execute assessment via Celery task
            task = full_assessment_orchestrator_task.delay(lead_id)
        
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
        from src.core.database import AsyncSessionLocal
        from src.models.lead import Assessment
        from sqlalchemy import select
        
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
            
            # Transform the result to match the format expected by the comprehensive UI
            if result and 'assessment_id' in result:
                # Get the assessment from the database
                async with AsyncSessionLocal() as session:
                    assessment_result = await session.execute(
                        select(Assessment).where(Assessment.id == result['assessment_id'])
                    )
                    assessment = assessment_result.scalar_one_or_none()
                    
                    if assessment:
                        # Get decomposed metrics from assessment_results table
                        from src.models.assessment_results import AssessmentResults
                        from src.api.v1.pagespeed_helpers import get_pagespeed_data_for_assessment
                        
                        assessment_results_query = await session.execute(
                            select(AssessmentResults).where(AssessmentResults.assessment_id == assessment.id)
                        )
                        assessment_results = assessment_results_query.scalar_one_or_none()
                        
                        # Get all 53 decomposed metrics if available
                        decomposed_metrics = {}
                        if assessment_results:
                            decomposed_metrics = assessment_results.get_all_metrics()
                        
                        # Get PageSpeed data from new tables
                        pagespeed_data = await get_pagespeed_data_for_assessment(session, assessment.id)
                        
                        # Build execution object with all component results
                        execution = {
                            "lead_id": assessment.lead_id,
                            "assessment_id": assessment.id,
                            "status": "completed",
                            "success_rate": 0.8,  # Calculate based on successful components
                            "successful_components": 6,  # Count successful components
                            "total_components": 8,  # Total component count
                            "total_duration_ms": result.get("duration_ms", 0),
                            "total_cost_cents": result.get("cost_cents", 0),
                            "overall_score": assessment.total_score or 0,
                            "decomposed_metrics": decomposed_metrics,  # Add all 53 metrics
                            
                            # Component results with proper status based on data presence
                            "pagespeed_result": {
                                "status": {"value": "success" if pagespeed_data.get("has_data") else "failed"},
                                "data": pagespeed_data if pagespeed_data.get("has_data") else assessment.pagespeed_data
                            },
                            "security_result": {
                                "status": {"value": "success" if assessment.security_headers else "failed"},
                                "data": assessment.security_headers
                            },
                            "gbp_result": {
                                "status": {"value": "success" if assessment.gbp_data else "failed"},
                                "data": assessment.gbp_data
                            },
                            "screenshots_result": {
                                "status": {"value": "failed"},  # Screenshots not stored in main assessment table
                                "data": {
                                    "desktop_screenshot": None,
                                    "mobile_screenshot": None
                                }
                            },
                            "semrush_result": {
                                "status": {"value": "success" if assessment.semrush_data else "failed"},
                                "data": assessment.semrush_data
                            },
                            "visual_analysis_result": {
                                "status": {"value": "success" if assessment.visual_analysis else "failed"},
                                "data": assessment.visual_analysis
                            },
                            "score_calculation_result": {
                                "status": {"value": "success" if assessment.llm_insights else "failed"},
                                "data": assessment.llm_insights  # Score calculation stored in llm_insights
                            },
                            "content_generation_result": {
                                "status": {"value": "success" if assessment.llm_insights else "failed"},
                                "data": assessment.llm_insights  # Marketing content also in llm_insights
                            }
                        }
                        
                        # Count actual successful components based on data presence
                        successful = 0
                        total = 0
                        
                        # Check each component for data
                        components = [
                            ("pagespeed_data", assessment.pagespeed_data),
                            ("security_headers", assessment.security_headers),
                            ("gbp_data", assessment.gbp_data),
                            ("semrush_data", assessment.semrush_data),
                            ("visual_analysis", assessment.visual_analysis),
                            ("llm_insights", assessment.llm_insights)
                        ]
                        
                        for name, data in components:
                            total += 1
                            if data is not None:
                                successful += 1
                        
                        # Add screenshots and marketing content to total
                        total += 2  # screenshots and content generation
                        
                        execution["successful_components"] = successful
                        execution["total_components"] = total
                        execution["success_rate"] = successful / total if total > 0 else 0
                        
                        return {
                            "task_id": task_id,
                            "status": "completed",
                            "message": "Assessment completed successfully",
                            "result": {
                                "execution": execution
                            }
                        }
            
            # Fallback to original result if not in expected format
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


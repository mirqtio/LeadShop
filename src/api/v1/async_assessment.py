"""
Async assessment API endpoints
Replaces Celery-based endpoints with direct async execution
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any, Optional
import logging
import time

from src.assessment.async_orchestrator import orchestrator
from src.core.database import AsyncSessionLocal
from src.models.lead import Lead
from src.schemas.lead import LeadCreate
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/async-assessment", tags=["async-assessment"])

class AssessmentRequest(BaseModel):
    """Assessment execution request"""
    url: HttpUrl
    business_name: Optional[str] = None
    address: Optional[str] = None

class AssessmentResponse(BaseModel):
    """Assessment execution response"""
    task_id: str
    status: str
    message: str

@router.post("/execute", response_model=AssessmentResponse)
async def execute_assessment(
    request: AssessmentRequest,
    background_tasks: BackgroundTasks
):
    """Execute website assessment using async orchestrator"""
    try:
        url = str(request.url)
        business_name = request.business_name or "Unknown Business"
        
        # Create lead in database
        async with AsyncSessionLocal() as db:
            # Check if lead exists
            existing_lead = await db.execute(
                select(Lead).where(Lead.url == url).order_by(Lead.created_at.desc()).limit(1)
            )
            existing_lead = existing_lead.scalar_one_or_none()
            
            if existing_lead:
                lead_id = existing_lead.id
            else:
                # Create new lead
                from urllib.parse import urlparse
                
                parsed_url = urlparse(url)
                domain = parsed_url.netloc or parsed_url.path
                test_email = f"assessment{int(time.time())}@{domain.replace('www.', '').replace('/', '').replace(':', '')}"
                
                lead_create = LeadCreate(
                    company=business_name,
                    email=test_email,
                    url=url,
                    address=request.address,
                    source="async_assessment",
                    description=f"Lead created for assessment from {url}"
                )
                
                db_lead = Lead(**lead_create.model_dump())
                db.add(db_lead)
                await db.commit()
                await db.refresh(db_lead)
                lead_id = db_lead.id
        
        # Execute assessment in background
        task_id = f"async-{lead_id}-{int(time.time())}"
        
        # Run assessment in background
        background_tasks.add_task(
            orchestrator.execute_assessment,
            lead_id=lead_id
        )
        
        return AssessmentResponse(
            task_id=task_id,
            status="started",
            message=f"Assessment started for {url}"
        )
        
    except Exception as e:
        logger.error(f"Failed to start assessment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start assessment: {str(e)}"
        )

@router.get("/status/{task_id}")
async def get_assessment_status(task_id: str):
    """Get assessment task status"""
    try:
        # For now, check if assessment exists in database
        # In production, we'd track this properly
        parts = task_id.split("-")
        if len(parts) >= 2:
            lead_id = int(parts[1])
            
            async with AsyncSessionLocal() as db:
                from src.models.lead import Assessment
                from sqlalchemy import select, desc
                
                result = await db.execute(
                    select(Assessment)
                    .where(Assessment.lead_id == lead_id)
                    .order_by(desc(Assessment.created_at))
                    .limit(1)
                )
                assessment = result.scalar_one_or_none()
                
                if assessment:
                    # Check if assessment has data
                    has_data = any([
                        assessment.pagespeed_data,
                        assessment.security_headers,
                        assessment.semrush_data,
                        assessment.gbp_data,
                        assessment.visual_analysis
                    ])
                    
                    if has_data:
                        return {
                            "task_id": task_id,
                            "status": "completed",
                            "assessment_id": assessment.id,
                            "message": "Assessment completed"
                        }
                    else:
                        return {
                            "task_id": task_id,
                            "status": "running",
                            "message": "Assessment in progress"
                        }
        
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Assessment pending"
        }
        
    except Exception as e:
        logger.error(f"Failed to get task status: {str(e)}")
        return {
            "task_id": task_id,
            "status": "error",
            "message": str(e)
        }
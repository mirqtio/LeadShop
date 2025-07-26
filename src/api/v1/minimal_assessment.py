"""
Minimal assessment API endpoints for demo
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any, Optional
import logging
import time

import sys
sys.path.append('/app')
from minimal_async_orchestrator import minimal_orchestrator

from src.core.database import AsyncSessionLocal
from src.models.lead import Lead
from src.schemas.lead import LeadCreate
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/minimal-assessment", tags=["minimal-assessment"])

class AssessmentRequest(BaseModel):
    """Assessment execution request"""
    url: HttpUrl
    business_name: Optional[str] = None

class AssessmentResponse(BaseModel):
    """Assessment execution response"""
    task_id: str
    status: str
    message: str

@router.post("/execute", response_model=AssessmentResponse)
async def execute_minimal_assessment(
    request: AssessmentRequest,
    background_tasks: BackgroundTasks
):
    """Execute minimal assessment with working components only"""
    try:
        url = str(request.url)
        business_name = request.business_name or "Test Business"
        
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
                test_email = f"minimal{int(time.time())}@{domain.replace('www.', '').replace('/', '').replace(':', '')}"
                
                lead_create = LeadCreate(
                    company=business_name,
                    email=test_email,
                    url=url,
                    source="minimal_assessment"
                )
                
                db_lead = Lead(**lead_create.model_dump())
                db.add(db_lead)
                await db.commit()
                await db.refresh(db_lead)
                lead_id = db_lead.id
        
        # Execute assessment in background
        task_id = f"minimal-{lead_id}-{int(time.time())}"
        
        # Run assessment in background
        background_tasks.add_task(
            minimal_orchestrator.execute_assessment,
            lead_id=lead_id
        )
        
        return AssessmentResponse(
            task_id=task_id,
            status="started",
            message=f"Minimal assessment started for {url} (PageSpeed + Security only)"
        )
        
    except Exception as e:
        logger.error(f"Failed to start assessment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start assessment: {str(e)}"
        )

@router.get("/status/{task_id}")
async def get_minimal_assessment_status(task_id: str):
    """Get minimal assessment task status"""
    try:
        # Check orchestrator status
        status_info = minimal_orchestrator.get_task_status(task_id)
        if status_info["status"] != "not_found":
            return {
                "task_id": task_id,
                "status": status_info["status"],
                "progress": status_info.get("progress", 0),
                "assessment_id": status_info.get("assessment_id"),
                "message": f"Assessment {status_info['status']}"
            }
        
        # Parse task_id to get lead_id
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
                
                if assessment and assessment.total_score is not None:
                    return {
                        "task_id": task_id,
                        "status": "completed",
                        "assessment_id": assessment.id,
                        "score": assessment.total_score,
                        "message": f"Assessment completed with score {assessment.total_score:.1f}"
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
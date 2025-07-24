"""
PRP-002: Assessment Orchestrator
Main coordinator for parallel assessment execution pipeline
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from celery import group, chord
from celery.exceptions import Retry

from src.core.database import get_db
from src.models.lead import Lead, Assessment
from src.core.logging import get_logger
from .utils import (
    update_assessment_field,
    update_assessment_status,
    sync_update_assessment_status,
    ASSESSMENT_STATUS,
    AssessmentError
)

logger = get_logger(__name__)

class AssessmentNotFoundError(AssessmentError):
    """Raised when assessment record not found"""
    pass

async def get_or_create_assessment(lead_id: int) -> Assessment:
    """
    Get existing assessment or create new one for lead
    
    Args:
        lead_id: Database ID of the lead
        
    Returns:
        Assessment instance
        
    Raises:
        AssessmentError: If lead not found or database error
    """
    try:
        from src.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            # Check if lead exists
            lead_result = await db.execute(select(Lead).where(Lead.id == lead_id))
            lead = lead_result.scalar_one_or_none()
            
            if not lead:
                raise AssessmentError(f"Lead {lead_id} not found")
            
            # Check for existing assessment
            assessment_result = await db.execute(
                select(Assessment).where(Assessment.lead_id == lead_id)
            )
            assessment = assessment_result.scalar_one_or_none()
            
            if assessment:
                logger.info(f"Found existing assessment {assessment.id} for lead {lead_id}")
                return assessment
            
            # Create new assessment
            assessment = Assessment(
                lead_id=lead_id,
                status=ASSESSMENT_STATUS['PENDING'],
                created_at=datetime.now(timezone.utc)
            )
            
            db.add(assessment)
            await db.commit()
            await db.refresh(assessment)
            
            logger.info(f"Created new assessment {assessment.id} for lead {lead_id}")
            return assessment
            
    except Exception as exc:
        logger.error(f"Failed to get/create assessment for lead {lead_id}: {exc}")
        raise AssessmentError(f"Database error: {exc}")


def sync_get_or_create_assessment(lead_id: int) -> Assessment:
    """
    Synchronous version of get_or_create_assessment for Celery workers
    """
    try:
        from src.core.database import SyncSessionLocal
        from sqlalchemy import select
        
        with SyncSessionLocal() as db:
            # Check if lead exists
            lead_result = db.execute(select(Lead).where(Lead.id == lead_id))
            lead = lead_result.scalar_one_or_none()
            
            if not lead:
                raise AssessmentError(f"Lead {lead_id} not found")
            
            # Check for existing assessment
            assessment_result = db.execute(
                select(Assessment).where(Assessment.lead_id == lead_id)
            )
            assessment = assessment_result.scalar_one_or_none()
            
            if assessment:
                logger.info(f"Found existing assessment {assessment.id} for lead {lead_id}")
                return assessment
            
            # Create new assessment
            assessment = Assessment(
                lead_id=lead_id,
                status=ASSESSMENT_STATUS['PENDING'],
                created_at=datetime.now(timezone.utc)
            )
            
            db.add(assessment)
            db.commit()
            db.refresh(assessment)
            
            logger.info(f"Created new assessment {assessment.id} for lead {lead_id}")
            return assessment
            
    except Exception as exc:
        logger.error(f"Failed to get/create assessment for lead {lead_id}: {exc}")
        raise AssessmentError(f"Database error: {exc}")


def coordinate_assessment_task(self, lead_id: int) -> Dict[str, Any]:
    """
    Orchestrate complete assessment pipeline for a business lead.
    
    This is the main entry point that coordinates parallel execution of all
    assessment types with proper error handling and status tracking.
    
    Args:
        lead_id: Database ID of the lead to assess
        
    Returns:
        Dict containing assessment coordination metadata
        
    Raises:
        AssessmentError: If coordination fails
        Retry: If retryable error occurs
    """
    start_time = datetime.now(timezone.utc)
    
    try:
        logger.info(f"Starting assessment coordination for lead {lead_id}")
        
        # Import here to avoid circular imports
        from .tasks import (
            pagespeed_task,
            security_task,
            gbp_task,
            semrush_task,
            visual_task,
            llm_analysis_task,
            aggregate_results
        )
        
        # Get or create assessment record using sync wrappers
        assessment = sync_get_or_create_assessment(lead_id)
        
        # Update status to in_progress
        sync_update_assessment_status(
            lead_id, 
            ASSESSMENT_STATUS['IN_PROGRESS']
        )
        
        # Create parallel task group for all assessment types
        assessment_tasks = group([
            pagespeed_task.s(lead_id),
            security_task.s(lead_id),
            gbp_task.s(lead_id),
            semrush_task.s(lead_id),
            visual_task.s(lead_id),
        ])
        
        # Execute parallel assessments with callback for aggregation
        # Note: LLM analysis runs after other assessments complete
        chord_result = chord(assessment_tasks)(
            aggregate_results.s(lead_id)
        )
        
        coordination_result = {
            "lead_id": lead_id,
            "assessment_id": assessment.id,
            "task_id": self.request.id,
            "chord_id": chord_result.id,
            "status": "coordinating",
            "started_at": start_time.isoformat(),
            "worker_id": self.request.hostname,
            "queue": self.request.delivery_info.get('routing_key', 'unknown')
        }
        
        logger.info(f"Assessment coordination started for lead {lead_id}, chord: {chord_result.id}")
        return coordination_result
        
    except Exception as exc:
        error_msg = f"Assessment coordination failed for lead {lead_id}: {exc}"
        logger.error(error_msg)
        
        # Update assessment status to failed
        try:
            sync_update_assessment_status(
                lead_id, 
                ASSESSMENT_STATUS['FAILED'],
                error_message=str(exc)
            )
        except Exception as db_exc:
            logger.error(f"Failed to update assessment status after coordination failure: {db_exc}")
        
        # Retry with exponential backoff if not at max retries
        if self.request.retries < 3:
            retry_countdown = 2 ** self.request.retries
            logger.warning(f"Retrying assessment coordination for lead {lead_id} in {retry_countdown}s (attempt {self.request.retries + 1}/3)")
            raise self.retry(countdown=retry_countdown, exc=exc)
        else:
            logger.error(f"Max retries reached for assessment coordination of lead {lead_id}")
            raise AssessmentError(error_msg)


# Apply celery task decorator - import at the bottom to avoid circular imports
try:
    from src.core.celery_app import celery_app
    coordinate_assessment = celery_app.task(
        bind=True,
        autoretry_for=(AssessmentError, ConnectionError, TimeoutError),
        retry_backoff=True,
        retry_jitter=True,
        retry_kwargs={'max_retries': 3},
        soft_time_limit=300,  # 5 minutes
        time_limit=600        # 10 minutes hard limit
    )(coordinate_assessment_task)
except ImportError as e:
    logger.error(f"Failed to register coordinate_assessment task: {e}")
    # Create a non-task version for testing
    coordinate_assessment = coordinate_assessment_task

def submit_assessment(lead_id: int) -> str:
    """
    Convenience function to submit assessment task
    
    Args:
        lead_id: Database ID of the lead to assess
        
    Returns:
        Task ID string for tracking
    """
    try:
        result = coordinate_assessment.delay(lead_id)
        logger.info(f"Submitted assessment task for lead {lead_id}: {result.id}")
        return result.id
    except Exception as exc:
        logger.error(f"Failed to submit assessment task for lead {lead_id}: {exc}")
        raise AssessmentError(f"Task submission failed: {exc}")

def get_assessment_status(task_id: str) -> Dict[str, Any]:
    """
    Get status of assessment task
    
    Args:
        task_id: Celery task ID
        
    Returns:
        Dict with task status information
    """
    try:
        from src.core.celery_app import celery_app
        result = celery_app.AsyncResult(task_id)
        
        status_info = {
            "task_id": task_id,
            "status": result.status,
            "ready": result.ready(),
            "successful": result.successful() if result.ready() else None,
            "failed": result.failed() if result.ready() else None,
        }
        
        if result.ready():
            if result.successful():
                status_info["result"] = result.result
            elif result.failed():
                status_info["error"] = str(result.info)
                status_info["traceback"] = result.traceback
        else:
            status_info["info"] = result.info
            
        return status_info
        
    except Exception as exc:
        logger.error(f"Failed to get assessment status for task {task_id}: {exc}")
        return {
            "task_id": task_id,
            "status": "ERROR",
            "error": f"Status check failed: {exc}"
        }
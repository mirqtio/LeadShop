"""
PRP-002: Assessment Utilities
Database utilities for updating assessment status and fields
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from src.core.database import get_db
from src.models.lead import Lead, Assessment
from src.core.logging import get_logger

logger = get_logger(__name__)

# Assessment status constants
ASSESSMENT_STATUS = {
    'PENDING': 'pending',
    'IN_PROGRESS': 'in_progress', 
    'COMPLETED': 'completed',
    'FAILED': 'failed',
    'VISUAL_COMPLETED': 'visual_completed',
    'SCORING_COMPLETED': 'scoring_completed',
    'CONTENT_COMPLETED': 'content_completed',
    'SETUP_COMPLETED': 'setup_completed'
}

class AssessmentError(Exception):
    """Custom exception for assessment errors"""
    pass

async def update_assessment_status(
    lead_id: str, 
    status: str, 
    error_message: Optional[str] = None,
    completed_at: Optional[datetime] = None
) -> bool:
    """
    Update assessment status with optional error message
    
    Args:
        lead_id: The lead ID to update
        status: New status value
        error_message: Optional error message if status is failed
        completed_at: Optional completion timestamp
        
    Returns:
        bool: True if update was successful
        
    Raises:
        AssessmentError: If lead not found or update fails
    """
    try:
        async with get_db() as session:
            # First verify the lead exists
            lead_query = select(Lead).where(Lead.id == lead_id)
            result = await session.execute(lead_query)
            lead = result.scalar_one_or_none()
            
            if not lead:
                raise AssessmentError(f"Lead {lead_id} not found")
            
            # Prepare update data
            update_data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc)
            }
            
            if error_message:
                update_data["error_message"] = error_message
                
            if completed_at:
                update_data["completed_at"] = completed_at
            elif status == ASSESSMENT_STATUS['COMPLETED']:
                update_data["completed_at"] = datetime.now(timezone.utc)
            
            # Update assessment via Lead relationship
            update_query = (
                update(Assessment)
                .where(Assessment.lead_id == lead_id)
                .values(**update_data)
            )
            
            await session.execute(update_query)
            await session.commit()
            
            logger.info(f"Updated assessment status for lead {lead_id}: {status}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to update assessment status for lead {lead_id}: {e}")
        raise AssessmentError(f"Database update failed: {e}")

async def update_assessment_field(
    lead_id: str, 
    field_name: str, 
    field_value: Any,
    merge_dict: bool = False
) -> bool:
    """
    Update a specific field in the assessment data
    
    Args:
        lead_id: The lead ID to update
        field_name: Name of the field to update
        field_value: Value to set for the field
        merge_dict: If True and field_value is dict, merge with existing data
        
    Returns:
        bool: True if update was successful
        
    Raises:
        AssessmentError: If lead not found or update fails
    """
    try:
        async with get_db() as session:
            # Get current assessment
            assessment_query = (
                select(Assessment)
                .where(Assessment.lead_id == lead_id)
            )
            result = await session.execute(assessment_query)
            assessment = result.scalar_one_or_none()
            
            if not assessment:
                raise AssessmentError(f"Assessment for lead {lead_id} not found")
            
            # Handle dictionary merging
            if merge_dict and isinstance(field_value, dict):
                current_data = getattr(assessment, field_name) or {}
                if isinstance(current_data, dict):
                    current_data.update(field_value)
                    field_value = current_data
            
            # Update the field
            update_query = (
                update(Assessment)
                .where(Assessment.lead_id == lead_id)
                .values({
                    field_name: field_value,
                    "updated_at": datetime.now(timezone.utc)
                })
            )
            
            await session.execute(update_query)
            await session.commit()
            
            logger.debug(f"Updated assessment field {field_name} for lead {lead_id}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to update assessment field {field_name} for lead {lead_id}: {e}")
        raise AssessmentError(f"Field update failed: {e}")
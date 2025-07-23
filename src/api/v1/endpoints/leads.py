"""
LeadFactory Lead API Endpoints - PRP-001 Implementation
FastAPI routes for Lead CRUD operations with proper error handling
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
import logging

from src.core.database import get_db
from src.models.lead import Lead, Company, LeadStatus
from src.schemas.lead import (
    LeadCreate,
    LeadUpdate,
    LeadResponse,
    LeadWithAssessments,
    LeadQueryParams
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ========================================
# Lead CRUD Operations
# ========================================

@router.post("/", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    lead_data: LeadCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new lead
    
    - **email**: Lead's email address (required, must be unique)
    - **first_name**: Lead's first name (optional)
    - **last_name**: Lead's last name (optional)
    - **phone**: Lead's phone number (optional)
    - **company_id**: Associated company ID (optional)
    - **source**: Lead source (e.g., 'website_form', 'linkedin') (optional)
    - **notes**: Additional notes (optional)
    - **tags**: Custom tags as key-value pairs (optional)
    """
    try:
        # Check if email already exists
        existing_lead = await db.execute(
            select(Lead).where(Lead.email == lead_data.email)
        )
        if existing_lead.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lead with email '{lead_data.email}' already exists"
            )
        
        # Validate company exists if provided
        if lead_data.company_id:
            company_result = await db.execute(
                select(Company).where(Company.id == lead_data.company_id)
            )
            if not company_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Company with ID '{lead_data.company_id}' not found"
                )
        
        # Create new lead
        lead = Lead(**lead_data.model_dump())
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        
        logger.info(f"Created new lead: {lead.id} ({lead.email})")
        return lead
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating lead: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create lead"
        )


@router.get("/", response_model=List[LeadResponse])
async def list_leads(
    status_filter: Optional[LeadStatus] = Query(None, alias="status"),
    is_qualified: Optional[bool] = Query(None),
    is_active: Optional[bool] = Query(True),
    company_id: Optional[UUID] = Query(None),
    source: Optional[str] = Query(None),
    min_score: Optional[int] = Query(None, ge=0, le=100),
    max_score: Optional[int] = Query(None, ge=0, le=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    List leads with optional filtering
    
    - **status**: Filter by lead status
    - **is_qualified**: Filter by qualification status
    - **is_active**: Filter by active status (default: true)
    - **company_id**: Filter by company ID
    - **source**: Filter by lead source
    - **min_score**: Minimum lead score (0-100)
    - **max_score**: Maximum lead score (0-100)
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return (max: 100)
    """
    try:
        # Validate score range
        if min_score is not None and max_score is not None and min_score > max_score:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="min_score must be less than or equal to max_score"
            )
        
        # Build query with filters
        query = select(Lead).options(selectinload(Lead.company))
        
        conditions = []
        if status_filter is not None:
            conditions.append(Lead.status == status_filter)
        if is_qualified is not None:
            conditions.append(Lead.is_qualified == is_qualified)
        if is_active is not None:
            conditions.append(Lead.is_active == is_active)
        if company_id is not None:
            conditions.append(Lead.company_id == company_id)
        if source is not None:
            conditions.append(Lead.source == source)
        if min_score is not None:
            conditions.append(Lead.score >= min_score)
        if max_score is not None:
            conditions.append(Lead.score <= max_score)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Apply pagination and ordering
        query = query.order_by(Lead.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        leads = result.scalars().all()
        
        return leads
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing leads: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve leads"
        )


@router.get("/{lead_id}", response_model=LeadWithAssessments)
async def get_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific lead by ID with assessments
    
    Returns the lead with all associated assessments and company information.
    """
    try:
        query = select(Lead).options(
            selectinload(Lead.assessments),
            selectinload(Lead.company)
        ).where(Lead.id == lead_id)
        
        result = await db.execute(query)
        lead = result.scalar_one_or_none()
        
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lead with ID '{lead_id}' not found"
            )
        
        return lead
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving lead {lead_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve lead"
        )


@router.put("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: UUID,
    lead_data: LeadUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a specific lead
    
    All fields are optional. Only provided fields will be updated.
    """
    try:
        # Get existing lead
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lead with ID '{lead_id}' not found"
            )
        
        # Check email uniqueness if email is being updated
        if lead_data.email and lead_data.email != lead.email:
            existing_email = await db.execute(
                select(Lead).where(
                    and_(Lead.email == lead_data.email, Lead.id != lead_id)
                )
            )
            if existing_email.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Email '{lead_data.email}' is already in use"
                )
        
        # Validate company exists if provided
        if lead_data.company_id:
            company_result = await db.execute(
                select(Company).where(Company.id == lead_data.company_id)
            )
            if not company_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Company with ID '{lead_data.company_id}' not found"
                )
        
        # Update lead fields
        update_data = lead_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(lead, field, value)
        
        await db.commit()
        await db.refresh(lead)
        
        logger.info(f"Updated lead: {lead.id} ({lead.email})")
        return lead
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating lead {lead_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update lead"
        )


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a specific lead
    
    This will also delete all associated assessments due to cascade delete.
    """
    try:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lead with ID '{lead_id}' not found"
            )
        
        await db.delete(lead)
        await db.commit()
        
        logger.info(f"Deleted lead: {lead_id} ({lead.email})")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting lead {lead_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete lead"
        )


# ========================================
# Additional Lead Operations
# ========================================

@router.post("/{lead_id}/qualify", response_model=LeadResponse)
async def qualify_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a lead as qualified
    
    Updates the lead status to 'qualified' and sets is_qualified to True.
    """
    try:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lead with ID '{lead_id}' not found"
            )
        
        lead.status = LeadStatus.QUALIFIED
        lead.is_qualified = True
        
        await db.commit()
        await db.refresh(lead)
        
        logger.info(f"Qualified lead: {lead.id} ({lead.email})")
        return lead
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error qualifying lead {lead_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to qualify lead"
        )


@router.post("/{lead_id}/convert", response_model=LeadResponse)
async def convert_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a lead as converted
    
    Updates the lead status to 'converted'. Lead must be qualified first.
    """
    try:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lead with ID '{lead_id}' not found"
            )
        
        if not lead.is_qualified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lead must be qualified before conversion"
            )
        
        lead.status = LeadStatus.CONVERTED
        
        await db.commit()
        await db.refresh(lead)
        
        logger.info(f"Converted lead: {lead.id} ({lead.email})")
        return lead
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error converting lead {lead_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to convert lead"
        )


@router.get("/search/email/{email}", response_model=LeadResponse)
async def search_lead_by_email(
    email: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Search for a lead by email address
    
    Returns the lead if found, otherwise returns 404.
    """
    try:
        result = await db.execute(
            select(Lead).options(selectinload(Lead.company))
            .where(Lead.email == email.lower())
        )
        lead = result.scalar_one_or_none()
        
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lead with email '{email}' not found"
            )
        
        return lead
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching lead by email {email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search lead"
        )
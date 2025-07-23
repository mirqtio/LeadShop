"""
PRP-001: Lead CRUD API Endpoints
FastAPI routes for lead management with validation and error handling
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from src.core.database import get_db
from src.models.lead import Lead, Assessment, Sale
from src.schemas.lead import (
    LeadCreate, LeadUpdate, LeadResponse, LeadWithAssessments,
    LeadListResponse
)
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("/", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    *,
    session: AsyncSession = Depends(get_db),
    lead_data: LeadCreate
) -> Lead:
    """
    Create a new business lead with validation
    
    - **company**: Company name (required)
    - **email**: Business email address (required, unique)
    - **source**: Lead acquisition source (required)
    - **phone**: Phone number (optional)
    - **url**: Company website URL (optional)
    - **address**, **city**, **state**, **zip_code**: Address components
    - **naics_code**, **sic_code**: Industry classification codes
    - **employee_size**, **sales_volume**: Business size metrics
    - **quality_score**: Lead quality score (0-1)
    """
    logger.info("Creating new lead", email=lead_data.email, company=lead_data.company)
    
    try:
        # Check for duplicate email
        existing_lead = await session.execute(
            select(Lead).where(Lead.email == lead_data.email)
        )
        existing = existing_lead.scalar_one_or_none()
        
        if existing:
            logger.warning("Duplicate email attempted", email=lead_data.email)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lead with this email already exists"
            )
        
        # Create new lead
        lead_dict = lead_data.model_dump()
        db_lead = Lead(**lead_dict)
        
        session.add(db_lead)
        await session.commit()
        await session.refresh(db_lead)
        
        logger.info(
            "Lead created successfully",
            lead_id=db_lead.id,
            email=db_lead.email,
            company=db_lead.company
        )
        
        return db_lead
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create lead", error=str(e), email=lead_data.email)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create lead"
        )


@router.get("/{lead_id}", response_model=LeadWithAssessments)
async def get_lead(
    *,
    session: AsyncSession = Depends(get_db),
    lead_id: int
) -> Lead:
    """
    Retrieve lead with assessment history and sales data
    
    Returns complete lead information including:
    - Basic lead data (company, email, contact info)
    - All associated assessments with scores and data
    - Sales history and revenue attribution
    """
    logger.debug("Retrieving lead", lead_id=lead_id)
    
    try:
        # Query lead with relationships
        result = await session.execute(
            select(Lead)
            .options(
                selectinload(Lead.assessments),
                selectinload(Lead.sales)
            )
            .where(Lead.id == lead_id)
        )
        lead = result.scalar_one_or_none()
        
        if not lead:
            logger.warning("Lead not found", lead_id=lead_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead not found"
            )
        
        logger.debug(
            "Lead retrieved successfully",
            lead_id=lead_id,
            assessments_count=len(lead.assessments),
            sales_count=len(lead.sales)
        )
        
        return lead
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve lead", error=str(e), lead_id=lead_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve lead"
        )


@router.put("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    *,
    session: AsyncSession = Depends(get_db),
    lead_id: int,
    lead_update: LeadUpdate
) -> Lead:
    """
    Update lead information
    
    Only provided fields will be updated. Email updates are not allowed
    to maintain data integrity and prevent duplicate key violations.
    """
    logger.info("Updating lead", lead_id=lead_id)
    
    try:
        # Get existing lead
        result = await session.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        
        if not lead:
            logger.warning("Lead not found for update", lead_id=lead_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead not found"
            )
        
        # Update only provided fields
        update_data = lead_update.model_dump(exclude_unset=True)
        
        if not update_data:
            logger.warning("No update data provided", lead_id=lead_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update data provided"
            )
        
        for field, value in update_data.items():
            setattr(lead, field, value)
        
        await session.commit()
        await session.refresh(lead)
        
        logger.info(
            "Lead updated successfully",
            lead_id=lead_id,
            fields_updated=list(update_data.keys())
        )
        
        return lead
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update lead", error=str(e), lead_id=lead_id)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update lead"
        )


@router.get("/", response_model=LeadListResponse)
async def list_leads(
    *,
    session: AsyncSession = Depends(get_db),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    source: Optional[str] = Query(None, description="Filter by lead source"),
    min_quality_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum quality score"),
    company: Optional[str] = Query(None, description="Filter by company name (partial match)"),
    city: Optional[str] = Query(None, description="Filter by city"),
    state: Optional[str] = Query(None, description="Filter by state")
) -> LeadListResponse:
    """
    List leads with filtering and pagination
    
    Supports filtering by:
    - **source**: Lead acquisition source
    - **min_quality_score**: Minimum lead quality score
    - **company**: Company name (partial text search)
    - **city**: City name
    - **state**: State abbreviation
    
    Results are paginated using offset/limit parameters.
    """
    logger.debug(
        "Listing leads",
        offset=offset,
        limit=limit,
        source=source,
        min_quality_score=min_quality_score
    )
    
    try:
        # Build query with filters
        query = select(Lead)
        count_query = select(func.count(Lead.id))
        
        # Apply filters
        if source:
            query = query.where(Lead.source == source)
            count_query = count_query.where(Lead.source == source)
            
        if min_quality_score is not None:
            query = query.where(Lead.quality_score >= min_quality_score)
            count_query = count_query.where(Lead.quality_score >= min_quality_score)
            
        if company:
            query = query.where(Lead.company.ilike(f"%{company}%"))
            count_query = count_query.where(Lead.company.ilike(f"%{company}%"))
            
        if city:
            query = query.where(Lead.city.ilike(f"%{city}%"))
            count_query = count_query.where(Lead.city.ilike(f"%{city}%"))
            
        if state:
            query = query.where(Lead.state == state.upper())
            count_query = count_query.where(Lead.state == state.upper())
        
        # Get total count
        total_result = await session.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination and execute
        query = query.offset(offset).limit(limit).order_by(Lead.created_at.desc())
        result = await session.execute(query)
        leads = result.scalars().all()
        
        has_more = (offset + limit) < total
        
        response = LeadListResponse(
            items=leads,
            total=total,
            offset=offset,
            limit=limit,
            has_more=has_more
        )
        
        logger.debug(
            "Leads listed successfully",
            count=len(leads),
            total=total,
            has_more=has_more
        )
        
        return response
        
    except Exception as e:
        logger.error("Failed to list leads", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list leads"
        )


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    *,
    session: AsyncSession = Depends(get_db),
    lead_id: int
) -> None:
    """
    Delete lead with cascade handling
    
    This will also delete all associated assessments and sales records
    due to the CASCADE foreign key constraints. Use with caution in
    production environments.
    """
    logger.info("Deleting lead", lead_id=lead_id)
    
    try:
        # Get lead to verify it exists
        result = await session.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        
        if not lead:
            logger.warning("Lead not found for deletion", lead_id=lead_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead not found"
            )
        
        # Delete lead (cascades to assessments and sales)
        await session.delete(lead)
        await session.commit()
        
        logger.info("Lead deleted successfully", lead_id=lead_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete lead", error=str(e), lead_id=lead_id)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete lead"
        )
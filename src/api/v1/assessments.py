"""
PRP-001: Assessment CRUD API Endpoints
FastAPI routes for assessment management and pipeline integration
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from src.core.database import get_db
from src.models.lead import Lead, Assessment
from src.schemas.lead import (
    AssessmentCreate, AssessmentUpdate, AssessmentResponse,
    AssessmentListResponse
)
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.post("/", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    *,
    session: AsyncSession = Depends(get_db),
    assessment_data: AssessmentCreate
) -> Assessment:
    """
    Store pipeline assessment results
    
    Creates a new assessment record for a lead with technical scores
    and detailed analysis data from various assessment tools:
    
    - **lead_id**: Associated lead (required)
    - **pagespeed_score**: PageSpeed performance score (0-100)
    - **security_score**: Security analysis score (0-100)
    - **mobile_score**: Mobile optimization score (0-100)
    - **seo_score**: SEO analysis score (0-100)
    - **pagespeed_data**: Raw PageSpeed API response
    - **security_headers**: Security headers analysis
    - **gbp_data**: Google Business Profile data
    - **semrush_data**: SEMrush analysis results
    - **visual_analysis**: Visual analysis results
    - **llm_insights**: LLM-generated insights and recommendations
    """
    logger.info("Creating new assessment", lead_id=assessment_data.lead_id)
    
    try:
        # Verify lead exists
        lead_result = await session.execute(
            select(Lead).where(Lead.id == assessment_data.lead_id)
        )
        lead = lead_result.scalar_one_or_none()
        
        if not lead:
            logger.warning("Lead not found for assessment", lead_id=assessment_data.lead_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead not found"
            )
        
        # Create assessment
        assessment_dict = assessment_data.model_dump()
        db_assessment = Assessment(**assessment_dict)
        
        session.add(db_assessment)
        await session.commit()
        await session.refresh(db_assessment)
        
        logger.info(
            "Assessment created successfully",
            assessment_id=db_assessment.id,
            lead_id=db_assessment.lead_id,
            status=db_assessment.status
        )
        
        return db_assessment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to create assessment",
            error=str(e),
            lead_id=assessment_data.lead_id
        )
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create assessment"
        )


@router.get("/{assessment_id}", response_model=AssessmentResponse)
async def get_assessment(
    *,
    session: AsyncSession = Depends(get_db),
    assessment_id: int
) -> Assessment:
    """
    Retrieve assessment by ID
    
    Returns complete assessment data including all technical scores,
    raw analysis data, and processing metadata.
    """
    logger.debug("Retrieving assessment", assessment_id=assessment_id)
    
    try:
        result = await session.execute(
            select(Assessment).where(Assessment.id == assessment_id)
        )
        assessment = result.scalar_one_or_none()
        
        if not assessment:
            logger.warning("Assessment not found", assessment_id=assessment_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not found"
            )
        
        logger.debug("Assessment retrieved successfully", assessment_id=assessment_id)
        return assessment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve assessment", error=str(e), assessment_id=assessment_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve assessment"
        )


@router.get("/lead/{lead_id}", response_model=List[AssessmentResponse])
async def get_lead_assessments(
    *,
    session: AsyncSession = Depends(get_db),
    lead_id: int
) -> List[Assessment]:
    """
    Retrieve all assessments for a specific lead
    
    Returns chronological list of all assessment attempts for the lead,
    useful for tracking assessment history and identifying trends.
    """
    logger.debug("Retrieving assessments for lead", lead_id=lead_id)
    
    try:
        # Verify lead exists
        lead_result = await session.execute(select(Lead).where(Lead.id == lead_id))
        lead = lead_result.scalar_one_or_none()
        
        if not lead:
            logger.warning("Lead not found for assessments query", lead_id=lead_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead not found"
            )
        
        # Get assessments
        result = await session.execute(
            select(Assessment)
            .where(Assessment.lead_id == lead_id)
            .order_by(Assessment.created_at.desc())
        )
        assessments = result.scalars().all()
        
        logger.debug(
            "Assessments retrieved successfully",
            lead_id=lead_id,
            count=len(assessments)
        )
        
        return assessments
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve lead assessments", error=str(e), lead_id=lead_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve assessments"
        )


@router.put("/{assessment_id}", response_model=AssessmentResponse)
async def update_assessment(
    *,
    session: AsyncSession = Depends(get_db),
    assessment_id: int,
    assessment_update: AssessmentUpdate
) -> Assessment:
    """
    Update assessment results
    
    Typically used by assessment pipeline processes to update scores,
    data, and status as analysis completes. Supports partial updates.
    """
    logger.info("Updating assessment", assessment_id=assessment_id)
    
    try:
        # Get existing assessment
        result = await session.execute(
            select(Assessment).where(Assessment.id == assessment_id)
        )
        assessment = result.scalar_one_or_none()
        
        if not assessment:
            logger.warning("Assessment not found for update", assessment_id=assessment_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not found"
            )
        
        # Update provided fields
        update_data = assessment_update.model_dump(exclude_unset=True)
        
        if not update_data:
            logger.warning("No update data provided", assessment_id=assessment_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update data provided"
            )
        
        for field, value in update_data.items():
            setattr(assessment, field, value)
        
        await session.commit()
        await session.refresh(assessment)
        
        logger.info(
            "Assessment updated successfully",
            assessment_id=assessment_id,
            fields_updated=list(update_data.keys())
        )
        
        return assessment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update assessment", error=str(e), assessment_id=assessment_id)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update assessment"
        )


@router.get("/", response_model=AssessmentListResponse)
async def list_assessments(
    *,
    session: AsyncSession = Depends(get_db),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    status: Optional[str] = Query(None, description="Filter by assessment status"),
    min_total_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum total score"),
    lead_id: Optional[int] = Query(None, description="Filter by lead ID")
) -> AssessmentListResponse:
    """
    List assessments with filtering and pagination
    
    Supports filtering by:
    - **status**: Assessment status (pending, in_progress, completed, failed)
    - **min_total_score**: Minimum composite score
    - **lead_id**: Specific lead ID
    
    Results are ordered by creation date (newest first).
    """
    logger.debug(
        "Listing assessments",
        offset=offset,
        limit=limit,
        status=status,
        min_total_score=min_total_score
    )
    
    try:
        # Build query with filters
        query = select(Assessment)
        count_query = select(func.count(Assessment.id))
        
        # Apply filters
        if status:
            query = query.where(Assessment.status == status)
            count_query = count_query.where(Assessment.status == status)
            
        if min_total_score is not None:
            query = query.where(Assessment.total_score >= min_total_score)
            count_query = count_query.where(Assessment.total_score >= min_total_score)
            
        if lead_id:
            query = query.where(Assessment.lead_id == lead_id)
            count_query = count_query.where(Assessment.lead_id == lead_id)
        
        # Get total count
        total_result = await session.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination and execute
        query = query.offset(offset).limit(limit).order_by(Assessment.created_at.desc())
        result = await session.execute(query)
        assessments = result.scalars().all()
        
        has_more = (offset + limit) < total
        
        response = AssessmentListResponse(
            items=assessments,
            total=total,
            offset=offset,
            limit=limit,
            has_more=has_more
        )
        
        logger.debug(
            "Assessments listed successfully",
            count=len(assessments),
            total=total,
            has_more=has_more
        )
        
        return response
        
    except Exception as e:
        logger.error("Failed to list assessments", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list assessments"
        )


@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assessment(
    *,
    session: AsyncSession = Depends(get_db),
    assessment_id: int
) -> None:
    """
    Delete assessment record
    
    Permanently removes assessment data. Use with caution as this
    will delete all associated analysis results and cannot be undone.
    """
    logger.info("Deleting assessment", assessment_id=assessment_id)
    
    try:
        # Get assessment to verify it exists
        result = await session.execute(
            select(Assessment).where(Assessment.id == assessment_id)
        )
        assessment = result.scalar_one_or_none()
        
        if not assessment:
            logger.warning("Assessment not found for deletion", assessment_id=assessment_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not found"
            )
        
        # Delete assessment
        await session.delete(assessment)
        await session.commit()
        
        logger.info("Assessment deleted successfully", assessment_id=assessment_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete assessment", error=str(e), assessment_id=assessment_id)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete assessment"
        )
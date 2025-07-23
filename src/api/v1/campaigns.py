"""
PRP-001: Campaign CRUD API Endpoints
FastAPI routes for email campaign management and revenue tracking
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.core.database import get_db
from src.models.lead import Campaign
from src.schemas.lead import (
    CampaignCreate, CampaignUpdate, CampaignResponse,
    CampaignListResponse
)
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("/", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    *,
    session: AsyncSession = Depends(get_db),
    campaign_data: CampaignCreate
) -> Campaign:
    """
    Create new email campaign
    
    Initializes a new campaign for lead conversion tracking:
    
    - **name**: Campaign name for identification
    - **subject_line**: Email subject line for the campaign
    - **send_date**: Scheduled send date (optional)
    - **leads_targeted**: Number of leads to target
    - **status**: Campaign status (draft, scheduled, etc.)
    
    Performance metrics will be updated as the campaign progresses.
    """
    logger.info("Creating new campaign", name=campaign_data.name)
    
    try:
        # Create campaign
        campaign_dict = campaign_data.model_dump()
        db_campaign = Campaign(**campaign_dict)
        
        session.add(db_campaign)
        await session.commit()
        await session.refresh(db_campaign)
        
        logger.info(
            "Campaign created successfully",
            campaign_id=db_campaign.id,
            name=db_campaign.name,
            leads_targeted=db_campaign.leads_targeted
        )
        
        return db_campaign
        
    except Exception as e:
        logger.error("Failed to create campaign", error=str(e), name=campaign_data.name)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create campaign"
        )


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    *,
    session: AsyncSession = Depends(get_db),
    campaign_id: int
) -> Campaign:
    """
    Retrieve campaign with calculated metrics
    
    Returns campaign data including:
    - Basic campaign information
    - Email performance metrics (sent, delivered, opened, clicked)
    - Revenue tracking (conversions, revenue generated)
    - Calculated rates (open rate, click rate, conversion rate, revenue per lead)
    """
    logger.debug("Retrieving campaign", campaign_id=campaign_id)
    
    try:
        result = await session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()
        
        if not campaign:
            logger.warning("Campaign not found", campaign_id=campaign_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
            )
        
        logger.debug("Campaign retrieved successfully", campaign_id=campaign_id)
        return campaign
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve campaign", error=str(e), campaign_id=campaign_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve campaign"
        )


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    *,
    session: AsyncSession = Depends(get_db),
    campaign_id: int,
    campaign_update: CampaignUpdate
) -> Campaign:
    """
    Update campaign metrics and information
    
    Typically used to update performance metrics as campaign progresses:
    - Email delivery statistics
    - Engagement metrics (opens, clicks)
    - Conversion and revenue data
    - Campaign status changes
    """
    logger.info("Updating campaign", campaign_id=campaign_id)
    
    try:
        # Get existing campaign
        result = await session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()
        
        if not campaign:
            logger.warning("Campaign not found for update", campaign_id=campaign_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
            )
        
        # Update provided fields
        update_data = campaign_update.model_dump(exclude_unset=True)
        
        if not update_data:
            logger.warning("No update data provided", campaign_id=campaign_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update data provided"
            )
        
        for field, value in update_data.items():
            setattr(campaign, field, value)
        
        await session.commit()
        await session.refresh(campaign)
        
        logger.info(
            "Campaign updated successfully",
            campaign_id=campaign_id,
            fields_updated=list(update_data.keys()),
            conversion_rate=campaign.conversion_rate
        )
        
        return campaign
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update campaign", error=str(e), campaign_id=campaign_id)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update campaign"
        )


@router.get("/", response_model=CampaignListResponse)
async def list_campaigns(
    *,
    session: AsyncSession = Depends(get_db),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    status: Optional[str] = Query(None, description="Filter by campaign status"),
    min_conversion_rate: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum conversion rate"),
    min_revenue: Optional[float] = Query(None, ge=0.0, description="Minimum revenue generated")
) -> CampaignListResponse:
    """
    List campaigns with filtering and pagination
    
    Supports filtering by:
    - **status**: Campaign status (draft, scheduled, sending, sent, completed)
    - **min_conversion_rate**: Minimum conversion rate (0.0-1.0)
    - **min_revenue**: Minimum revenue generated
    
    Results include calculated performance metrics for analysis.
    """
    logger.debug(
        "Listing campaigns",
        offset=offset,
        limit=limit,
        status=status,
        min_conversion_rate=min_conversion_rate
    )
    
    try:
        # Build query with filters
        query = select(Campaign)
        count_query = select(func.count(Campaign.id))
        
        # Apply filters
        if status:
            query = query.where(Campaign.status == status)
            count_query = count_query.where(Campaign.status == status)
            
        if min_revenue is not None:
            query = query.where(Campaign.revenue_generated >= min_revenue)
            count_query = count_query.where(Campaign.revenue_generated >= min_revenue)
        
        # Note: min_conversion_rate filter would require calculated field,
        # which is more complex in SQL. For now, we'll filter in Python
        # if needed, or implement as a computed column in the future.
        
        # Get total count
        total_result = await session.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination and execute
        query = query.offset(offset).limit(limit).order_by(Campaign.created_at.desc())
        result = await session.execute(query)
        campaigns = result.scalars().all()
        
        # Apply Python-based filtering for conversion rate if needed
        if min_conversion_rate is not None:
            campaigns = [c for c in campaigns if c.conversion_rate >= min_conversion_rate]
            # Adjust total count (this is approximate since we're filtering post-query)
            # In production, this should be implemented as a database-level filter
        
        has_more = (offset + limit) < total
        
        response = CampaignListResponse(
            items=campaigns,
            total=total,
            offset=offset,
            limit=limit,
            has_more=has_more
        )
        
        logger.debug(
            "Campaigns listed successfully",
            count=len(campaigns),
            total=total,
            has_more=has_more
        )
        
        return response
        
    except Exception as e:
        logger.error("Failed to list campaigns", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list campaigns"
        )


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    *,
    session: AsyncSession = Depends(get_db),
    campaign_id: int
) -> None:
    """
    Delete campaign
    
    Removes campaign record. Associated sales records will have their
    campaign_id set to NULL due to the SET NULL foreign key constraint.
    """
    logger.info("Deleting campaign", campaign_id=campaign_id)
    
    try:
        # Get campaign to verify it exists
        result = await session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()
        
        if not campaign:
            logger.warning("Campaign not found for deletion", campaign_id=campaign_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
            )
        
        # Delete campaign
        await session.delete(campaign)
        await session.commit()
        
        logger.info("Campaign deleted successfully", campaign_id=campaign_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete campaign", error=str(e), campaign_id=campaign_id)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete campaign"
        )
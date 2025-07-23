"""
PRP-001: Sales CRUD API Endpoints
FastAPI routes for revenue tracking and attribution
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.core.database import get_db
from src.models.lead import Lead, Campaign, Sale
from src.schemas.lead import (
    SaleCreate, SaleUpdate, SaleResponse
)
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/sales", tags=["sales"])


@router.post("/", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
async def create_sale(
    *,
    session: AsyncSession = Depends(get_db),
    sale_data: SaleCreate
) -> Sale:
    """
    Record new sale transaction
    
    Creates revenue attribution record linking lead acquisition
    through campaign to $399 report purchase:
    
    - **lead_id**: Associated lead (required)
    - **campaign_id**: Associated campaign (optional)
    - **amount**: Sale amount (typically $399.00)
    - **payment_method**: Payment processor used
    - **transaction_id**: External transaction reference
    - **attribution_source**: How the sale was attributed
    """
    logger.info(
        "Creating new sale",
        lead_id=sale_data.lead_id,
        amount=sale_data.amount,
        attribution_source=sale_data.attribution_source
    )
    
    try:
        # Verify lead exists
        lead_result = await session.execute(
            select(Lead).where(Lead.id == sale_data.lead_id)
        )
        lead = lead_result.scalar_one_or_none()
        
        if not lead:
            logger.warning("Lead not found for sale", lead_id=sale_data.lead_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead not found"
            )
        
        # Verify campaign exists if provided
        if sale_data.campaign_id:
            campaign_result = await session.execute(
                select(Campaign).where(Campaign.id == sale_data.campaign_id)
            )
            campaign = campaign_result.scalar_one_or_none()
            
            if not campaign:
                logger.warning("Campaign not found for sale", campaign_id=sale_data.campaign_id)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Campaign not found"
                )
        
        # Create sale
        sale_dict = sale_data.model_dump()
        db_sale = Sale(**sale_dict)
        
        session.add(db_sale)
        await session.commit()
        await session.refresh(db_sale)
        
        logger.info(
            "Sale created successfully",
            sale_id=db_sale.id,
            lead_id=db_sale.lead_id,
            amount=db_sale.amount
        )
        
        return db_sale
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to create sale",
            error=str(e),
            lead_id=sale_data.lead_id,
            amount=sale_data.amount
        )
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create sale"
        )


@router.get("/{sale_id}", response_model=SaleResponse)
async def get_sale(
    *,
    session: AsyncSession = Depends(get_db),
    sale_id: int
) -> Sale:
    """
    Retrieve sale transaction details
    
    Returns complete sale information including transaction details
    and attribution data for revenue tracking.
    """
    logger.debug("Retrieving sale", sale_id=sale_id)
    
    try:
        result = await session.execute(
            select(Sale).where(Sale.id == sale_id)
        )
        sale = result.scalar_one_or_none()
        
        if not sale:
            logger.warning("Sale not found", sale_id=sale_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sale not found"
            )
        
        logger.debug("Sale retrieved successfully", sale_id=sale_id)
        return sale
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve sale", error=str(e), sale_id=sale_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sale"
        )


@router.put("/{sale_id}", response_model=SaleResponse)
async def update_sale(
    *,
    session: AsyncSession = Depends(get_db),
    sale_id: int,
    sale_update: SaleUpdate
) -> Sale:
    """
    Update sale transaction
    
    Typically used to update transaction details, change status,
    or correct attribution information.
    """
    logger.info("Updating sale", sale_id=sale_id)
    
    try:
        # Get existing sale
        result = await session.execute(
            select(Sale).where(Sale.id == sale_id)
        )
        sale = result.scalar_one_or_none()
        
        if not sale:
            logger.warning("Sale not found for update", sale_id=sale_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sale not found"
            )
        
        # Update provided fields
        update_data = sale_update.model_dump(exclude_unset=True)
        
        if not update_data:
            logger.warning("No update data provided", sale_id=sale_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update data provided"
            )
        
        for field, value in update_data.items():
            setattr(sale, field, value)
        
        await session.commit()
        await session.refresh(sale)
        
        logger.info(
            "Sale updated successfully",
            sale_id=sale_id,
            fields_updated=list(update_data.keys())
        )
        
        return sale
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update sale", error=str(e), sale_id=sale_id)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update sale"
        )


@router.get("/", response_model=List[SaleResponse])
async def list_sales(
    *,
    session: AsyncSession = Depends(get_db),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    lead_id: Optional[int] = Query(None, description="Filter by lead ID"),
    campaign_id: Optional[int] = Query(None, description="Filter by campaign ID"),
    min_amount: Optional[float] = Query(None, ge=0.0, description="Minimum sale amount"),
    status: Optional[str] = Query(None, description="Filter by sale status"),
    attribution_source: Optional[str] = Query(None, description="Filter by attribution source")
) -> List[Sale]:
    """
    List sales with filtering and pagination
    
    Supports filtering by:
    - **lead_id**: Specific lead
    - **campaign_id**: Specific campaign
    - **min_amount**: Minimum sale amount
    - **status**: Sale status (pending, completed, refunded, failed)
    - **attribution_source**: Attribution source
    
    Results are ordered by creation date (newest first).
    """
    logger.debug(
        "Listing sales",
        offset=offset,
        limit=limit,
        lead_id=lead_id,
        campaign_id=campaign_id
    )
    
    try:
        # Build query with filters
        query = select(Sale)
        
        # Apply filters
        if lead_id:
            query = query.where(Sale.lead_id == lead_id)
            
        if campaign_id:
            query = query.where(Sale.campaign_id == campaign_id)
            
        if min_amount is not None:
            query = query.where(Sale.amount >= min_amount)
            
        if status:
            query = query.where(Sale.status == status)
            
        if attribution_source:
            query = query.where(Sale.attribution_source == attribution_source)
        
        # Apply pagination and execute
        query = query.offset(offset).limit(limit).order_by(Sale.created_at.desc())
        result = await session.execute(query)
        sales = result.scalars().all()
        
        logger.debug(
            "Sales listed successfully",
            count=len(sales)
        )
        
        return sales
        
    except Exception as e:
        logger.error("Failed to list sales", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list sales"
        )


@router.delete("/{sale_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sale(
    *,
    session: AsyncSession = Depends(get_db),
    sale_id: int
) -> None:
    """
    Delete sale record
    
    Removes sale transaction. Use with caution as this affects
    revenue reporting and attribution analytics.
    """
    logger.info("Deleting sale", sale_id=sale_id)
    
    try:
        # Get sale to verify it exists
        result = await session.execute(
            select(Sale).where(Sale.id == sale_id)
        )
        sale = result.scalar_one_or_none()
        
        if not sale:
            logger.warning("Sale not found for deletion", sale_id=sale_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sale not found"
            )
        
        # Delete sale
        await session.delete(sale)
        await session.commit()
        
        logger.info("Sale deleted successfully", sale_id=sale_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete sale", error=str(e), sale_id=sale_id)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete sale"
        )
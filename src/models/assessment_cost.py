"""
PRP-003: Assessment Cost Tracking Model
Tracks API costs for PageSpeed and other external service calls
"""

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.lead import Lead

from src.core.database import Base


class AssessmentCost(Base):
    """
    Track costs for external API calls during assessments
    Implements cost tracking requirements from PRP-003
    """
    __tablename__ = "assessment_costs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Assessment relationship
    lead_id: Mapped[int] = mapped_column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    assessment_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("assessments.id"), nullable=True, index=True)
    
    # Service and cost details
    service_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # pagespeed, semrush, etc.
    api_endpoint: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    cost_cents: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # Cost in cents for precision
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    
    # Request details
    request_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    response_status: Mapped[str] = mapped_column(String(20), nullable=False)  # success, error, timeout
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # API-specific metadata
    api_quota_used: Mapped[bool] = mapped_column(Boolean, default=False)  # Whether this used free quota
    rate_limited: Mapped[bool] = mapped_column(Boolean, default=False)  # Whether request was rate limited
    retry_count: Mapped[int] = mapped_column(Integer, default=0)  # Number of retries needed
    
    # Error tracking
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Budget tracking
    daily_budget_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD format
    monthly_budget_date: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # YYYY-MM format
    
    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="assessment_costs")
    
    @property
    def cost_dollars(self) -> float:
        """Convert cost from cents to dollars"""
        return self.cost_cents / 100.0
    
    @classmethod
    def create_pagespeed_cost(
        cls,
        lead_id: int,
        cost_cents: float = 0.25,  # $0.0025 default
        response_status: str = "success",
        response_time_ms: Optional[int] = None,
        api_quota_used: bool = False,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> "AssessmentCost":
        """
        Create cost record for PageSpeed API call
        
        Args:
            lead_id: ID of the lead being assessed
            cost_cents: Cost in cents (default $0.0025)
            response_status: success, error, or timeout
            response_time_ms: API response time in milliseconds
            api_quota_used: Whether free quota was used
            error_code: Error code if applicable
            error_message: Error message if applicable
            
        Returns:
            AssessmentCost instance
        """
        now = datetime.now(timezone.utc)
        
        return cls(
            lead_id=lead_id,
            service_name="pagespeed",
            api_endpoint="https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed",
            cost_cents=cost_cents,
            currency="USD",
            request_timestamp=now,
            response_status=response_status,
            response_time_ms=response_time_ms,
            api_quota_used=api_quota_used,
            rate_limited=False,  # Will be updated if rate limited
            retry_count=0,  # Will be updated if retries needed
            error_code=error_code,
            error_message=error_message,
            daily_budget_date=now.strftime("%Y-%m-%d"),
            monthly_budget_date=now.strftime("%Y-%m")
        )
    
    @classmethod
    def get_daily_cost(cls, session, date: str, service_name: Optional[str] = None) -> float:
        """
        Get total cost for a specific date
        
        Args:
            session: Database session
            date: Date in YYYY-MM-DD format
            service_name: Optional service filter
            
        Returns:
            Total cost in cents
        """
        query = session.query(cls).filter(cls.daily_budget_date == date)
        
        if service_name:
            query = query.filter(cls.service_name == service_name)
        
        costs = query.all()
        return sum(cost.cost_cents for cost in costs)
    
    @classmethod
    def get_monthly_cost(cls, session, month: str, service_name: Optional[str] = None) -> float:
        """
        Get total cost for a specific month
        
        Args:
            session: Database session  
            month: Month in YYYY-MM format
            service_name: Optional service filter
            
        Returns:
            Total cost in cents
        """
        query = session.query(cls).filter(cls.monthly_budget_date == month)
        
        if service_name:
            query = query.filter(cls.service_name == service_name)
        
        costs = query.all()
        return sum(cost.cost_cents for cost in costs)
    
    @classmethod
    def get_quota_usage_today(cls, session, service_name: str) -> int:
        """
        Get number of API calls made today for quota tracking
        
        Args:
            session: Database session
            service_name: Service to check (e.g., 'pagespeed')
            
        Returns:
            Number of API calls made today
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        return session.query(cls).filter(
            cls.daily_budget_date == today,
            cls.service_name == service_name,
            cls.response_status == "success"
        ).count()
    
    def __repr__(self):
        return f"<AssessmentCost(service={self.service_name}, cost=${self.cost_dollars:.4f}, status={self.response_status})>"
"""
PRP-001: Lead Data Model Implementation
SQLAlchemy models for business leads, assessments, campaigns, and sales tracking
"""

from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.assessment_cost import AssessmentCost
from datetime import datetime
from sqlalchemy import String, Integer, Float, Text, JSON, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class Lead(Base):
    """
    Business lead model for managing directory data and contact information
    Supports lead acquisition from data providers and quality scoring
    """
    __tablename__ = "leads"
    
    # Primary key and metadata
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Business information (required fields)
    company: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Contact information (optional)
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    url: Mapped[Optional[str]] = mapped_column(String(512))
    
    # Address information
    address: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(2))
    zip_code: Mapped[Optional[str]] = mapped_column(String(10))
    
    # Business classification
    naics_code: Mapped[Optional[str]] = mapped_column(String(10))
    sic_code: Mapped[Optional[str]] = mapped_column(String(10))
    employee_size: Mapped[Optional[int]] = mapped_column(Integer)
    sales_volume: Mapped[Optional[float]] = mapped_column(Float)
    
    # Lead scoring and quality
    quality_score: Mapped[Optional[float]] = mapped_column(Float)
    
    # Relationships
    assessments: Mapped[List["Assessment"]] = relationship(
        "Assessment",
        back_populates="lead",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    sales: Mapped[List["Sale"]] = relationship(
        "Sale",
        back_populates="lead", 
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    assessment_costs: Mapped[List["AssessmentCost"]] = relationship(
        "AssessmentCost",
        back_populates="lead",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<Lead(id={self.id}, company='{self.company}', email='{self.email}')>"


class Assessment(Base):
    """
    Assessment results model for storing pipeline outputs
    Supports PageSpeed, security, SEO, visual analysis, and LLM insights
    """
    __tablename__ = "assessments"
    
    # Primary key and relationships
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("leads.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Technical metric scores (0-100 scale)
    pagespeed_score: Mapped[Optional[int]] = mapped_column(Integer)
    security_score: Mapped[Optional[int]] = mapped_column(Integer)  
    mobile_score: Mapped[Optional[int]] = mapped_column(Integer)
    seo_score: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Assessment results in JSON format for flexibility
    pagespeed_data: Mapped[Optional[dict]] = mapped_column(JSON)
    security_headers: Mapped[Optional[dict]] = mapped_column(JSON)
    gbp_data: Mapped[Optional[dict]] = mapped_column(JSON)  # Google Business Profile
    semrush_data: Mapped[Optional[dict]] = mapped_column(JSON)
    visual_analysis: Mapped[Optional[dict]] = mapped_column(JSON)
    llm_insights: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Assessment status and error tracking
    status: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        default="pending",
        index=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Processing metadata
    assessment_duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    total_score: Mapped[Optional[float]] = mapped_column(Float)  # Calculated composite score
    
    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="assessments")
    result: Mapped["AssessmentResults"] = relationship(
        "AssessmentResults", 
        back_populates="assessment",
        uselist=False  # One-to-one relationship
    )
    security_analysis: Mapped["SecurityAnalysis"] = relationship(
        "SecurityAnalysis",
        back_populates="assessment",
        uselist=False  # One-to-one relationship
    )
    gbp_analysis: Mapped["GBPAnalysis"] = relationship(
        "GBPAnalysis",
        back_populates="assessment",
        uselist=False  # One-to-one relationship
    )
    
    def __repr__(self) -> str:
        return f"<Assessment(id={self.id}, lead_id={self.lead_id}, status='{self.status}')>"


class Campaign(Base):
    """
    Email campaign model for tracking performance and revenue attribution
    Supports conversion rate optimization targeting 0.25-0.6%
    """
    __tablename__ = "campaigns"
    
    # Primary key and metadata
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Campaign information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject_line: Mapped[str] = mapped_column(String(255), nullable=False)
    send_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Email performance metrics
    leads_targeted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    emails_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    emails_delivered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    emails_opened: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    emails_clicked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Revenue tracking for $399 report sales
    leads_converted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revenue_generated: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    # Campaign status
    status: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        default="draft",
        index=True
    )
    
    # Relationships
    sales: Mapped[List["Sale"]] = relationship(
        "Sale",
        back_populates="campaign",
        lazy="selectin"
    )
    
    # Calculated properties for conversion rate tracking
    @property
    def open_rate(self) -> float:
        """Calculate email open rate"""
        if self.emails_delivered == 0:
            return 0.0
        return self.emails_opened / self.emails_delivered
    
    @property
    def click_rate(self) -> float:
        """Calculate email click rate"""
        if self.emails_delivered == 0:
            return 0.0
        return self.emails_clicked / self.emails_delivered
    
    @property
    def conversion_rate(self) -> float:
        """Calculate lead conversion rate"""
        if self.leads_targeted == 0:
            return 0.0
        return self.leads_converted / self.leads_targeted
    
    @property
    def revenue_per_lead(self) -> float:
        """Calculate revenue per targeted lead"""
        if self.leads_targeted == 0:
            return 0.0
        return self.revenue_generated / self.leads_targeted
    
    def __repr__(self) -> str:
        return f"<Campaign(id={self.id}, name='{self.name}', conversion_rate={self.conversion_rate:.3f})>"


class Sale(Base):
    """
    Sales transaction model for revenue attribution and tracking
    Links lead acquisition through campaign to $399 report purchase
    """
    __tablename__ = "sales"
    
    # Primary key and relationships
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    campaign_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Transaction details
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_method: Mapped[Optional[str]] = mapped_column(String(50))
    transaction_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    
    # Attribution tracking
    attribution_source: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Sale status for processing
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="completed",
        index=True
    )
    
    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="sales")
    campaign: Mapped[Optional["Campaign"]] = relationship("Campaign", back_populates="sales")
    
    def __repr__(self) -> str:
        return f"<Sale(id={self.id}, lead_id={self.lead_id}, amount=${self.amount:.2f})>"
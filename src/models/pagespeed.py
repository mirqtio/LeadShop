"""
PageSpeed Insights Data Models
Comprehensive models for storing all PageSpeed API data elements
"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, Text, JSON, ForeignKey, DateTime, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class PageSpeedAnalysis(Base):
    """
    Main PageSpeed analysis results for both mobile and desktop strategies
    Stores core metrics, scores, and metadata from PageSpeed Insights API
    """
    __tablename__ = "pagespeed_analysis"
    
    # Primary key and relationships
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    # Request metadata
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    strategy: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # 'mobile' or 'desktop'
    analysis_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    analysis_duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    cost_cents: Mapped[Optional[float]] = mapped_column(Float)  # API call cost tracking
    
    # URLs after processing
    requested_url: Mapped[Optional[str]] = mapped_column(String(1024))
    final_url: Mapped[Optional[str]] = mapped_column(String(1024))
    main_document_url: Mapped[Optional[str]] = mapped_column(String(1024))
    final_displayed_url: Mapped[Optional[str]] = mapped_column(String(1024))
    
    # Core Web Vitals
    first_contentful_paint_ms: Mapped[Optional[int]] = mapped_column(Integer)
    largest_contentful_paint_ms: Mapped[Optional[int]] = mapped_column(Integer)
    cumulative_layout_shift: Mapped[Optional[float]] = mapped_column(Float)
    total_blocking_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    time_to_interactive_ms: Mapped[Optional[int]] = mapped_column(Integer)
    speed_index_ms: Mapped[Optional[int]] = mapped_column(Integer)
    performance_score: Mapped[Optional[int]] = mapped_column(Integer, index=True)  # 0-100
    
    # Category scores
    accessibility_score: Mapped[Optional[int]] = mapped_column(Integer)  # 0-100
    best_practices_score: Mapped[Optional[int]] = mapped_column(Integer)  # 0-100
    seo_score: Mapped[Optional[int]] = mapped_column(Integer)  # 0-100
    pwa_score: Mapped[Optional[int]] = mapped_column(Integer)  # 0-100 (if applicable)
    
    # Lighthouse metadata
    lighthouse_version: Mapped[Optional[str]] = mapped_column(String(20))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    fetch_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    environment: Mapped[Optional[dict]] = mapped_column(JSON)  # Test environment details
    config_settings: Mapped[Optional[dict]] = mapped_column(JSON)  # Configuration used
    timing_total_ms: Mapped[Optional[int]] = mapped_column(Integer)  # Total Lighthouse runtime
    
    # Benchmark and credits
    benchmark_index: Mapped[Optional[int]] = mapped_column(Integer)
    credits: Mapped[Optional[dict]] = mapped_column(JSON)  # Tool versions used
    
    # Raw data storage for detailed analysis
    raw_lighthouse_result: Mapped[Optional[dict]] = mapped_column(JSON)  # Complete Lighthouse result
    i18n_strings: Mapped[Optional[dict]] = mapped_column(JSON)  # Internationalization strings
    
    # Relationships
    assessment: Mapped["Assessment"] = relationship("Assessment", backref="pagespeed_analyses")
    audits: Mapped[List["PageSpeedAudit"]] = relationship(
        "PageSpeedAudit",
        back_populates="analysis",
        cascade="all, delete-orphan"
    )
    screenshots: Mapped[List["PageSpeedScreenshot"]] = relationship(
        "PageSpeedScreenshot",
        back_populates="analysis",
        cascade="all, delete-orphan"
    )
    elements: Mapped[List["PageSpeedElement"]] = relationship(
        "PageSpeedElement",
        back_populates="analysis",
        cascade="all, delete-orphan"
    )
    entities: Mapped[List["PageSpeedEntity"]] = relationship(
        "PageSpeedEntity",
        back_populates="analysis",
        cascade="all, delete-orphan"
    )
    opportunities: Mapped[List["PageSpeedOpportunity"]] = relationship(
        "PageSpeedOpportunity",
        back_populates="analysis",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<PageSpeedAnalysis(id={self.id}, assessment_id={self.assessment_id}, strategy='{self.strategy}', score={self.performance_score})>"


class PageSpeedAudit(Base):
    """
    Individual audit results from PageSpeed Insights
    Stores detailed metrics for each audit (e.g., first-contentful-paint, uses-responsive-images)
    """
    __tablename__ = "pagespeed_audits"
    __table_args__ = (
        UniqueConstraint('pagespeed_analysis_id', 'audit_id', name='uq_pagespeed_audit'),
    )
    
    # Primary key and relationships
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pagespeed_analysis_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pagespeed_analysis.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Audit identification
    audit_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # e.g., 'first-contentful-paint'
    title: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Scoring
    score: Mapped[Optional[float]] = mapped_column(Float, index=True)  # 0-1 or null
    score_display_mode: Mapped[Optional[str]] = mapped_column(String(50))  # 'numeric', 'binary', etc.
    display_value: Mapped[Optional[str]] = mapped_column(Text)
    
    # Details
    explanation: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    warnings: Mapped[Optional[dict]] = mapped_column(JSON)
    details: Mapped[Optional[dict]] = mapped_column(JSON)  # Detailed audit results
    
    # Numeric values
    numeric_value: Mapped[Optional[float]] = mapped_column(Float)
    numeric_unit: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Relationships
    analysis: Mapped["PageSpeedAnalysis"] = relationship("PageSpeedAnalysis", back_populates="audits")
    
    def __repr__(self) -> str:
        return f"<PageSpeedAudit(id={self.id}, audit_id='{self.audit_id}', score={self.score})>"


class PageSpeedScreenshot(Base):
    """
    Screenshots captured during PageSpeed analysis
    Stores full page screenshots and filmstrip frames
    """
    __tablename__ = "pagespeed_screenshots"
    
    # Primary key and relationships
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pagespeed_analysis_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pagespeed_analysis.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Screenshot metadata
    screenshot_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # 'full_page', 'filmstrip', etc.
    data: Mapped[Optional[str]] = mapped_column(Text)  # Base64 encoded image
    data_url: Mapped[Optional[str]] = mapped_column(String(1024))  # S3 URL if stored externally
    height: Mapped[Optional[int]] = mapped_column(Integer)
    width: Mapped[Optional[int]] = mapped_column(Integer)
    mime_type: Mapped[Optional[str]] = mapped_column(String(50))  # 'image/webp', 'image/jpeg'
    timestamp_ms: Mapped[Optional[int]] = mapped_column(Integer)  # For filmstrip timing
    
    # Relationships
    analysis: Mapped["PageSpeedAnalysis"] = relationship("PageSpeedAnalysis", back_populates="screenshots")
    
    def __repr__(self) -> str:
        return f"<PageSpeedScreenshot(id={self.id}, type='{self.screenshot_type}', {self.width}x{self.height})>"


class PageSpeedElement(Base):
    """
    Element positioning data from PageSpeed analysis
    Maps DOM elements to their positions in screenshots
    """
    __tablename__ = "pagespeed_elements"
    
    # Primary key and relationships
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pagespeed_analysis_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pagespeed_analysis.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Element identification
    node_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # Internal node identifier
    selector: Mapped[Optional[str]] = mapped_column(Text)  # CSS selector
    snippet: Mapped[Optional[str]] = mapped_column(Text)  # HTML snippet
    bounding_rect: Mapped[Optional[dict]] = mapped_column(JSON)  # {top, bottom, left, right, width, height}
    node_label: Mapped[Optional[str]] = mapped_column(Text)  # Human-readable label
    element_type: Mapped[Optional[str]] = mapped_column(String(100))  # Tag name or element type
    
    # Relationships
    analysis: Mapped["PageSpeedAnalysis"] = relationship("PageSpeedAnalysis", back_populates="elements")
    
    def __repr__(self) -> str:
        return f"<PageSpeedElement(id={self.id}, node_id='{self.node_id}', type='{self.element_type}')>"


class PageSpeedEntity(Base):
    """
    Third-party entities detected during PageSpeed analysis
    Tracks external resources and their performance impact
    """
    __tablename__ = "pagespeed_entities"
    
    # Primary key and relationships
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pagespeed_analysis_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pagespeed_analysis.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Entity information
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # Entity name
    homepage: Mapped[Optional[str]] = mapped_column(String(1024))
    category: Mapped[Optional[str]] = mapped_column(String(100), index=True)  # 'analytics', 'social', 'advertising', etc.
    is_first_party: Mapped[bool] = mapped_column(Boolean, default=False)
    is_unrecognized: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Performance metrics
    total_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    total_tasks: Mapped[Optional[int]] = mapped_column(Integer)
    total_task_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    main_thread_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    blocking_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    transfer_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Relationships
    analysis: Mapped["PageSpeedAnalysis"] = relationship("PageSpeedAnalysis", back_populates="entities")
    
    def __repr__(self) -> str:
        return f"<PageSpeedEntity(id={self.id}, name='{self.name}', category='{self.category}')>"


class PageSpeedOpportunity(Base):
    """
    Performance improvement opportunities identified by PageSpeed
    Provides actionable recommendations with potential savings
    """
    __tablename__ = "pagespeed_opportunities"
    
    # Primary key and relationships
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pagespeed_analysis_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pagespeed_analysis.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Opportunity details
    audit_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Potential savings
    savings_ms: Mapped[Optional[int]] = mapped_column(Integer, index=True)  # Potential time savings
    savings_bytes: Mapped[Optional[int]] = mapped_column(Integer)  # Potential byte savings
    
    # Rating and details
    rating: Mapped[Optional[str]] = mapped_column(String(20))  # 'pass', 'average', 'fail'
    details: Mapped[Optional[dict]] = mapped_column(JSON)  # Specific recommendations
    
    # Relationships
    analysis: Mapped["PageSpeedAnalysis"] = relationship("PageSpeedAnalysis", back_populates="opportunities")
    
    def __repr__(self) -> str:
        return f"<PageSpeedOpportunity(id={self.id}, audit_id='{self.audit_id}', savings_ms={self.savings_ms})>"
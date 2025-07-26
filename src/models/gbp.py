"""
Google Business Profile database models
Stores comprehensive GBP data from Google Places API
"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, Text, JSON, ForeignKey, DateTime, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class GBPAnalysis(Base):
    """
    Main Google Business Profile analysis data
    One-to-one relationship with Assessment
    """
    __tablename__ = "gbp_analysis"
    
    # Primary key and relationships
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("assessments.id", ondelete="CASCADE"), 
        nullable=False,
        unique=True,  # One-to-one relationship
        index=True
    )
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
    
    # Google Place identification
    place_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, comment='Google Places unique identifier')
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    formatted_address: Mapped[Optional[str]] = mapped_column(Text)
    phone_number: Mapped[Optional[str]] = mapped_column(String(50))
    website: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Location data
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    
    # Business status
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_open_now: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_permanently_closed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_temporarily_closed: Mapped[bool] = mapped_column(Boolean, default=False)
    business_status: Mapped[Optional[str]] = mapped_column(String(50), comment='operational, closed_permanently, closed_temporarily')
    
    # Review metrics
    total_reviews: Mapped[int] = mapped_column(Integer, default=0, index=True)
    average_rating: Mapped[Optional[float]] = mapped_column(Float, index=True, comment='1.0-5.0 scale')
    recent_90d_reviews: Mapped[int] = mapped_column(Integer, default=0)
    rating_trend: Mapped[Optional[str]] = mapped_column(String(20), comment='improving, declining, stable')
    
    # Photo metrics
    total_photos: Mapped[int] = mapped_column(Integer, default=0)
    owner_photos: Mapped[int] = mapped_column(Integer, default=0)
    customer_photos: Mapped[int] = mapped_column(Integer, default=0)
    last_photo_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Business categories
    primary_category: Mapped[Optional[str]] = mapped_column(String(255))
    categories: Mapped[Optional[dict]] = mapped_column(JSON, comment='Array of all business categories')
    
    # Operating hours
    is_24_hours: Mapped[bool] = mapped_column(Boolean, default=False)
    timezone: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Matching and search metadata
    match_confidence: Mapped[float] = mapped_column(Float, default=0.0, comment='0.0-1.0 confidence score')
    search_query: Mapped[str] = mapped_column(Text, nullable=False, comment='Original search query used')
    search_results_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Analysis metadata
    data_freshness: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    extraction_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    analysis_duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Raw API response storage
    raw_api_response: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Relationships
    assessment: Mapped["Assessment"] = relationship(
        "Assessment", 
        back_populates="gbp_analysis",
        uselist=False  # One-to-one
    )
    business_hours: Mapped[List["GBPBusinessHours"]] = relationship(
        "GBPBusinessHours",
        back_populates="gbp_analysis",
        cascade="all, delete-orphan"
    )
    reviews: Mapped[List["GBPReviews"]] = relationship(
        "GBPReviews",
        back_populates="gbp_analysis",
        cascade="all, delete-orphan"
    )
    photos: Mapped[List["GBPPhotos"]] = relationship(
        "GBPPhotos",
        back_populates="gbp_analysis",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<GBPAnalysis(id={self.id}, business={self.business_name}, rating={self.average_rating})>"


class GBPBusinessHours(Base):
    """
    Business operating hours by day of week
    """
    __tablename__ = "gbp_business_hours"
    __table_args__ = (
        UniqueConstraint('gbp_analysis_id', 'day_of_week', name='uq_gbp_hours_day'),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gbp_analysis_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("gbp_analysis.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    day_of_week: Mapped[str] = mapped_column(String(20), nullable=False, index=True, comment='monday, tuesday, etc.')
    open_time: Mapped[Optional[str]] = mapped_column(String(10), comment='HH:MM format')
    close_time: Mapped[Optional[str]] = mapped_column(String(10), comment='HH:MM format')
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)
    hours_text: Mapped[Optional[str]] = mapped_column(String(100), comment='Full hours text e.g. "09:00 - 17:00"')
    
    # Relationship
    gbp_analysis: Mapped["GBPAnalysis"] = relationship(
        "GBPAnalysis",
        back_populates="business_hours"
    )
    
    def __repr__(self) -> str:
        return f"<GBPBusinessHours(day={self.day_of_week}, hours={self.hours_text})>"


class GBPReviews(Base):
    """
    Review rating distribution snapshot
    """
    __tablename__ = "gbp_reviews"
    __table_args__ = (
        UniqueConstraint('gbp_analysis_id', 'rating', name='uq_gbp_reviews_rating'),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gbp_analysis_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("gbp_analysis.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    rating: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment='1-5 stars')
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    percentage: Mapped[Optional[float]] = mapped_column(Float, comment='Percentage of total reviews')
    
    # Relationship
    gbp_analysis: Mapped["GBPAnalysis"] = relationship(
        "GBPAnalysis",
        back_populates="reviews"
    )
    
    def __repr__(self) -> str:
        return f"<GBPReviews(rating={self.rating}, count={self.review_count})>"


class GBPPhotos(Base):
    """
    Photo category distribution
    """
    __tablename__ = "gbp_photos"
    __table_args__ = (
        UniqueConstraint('gbp_analysis_id', 'category', name='uq_gbp_photos_category'),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gbp_analysis_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("gbp_analysis.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment='exterior, interior, product, etc.')
    photo_count: Mapped[int] = mapped_column(Integer, default=0)
    percentage: Mapped[Optional[float]] = mapped_column(Float, comment='Percentage of total photos')
    
    # Relationship
    gbp_analysis: Mapped["GBPAnalysis"] = relationship(
        "GBPAnalysis",
        back_populates="photos"
    )
    
    def __repr__(self) -> str:
        return f"<GBPPhotos(category={self.category}, count={self.photo_count})>"
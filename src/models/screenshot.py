"""
Screenshot Data Models
Models for storing website screenshots and metadata for visual analysis
"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, Text, JSON, ForeignKey, DateTime, func, UniqueConstraint, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from src.core.database import Base


class ScreenshotType(enum.Enum):
    """Types of screenshots captured"""
    FULL_PAGE = "full_page"
    ABOVE_FOLD = "above_fold"
    MOBILE = "mobile"
    DESKTOP = "desktop"
    TABLET = "tablet"
    THUMBNAIL = "thumbnail"


class ScreenshotStatus(enum.Enum):
    """Status of screenshot capture and processing"""
    PENDING = "pending"
    CAPTURING = "capturing"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Screenshot(Base):
    """
    Main screenshot storage model for website visual captures
    Supports multiple viewport sizes and full page captures
    """
    __tablename__ = "screenshots"
    
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
    
    # Screenshot metadata
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    screenshot_type: Mapped[str] = mapped_column(
        Enum(ScreenshotType, native_enum=False),
        nullable=False,
        index=True
    )
    viewport_width: Mapped[int] = mapped_column(Integer, nullable=False)
    viewport_height: Mapped[int] = mapped_column(Integer, nullable=False)
    device_scale_factor: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_mobile: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Image data
    image_data: Mapped[Optional[str]] = mapped_column(Text)  # Base64 encoded for small images
    image_url: Mapped[Optional[str]] = mapped_column(String(1024))  # S3 URL for larger images
    image_format: Mapped[str] = mapped_column(String(10), default="webp", nullable=False)  # webp, png, jpeg
    image_width: Mapped[Optional[int]] = mapped_column(Integer)
    image_height: Mapped[Optional[int]] = mapped_column(Integer)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Capture metadata
    capture_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    capture_duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    
    # Processing status
    status: Mapped[str] = mapped_column(
        Enum(ScreenshotStatus, native_enum=False),
        nullable=False,
        default=ScreenshotStatus.PENDING,
        index=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    processing_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Quality metrics
    quality_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100 based on clarity, completeness
    is_complete: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # False if page didn't fully load
    has_errors: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Console errors during capture
    
    # Performance data
    page_load_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    dom_content_loaded_ms: Mapped[Optional[int]] = mapped_column(Integer)
    first_paint_ms: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Additional metadata
    capture_metadata: Mapped[Optional[dict]] = mapped_column(JSON)  # Additional capture details
    browser_info: Mapped[Optional[dict]] = mapped_column(JSON)  # Browser version, engine, etc.
    
    # Relationships
    assessment: Mapped["Assessment"] = relationship("Assessment", backref="screenshots")
    visual_analyses: Mapped[List["VisualAnalysis"]] = relationship(
        "VisualAnalysis",
        back_populates="screenshot",
        cascade="all, delete-orphan"
    )
    screenshot_regions: Mapped[List["ScreenshotRegion"]] = relationship(
        "ScreenshotRegion",
        back_populates="screenshot",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Screenshot(id={self.id}, type='{self.screenshot_type}', {self.image_width}x{self.image_height})>"


class ScreenshotRegion(Base):
    """
    Regions of interest within screenshots
    Used to mark specific areas for analysis or annotation
    """
    __tablename__ = "screenshot_regions"
    
    # Primary key and relationships
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    screenshot_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("screenshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Region identification
    region_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # 'header', 'hero', 'cta', 'form', etc.
    region_name: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Bounding box coordinates
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Analysis data
    dom_selector: Mapped[Optional[str]] = mapped_column(Text)  # CSS selector if applicable
    html_snippet: Mapped[Optional[str]] = mapped_column(Text)  # HTML content of region
    text_content: Mapped[Optional[str]] = mapped_column(Text)  # Extracted text
    
    # Visual properties
    background_color: Mapped[Optional[str]] = mapped_column(String(20))  # Dominant background color
    text_color: Mapped[Optional[str]] = mapped_column(String(20))  # Dominant text color
    contrast_ratio: Mapped[Optional[float]] = mapped_column(Float)  # WCAG contrast ratio
    
    # Quality metrics for region
    visibility_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100 how prominent
    readability_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100 text readability
    
    # Additional attributes
    attributes: Mapped[Optional[dict]] = mapped_column(JSON)  # Additional region-specific data
    
    # Relationships
    screenshot: Mapped["Screenshot"] = relationship("Screenshot", back_populates="screenshot_regions")
    
    def __repr__(self) -> str:
        return f"<ScreenshotRegion(id={self.id}, type='{self.region_type}', {self.width}x{self.height})>"


class ScreenshotComparison(Base):
    """
    Comparison between screenshots for A/B testing or historical analysis
    Tracks visual differences and improvements
    """
    __tablename__ = "screenshot_comparisons"
    __table_args__ = (
        UniqueConstraint('screenshot_a_id', 'screenshot_b_id', name='uq_screenshot_comparison'),
    )
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Screenshots being compared
    screenshot_a_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("screenshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    screenshot_b_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("screenshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Comparison metadata
    comparison_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'historical', 'variant', 'competitor'
    
    # Difference metrics
    visual_similarity_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100 similarity
    layout_changes: Mapped[Optional[int]] = mapped_column(Integer)  # Number of layout differences
    color_changes: Mapped[Optional[int]] = mapped_column(Integer)  # Number of color differences
    text_changes: Mapped[Optional[int]] = mapped_column(Integer)  # Number of text differences
    
    # Diff visualization
    diff_image_url: Mapped[Optional[str]] = mapped_column(String(1024))  # URL to diff image
    diff_regions: Mapped[Optional[dict]] = mapped_column(JSON)  # Regions that changed
    
    # Analysis results
    improvements: Mapped[Optional[dict]] = mapped_column(JSON)  # Detected improvements
    regressions: Mapped[Optional[dict]] = mapped_column(JSON)  # Detected regressions
    summary: Mapped[Optional[str]] = mapped_column(Text)  # Human-readable summary
    
    # Relationships
    screenshot_a: Mapped["Screenshot"] = relationship(
        "Screenshot",
        foreign_keys=[screenshot_a_id],
        backref="comparisons_as_a"
    )
    screenshot_b: Mapped["Screenshot"] = relationship(
        "Screenshot",
        foreign_keys=[screenshot_b_id],
        backref="comparisons_as_b"
    )
    
    def __repr__(self) -> str:
        return f"<ScreenshotComparison(id={self.id}, similarity={self.visual_similarity_score}%)>"
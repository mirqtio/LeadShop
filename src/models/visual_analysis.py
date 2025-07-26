"""
Visual Analysis Data Models
Models for storing AI-powered visual analysis results and design insights
"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, Text, JSON, ForeignKey, DateTime, func, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from src.core.database import Base


class AnalysisStatus(enum.Enum):
    """Status of visual analysis processing"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class VisualAnalysis(Base):
    """
    Main visual analysis results from AI/ML processing of screenshots
    Stores design quality, UX issues, and improvement recommendations
    """
    __tablename__ = "visual_analyses"
    
    # Primary key and relationships
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    screenshot_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("screenshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    # Analysis metadata
    analysis_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    analysis_duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    analyzer_version: Mapped[Optional[str]] = mapped_column(String(50))  # AI model version
    
    # Overall scores
    design_score: Mapped[Optional[int]] = mapped_column(Integer, index=True)  # 0-100
    usability_score: Mapped[Optional[int]] = mapped_column(Integer, index=True)  # 0-100
    accessibility_score: Mapped[Optional[int]] = mapped_column(Integer, index=True)  # 0-100
    professionalism_score: Mapped[Optional[int]] = mapped_column(Integer, index=True)  # 0-100
    trust_score: Mapped[Optional[int]] = mapped_column(Integer, index=True)  # 0-100
    
    # Visual hierarchy analysis
    visual_hierarchy_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100
    layout_balance_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100
    whitespace_usage_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100
    
    # Color analysis
    color_scheme_quality: Mapped[Optional[float]] = mapped_column(Float)  # 0-100
    color_contrast_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100
    brand_consistency_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100
    dominant_colors: Mapped[Optional[dict]] = mapped_column(JSON)  # List of hex colors with percentages
    
    # Typography analysis
    typography_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100
    font_consistency_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100
    readability_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100
    detected_fonts: Mapped[Optional[dict]] = mapped_column(JSON)  # Font families and usage
    
    # Content analysis
    content_clarity_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100
    cta_effectiveness_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100
    information_density_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100
    
    # Mobile responsiveness
    mobile_friendliness_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100
    responsive_design_issues: Mapped[Optional[dict]] = mapped_column(JSON)  # List of issues
    
    # Key findings
    strengths: Mapped[Optional[dict]] = mapped_column(JSON)  # List of positive findings
    weaknesses: Mapped[Optional[dict]] = mapped_column(JSON)  # List of issues found
    opportunities: Mapped[Optional[dict]] = mapped_column(JSON)  # Improvement opportunities
    
    # AI insights
    ai_summary: Mapped[Optional[str]] = mapped_column(Text)  # Executive summary
    ai_recommendations: Mapped[Optional[dict]] = mapped_column(JSON)  # Prioritized recommendations
    competitor_comparison: Mapped[Optional[dict]] = mapped_column(JSON)  # Industry comparison
    
    # Processing status
    status: Mapped[str] = mapped_column(
        Enum(AnalysisStatus, native_enum=False),
        nullable=False,
        default=AnalysisStatus.PENDING,
        index=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Cost tracking
    analysis_cost_cents: Mapped[Optional[float]] = mapped_column(Float)  # API/processing costs
    
    # Raw analysis data
    raw_analysis_data: Mapped[Optional[dict]] = mapped_column(JSON)  # Complete AI analysis output
    
    # Relationships
    assessment: Mapped["Assessment"] = relationship("Assessment", backref="visual_analyses")
    screenshot: Mapped["Screenshot"] = relationship("Screenshot", back_populates="visual_analyses")
    design_elements: Mapped[List["DesignElement"]] = relationship(
        "DesignElement",
        back_populates="visual_analysis",
        cascade="all, delete-orphan"
    )
    ux_issues: Mapped[List["UXIssue"]] = relationship(
        "UXIssue",
        back_populates="visual_analysis",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<VisualAnalysis(id={self.id}, design_score={self.design_score}, status='{self.status}')>"


class DesignElement(Base):
    """
    Individual design elements detected in visual analysis
    Tracks specific UI components and their quality
    """
    __tablename__ = "design_elements"
    
    # Primary key and relationships
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visual_analysis_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("visual_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Element identification
    element_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # 'header', 'navigation', 'hero', 'cta', etc.
    element_name: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Location in screenshot
    x: Mapped[Optional[int]] = mapped_column(Integer)
    y: Mapped[Optional[int]] = mapped_column(Integer)
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Quality assessment
    quality_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100
    visibility_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100
    effectiveness_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100
    
    # Design properties
    alignment: Mapped[Optional[str]] = mapped_column(String(50))  # 'left', 'center', 'right'
    spacing_quality: Mapped[Optional[str]] = mapped_column(String(50))  # 'good', 'cramped', 'excessive'
    visual_weight: Mapped[Optional[str]] = mapped_column(String(50))  # 'light', 'medium', 'heavy'
    
    # Issues and recommendations
    issues: Mapped[Optional[dict]] = mapped_column(JSON)  # List of issues with this element
    recommendations: Mapped[Optional[dict]] = mapped_column(JSON)  # Improvement suggestions
    
    # Additional attributes
    attributes: Mapped[Optional[dict]] = mapped_column(JSON)  # Element-specific data
    
    # Relationships
    visual_analysis: Mapped["VisualAnalysis"] = relationship("VisualAnalysis", back_populates="design_elements")
    
    def __repr__(self) -> str:
        return f"<DesignElement(id={self.id}, type='{self.element_type}', quality={self.quality_score})>"


class UXIssue(Base):
    """
    Specific UX/UI issues identified during visual analysis
    Provides actionable feedback for improvements
    """
    __tablename__ = "ux_issues"
    
    # Primary key and relationships
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visual_analysis_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("visual_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Issue identification
    issue_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # Category of issue
    issue_code: Mapped[Optional[str]] = mapped_column(String(50), index=True)  # Standardized code
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Severity and impact
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # 'critical', 'high', 'medium', 'low'
    impact_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100 impact on user experience
    affects_mobile: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    affects_desktop: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Location if applicable
    element_selector: Mapped[Optional[str]] = mapped_column(Text)  # CSS selector
    screenshot_region: Mapped[Optional[dict]] = mapped_column(JSON)  # Bounding box
    
    # WCAG compliance if applicable
    wcag_criterion: Mapped[Optional[str]] = mapped_column(String(20))  # e.g., '1.4.3'
    wcag_level: Mapped[Optional[str]] = mapped_column(String(5))  # 'A', 'AA', 'AAA'
    
    # Recommendations
    recommendation: Mapped[Optional[str]] = mapped_column(Text)
    fix_difficulty: Mapped[Optional[str]] = mapped_column(String(20))  # 'easy', 'medium', 'hard'
    estimated_fix_time_hours: Mapped[Optional[float]] = mapped_column(Float)
    
    # Supporting evidence
    evidence: Mapped[Optional[dict]] = mapped_column(JSON)  # Screenshots, measurements, etc.
    
    # Relationships
    visual_analysis: Mapped["VisualAnalysis"] = relationship("VisualAnalysis", back_populates="ux_issues")
    
    def __repr__(self) -> str:
        return f"<UXIssue(id={self.id}, type='{self.issue_type}', severity='{self.severity}')>"


class VisualBenchmark(Base):
    """
    Industry benchmarks for visual design quality
    Used to compare sites against industry standards
    """
    __tablename__ = "visual_benchmarks"
    
    # Primary key
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
    
    # Benchmark identification
    industry: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    business_type: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    benchmark_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Benchmark scores (industry averages)
    avg_design_score: Mapped[Optional[float]] = mapped_column(Float)
    avg_usability_score: Mapped[Optional[float]] = mapped_column(Float)
    avg_accessibility_score: Mapped[Optional[float]] = mapped_column(Float)
    avg_professionalism_score: Mapped[Optional[float]] = mapped_column(Float)
    avg_trust_score: Mapped[Optional[float]] = mapped_column(Float)
    
    # Percentiles for scoring
    percentile_10: Mapped[Optional[float]] = mapped_column(Float)  # Bottom 10%
    percentile_25: Mapped[Optional[float]] = mapped_column(Float)  # Bottom quartile
    percentile_50: Mapped[Optional[float]] = mapped_column(Float)  # Median
    percentile_75: Mapped[Optional[float]] = mapped_column(Float)  # Top quartile
    percentile_90: Mapped[Optional[float]] = mapped_column(Float)  # Top 10%
    
    # Sample size and validity
    sample_size: Mapped[Optional[int]] = mapped_column(Integer)
    last_updated: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Common patterns and issues
    common_strengths: Mapped[Optional[dict]] = mapped_column(JSON)
    common_weaknesses: Mapped[Optional[dict]] = mapped_column(JSON)
    best_practices: Mapped[Optional[dict]] = mapped_column(JSON)
    
    def __repr__(self) -> str:
        return f"<VisualBenchmark(id={self.id}, industry='{self.industry}', avg_score={self.avg_design_score})>"
"""
PRP-014: Decomposed Assessment Results Model
Stores individual metrics from all assessment components
"""

from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class AssessmentResults(Base):
    """
    Comprehensive assessment results with decomposed scores
    Each metric is stored individually for detailed analysis
    """
    __tablename__ = "assessment_results"
    
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
    
    # PageSpeed metrics (times in milliseconds)
    pagespeed_fcp_ms: Mapped[Optional[int]] = mapped_column(Integer)  # First Contentful Paint
    pagespeed_lcp_ms: Mapped[Optional[int]] = mapped_column(Integer)  # Largest Contentful Paint
    pagespeed_cls: Mapped[Optional[float]] = mapped_column(Float)     # Cumulative Layout Shift
    pagespeed_tbt_ms: Mapped[Optional[int]] = mapped_column(Integer)  # Total Blocking Time
    pagespeed_tti_ms: Mapped[Optional[int]] = mapped_column(Integer)  # Time to Interactive
    pagespeed_score: Mapped[Optional[int]] = mapped_column(Integer)   # Overall PageSpeed score (0-100)
    pagespeed_mobile_score: Mapped[Optional[int]] = mapped_column(Integer)  # Mobile score (0-100)
    
    # Tech scraper booleans/values
    tech_https_enforced: Mapped[Optional[bool]] = mapped_column(Boolean)
    tech_tls_version: Mapped[Optional[str]] = mapped_column(String(10))  # e.g., "1.3", "1.2"
    tech_hsts_present: Mapped[Optional[bool]] = mapped_column(Boolean)
    tech_csp_present: Mapped[Optional[bool]] = mapped_column(Boolean)
    tech_robots_found: Mapped[Optional[bool]] = mapped_column(Boolean)
    tech_js_errors_count: Mapped[Optional[int]] = mapped_column(Integer)
    tech_broken_links_count: Mapped[Optional[int]] = mapped_column(Integer)
    tech_redirect_chains: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Security analysis metrics
    security_ssl_valid: Mapped[Optional[bool]] = mapped_column(Boolean)
    security_headers_score: Mapped[Optional[int]] = mapped_column(Integer)  # 0-100
    security_vulnerabilities_count: Mapped[Optional[int]] = mapped_column(Integer)
    security_critical_issues: Mapped[Optional[int]] = mapped_column(Integer)
    
    # GBP (Google Business Profile) data
    gbp_found: Mapped[Optional[bool]] = mapped_column(Boolean)
    gbp_rating: Mapped[Optional[float]] = mapped_column(Float)  # 1.0-5.0
    gbp_review_count: Mapped[Optional[int]] = mapped_column(Integer)
    gbp_photos_count: Mapped[Optional[int]] = mapped_column(Integer)
    gbp_recent_reviews_90d: Mapped[Optional[int]] = mapped_column(Integer)
    gbp_rating_trend: Mapped[Optional[str]] = mapped_column(String(20))  # "improving", "declining", "stable"
    gbp_is_closed: Mapped[Optional[bool]] = mapped_column(Boolean)
    gbp_verified: Mapped[Optional[bool]] = mapped_column(Boolean)
    
    # SEMrush scores
    semrush_health_score: Mapped[Optional[int]] = mapped_column(Integer)  # 0-100
    semrush_toxicity_score: Mapped[Optional[int]] = mapped_column(Integer)  # 0-100
    semrush_traffic_estimate: Mapped[Optional[int]] = mapped_column(Integer)
    semrush_keywords_count: Mapped[Optional[int]] = mapped_column(Integer)
    semrush_backlinks_count: Mapped[Optional[int]] = mapped_column(Integer)
    semrush_domain_authority: Mapped[Optional[int]] = mapped_column(Integer)  # 0-100
    
    # Visual rubrics (1-9 scale for each aspect)
    visual_score_1: Mapped[Optional[int]] = mapped_column(Integer)  # First Impression
    visual_score_2: Mapped[Optional[int]] = mapped_column(Integer)  # Visual Hierarchy
    visual_score_3: Mapped[Optional[int]] = mapped_column(Integer)  # Color & Contrast
    visual_score_4: Mapped[Optional[int]] = mapped_column(Integer)  # Typography
    visual_score_5: Mapped[Optional[int]] = mapped_column(Integer)  # Layout & Spacing
    visual_score_6: Mapped[Optional[int]] = mapped_column(Integer)  # Mobile Responsiveness
    visual_score_7: Mapped[Optional[int]] = mapped_column(Integer)  # CTAs & Conversion
    visual_score_8: Mapped[Optional[int]] = mapped_column(Integer)  # Brand Consistency
    visual_score_9: Mapped[Optional[int]] = mapped_column(Integer)  # Trust Signals
    
    # Calculated business impact metrics
    impact_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100 overall business impact
    revenue_impact_monthly: Mapped[Optional[float]] = mapped_column(Float)  # Estimated monthly revenue impact
    conversion_impact_percent: Mapped[Optional[float]] = mapped_column(Float)  # Estimated conversion rate impact
    
    # Error tracking for partial failures
    error_components: Mapped[Optional[str]] = mapped_column(Text)  # JSON list of failed components
    
    # Relationship back to assessment
    assessment: Mapped["Assessment"] = relationship(
        "Assessment", 
        backref="detailed_results",
        uselist=False  # One-to-one
    )
    
    def __repr__(self) -> str:
        return f"<AssessmentResults(id={self.id}, assessment_id={self.assessment_id})>"
    
    def get_visual_scores_dict(self) -> dict:
        """Return all visual scores as a dictionary"""
        return {
            "first_impression": self.visual_score_1,
            "visual_hierarchy": self.visual_score_2,
            "color_contrast": self.visual_score_3,
            "typography": self.visual_score_4,
            "layout_spacing": self.visual_score_5,
            "mobile_responsive": self.visual_score_6,
            "ctas_conversion": self.visual_score_7,
            "brand_consistency": self.visual_score_8,
            "trust_signals": self.visual_score_9
        }
    
    def get_pagespeed_metrics_dict(self) -> dict:
        """Return all PageSpeed metrics as a dictionary"""
        return {
            "fcp_ms": self.pagespeed_fcp_ms,
            "lcp_ms": self.pagespeed_lcp_ms,
            "cls": self.pagespeed_cls,
            "tbt_ms": self.pagespeed_tbt_ms,
            "tti_ms": self.pagespeed_tti_ms,
            "desktop_score": self.pagespeed_score,
            "mobile_score": self.pagespeed_mobile_score
        }
    
    def get_security_metrics_dict(self) -> dict:
        """Return all security metrics as a dictionary"""
        return {
            "ssl_valid": self.security_ssl_valid,
            "headers_score": self.security_headers_score,
            "vulnerabilities_count": self.security_vulnerabilities_count,
            "critical_issues": self.security_critical_issues,
            "https_enforced": self.tech_https_enforced,
            "tls_version": self.tech_tls_version,
            "hsts_present": self.tech_hsts_present,
            "csp_present": self.tech_csp_present
        }
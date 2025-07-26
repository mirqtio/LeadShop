"""
PRP-014: Decomposed Assessment Results Model
Stores all 53 individual metrics from ASSESSMENT_PROGRESS_TRACKER.md
"""

from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, Text, JSON, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class AssessmentResults(Base):
    """
    Decomposed assessment results with all 53 metrics stored individually
    Each metric corresponds to a specific item from ASSESSMENT_PROGRESS_TRACKER.md
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
    
    # PAGESPEED METRICS (PRP-003) - 7 metrics
    pagespeed_fcp_ms: Mapped[Optional[int]] = mapped_column(Integer)  # First Contentful Paint
    pagespeed_lcp_ms: Mapped[Optional[int]] = mapped_column(Integer)  # Largest Contentful Paint
    pagespeed_cls: Mapped[Optional[float]] = mapped_column(Float)     # Cumulative Layout Shift
    pagespeed_tbt_ms: Mapped[Optional[int]] = mapped_column(Integer)  # Total Blocking Time
    pagespeed_tti_ms: Mapped[Optional[int]] = mapped_column(Integer)  # Time to Interactive
    pagespeed_speed_index: Mapped[Optional[int]] = mapped_column(Integer)  # Speed Index
    pagespeed_performance_score: Mapped[Optional[int]] = mapped_column(Integer)  # Performance Score (runtime)
    
    # TECHNICAL/SECURITY METRICS (PRP-004) - 9 metrics
    security_https_enforced: Mapped[Optional[bool]] = mapped_column(Boolean)  # HTTPS enforced?
    security_tls_version: Mapped[Optional[str]] = mapped_column(String(10))   # TLS Version
    security_hsts_header_present: Mapped[Optional[bool]] = mapped_column(Boolean)  # HSTS Header present
    security_csp_header_present: Mapped[Optional[bool]] = mapped_column(Boolean)   # Content-Security-Policy header
    security_xframe_options_header: Mapped[Optional[bool]] = mapped_column(Boolean)  # X-Frame-Options header
    tech_robots_txt_found: Mapped[Optional[bool]] = mapped_column(Boolean)     # robots.txt found
    tech_sitemap_xml_found: Mapped[Optional[bool]] = mapped_column(Boolean)    # sitemap.xml found
    tech_broken_internal_links_count: Mapped[Optional[int]] = mapped_column(Integer)  # Broken internal links (#)
    tech_js_console_errors_count: Mapped[Optional[int]] = mapped_column(Integer)     # JS console errors (#)
    
    # GOOGLE BUSINESS PROFILE METRICS (PRP-005) - 9 metrics
    gbp_hours: Mapped[Optional[dict]] = mapped_column(JSON)            # hours - Opening-hours JSON
    gbp_review_count: Mapped[Optional[int]] = mapped_column(Integer)   # review_count - Total public reviews
    gbp_rating: Mapped[Optional[float]] = mapped_column(Float)         # rating - Average star rating (1–5)
    gbp_photos_count: Mapped[Optional[int]] = mapped_column(Integer)   # photos_count - Number of photos uploaded
    gbp_total_reviews: Mapped[Optional[int]] = mapped_column(Integer)  # total_reviews - Snapshot review count
    gbp_avg_rating: Mapped[Optional[float]] = mapped_column(Float)     # avg_rating - Mean rating across lifetime
    gbp_recent_90d: Mapped[Optional[int]] = mapped_column(Integer)     # recent_90d - Reviews added in past 90 days
    gbp_rating_trend: Mapped[Optional[str]] = mapped_column(String(20))  # rating_trend - Stable/improving/declining
    gbp_is_closed: Mapped[Optional[bool]] = mapped_column(Boolean)     # is_closed - Permanently-closed business flag
    
    # SCREENSHOT/VISUAL METRICS (PRP-006) - 2 metrics
    screenshots_captured: Mapped[Optional[bool]] = mapped_column(Boolean)  # Screenshots Captured
    screenshots_quality_assessment: Mapped[Optional[int]] = mapped_column(Integer)  # Image Quality Assessment
    
    # SEMRUSH METRICS (PRP-007) - 6 metrics
    semrush_site_health_score: Mapped[Optional[int]] = mapped_column(Integer)      # Site Health Score
    semrush_backlink_toxicity_score: Mapped[Optional[int]] = mapped_column(Integer)  # Backlink Toxicity Score
    semrush_organic_traffic_est: Mapped[Optional[int]] = mapped_column(Integer)    # Organic Traffic Est.
    semrush_ranking_keywords_count: Mapped[Optional[int]] = mapped_column(Integer)  # Ranking Keywords (#)
    semrush_domain_authority_score: Mapped[Optional[int]] = mapped_column(Integer)  # Domain Authority Score
    semrush_top_issue_categories: Mapped[Optional[dict]] = mapped_column(JSON)     # Top Issue Categories
    
    # LIGHTHOUSE/VISUAL ASSESSMENT METRICS (PRP-008) - 13 metrics
    visual_performance_score: Mapped[Optional[int]] = mapped_column(Integer)      # Performance Score (headless)
    visual_accessibility_score: Mapped[Optional[int]] = mapped_column(Integer)    # Accessibility Score
    visual_best_practices_score: Mapped[Optional[int]] = mapped_column(Integer)   # Best-Practices Score
    visual_seo_score: Mapped[Optional[int]] = mapped_column(Integer)              # SEO Score
    visual_above_fold_clarity: Mapped[Optional[int]] = mapped_column(Integer)     # Visual rubric #1
    visual_cta_prominence: Mapped[Optional[int]] = mapped_column(Integer)         # Visual rubric #2
    visual_trust_signals: Mapped[Optional[int]] = mapped_column(Integer)          # Visual rubric #3
    visual_hierarchy_contrast: Mapped[Optional[int]] = mapped_column(Integer)     # Visual rubric #4
    visual_text_readability: Mapped[Optional[int]] = mapped_column(Integer)       # Visual rubric #5
    visual_brand_cohesion: Mapped[Optional[int]] = mapped_column(Integer)         # Visual rubric #6
    visual_image_quality: Mapped[Optional[int]] = mapped_column(Integer)          # Visual rubric #7
    visual_mobile_responsive: Mapped[Optional[int]] = mapped_column(Integer)      # Visual rubric #8
    visual_clutter_balance: Mapped[Optional[int]] = mapped_column(Integer)        # Visual rubric #9
    
    # LLM CONTENT GENERATOR METRICS (PRP-010) - 7 metrics
    content_unique_value_prop_clarity: Mapped[Optional[int]] = mapped_column(Integer)  # Unique Value Prop clarity
    content_contact_info_presence: Mapped[Optional[int]] = mapped_column(Integer)      # Contact Info presence
    content_next_step_clarity: Mapped[Optional[int]] = mapped_column(Integer)          # Next-Step clarity (CTA)
    content_social_proof_presence: Mapped[Optional[int]] = mapped_column(Integer)      # Social-Proof presence
    content_quality_score: Mapped[Optional[int]] = mapped_column(Integer)              # Content Quality Score
    content_brand_voice_consistency: Mapped[Optional[int]] = mapped_column(Integer)    # Brand Voice Consistency
    content_spam_score_assessment: Mapped[Optional[int]] = mapped_column(Integer)      # Spam Score Assessment
    
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
    
    def get_all_metrics(self) -> dict:
        """
        Returns all 53 metrics with human-readable labels
        Matches the format from ASSESSMENT_PROGRESS_TRACKER.md
        """
        return {
            # PAGESPEED METRICS (PRP-003) - 7 metrics
            "First Contentful Paint (FCP)": self.pagespeed_fcp_ms,
            "Largest Contentful Paint (LCP)": self.pagespeed_lcp_ms,
            "Cumulative Layout Shift (CLS)": self.pagespeed_cls,
            "Total Blocking Time (TBT)": self.pagespeed_tbt_ms,
            "Time to Interactive (TTI)": self.pagespeed_tti_ms,
            "Speed Index": self.pagespeed_speed_index,
            "Performance Score (runtime)": self.pagespeed_performance_score,
            
            # TECHNICAL/SECURITY METRICS (PRP-004) - 9 metrics
            "HTTPS enforced?": self.security_https_enforced,
            "TLS Version": self.security_tls_version,
            "HSTS Header present": self.security_hsts_header_present,
            "Content-Security-Policy header": self.security_csp_header_present,
            "X-Frame-Options header": self.security_xframe_options_header,
            "robots.txt found": self.tech_robots_txt_found,
            "sitemap.xml found": self.tech_sitemap_xml_found,
            "Broken internal links (#)": self.tech_broken_internal_links_count,
            "JS console errors (#)": self.tech_js_console_errors_count,
            
            # GOOGLE BUSINESS PROFILE METRICS (PRP-005) - 9 metrics
            "hours": self.gbp_hours,
            "review_count": self.gbp_review_count,
            "rating": self.gbp_rating,
            "photos_count": self.gbp_photos_count,
            "total_reviews": self.gbp_total_reviews,
            "avg_rating": self.gbp_avg_rating,
            "recent_90d": self.gbp_recent_90d,
            "rating_trend": self.gbp_rating_trend,
            "is_closed": self.gbp_is_closed,
            
            # SCREENSHOT/VISUAL METRICS (PRP-006) - 2 metrics
            "Screenshots Captured": self.screenshots_captured,
            "Image Quality Assessment": self.screenshots_quality_assessment,
            
            # SEMRUSH METRICS (PRP-007) - 6 metrics
            "Site Health Score": self.semrush_site_health_score,
            "Backlink Toxicity Score": self.semrush_backlink_toxicity_score,
            "Organic Traffic Est.": self.semrush_organic_traffic_est,
            "Ranking Keywords (#)": self.semrush_ranking_keywords_count,
            "Domain Authority Score": self.semrush_domain_authority_score,
            "Top Issue Categories": self.semrush_top_issue_categories,
            
            # LIGHTHOUSE/VISUAL ASSESSMENT METRICS (PRP-008) - 13 metrics
            "Performance Score (headless)": self.visual_performance_score,
            "Accessibility Score": self.visual_accessibility_score,
            "Best-Practices Score": self.visual_best_practices_score,
            "SEO Score": self.visual_seo_score,
            "Visual rubric #1 – Above-the-fold clarity": self.visual_above_fold_clarity,
            "Visual rubric #2 – Primary CTA prominence": self.visual_cta_prominence,
            "Visual rubric #3 – Trust signals present": self.visual_trust_signals,
            "Visual rubric #4 – Visual hierarchy / contrast": self.visual_hierarchy_contrast,
            "Visual rubric #5 – Text readability": self.visual_text_readability,
            "Visual rubric #6 – Brand colour cohesion": self.visual_brand_cohesion,
            "Visual rubric #7 – Image quality": self.visual_image_quality,
            "Visual rubric #8 – Mobile responsiveness hint": self.visual_mobile_responsive,
            "Visual rubric #9 – Clutter / white-space balance": self.visual_clutter_balance,
            
            # LLM CONTENT GENERATOR METRICS (PRP-010) - 7 metrics
            "Unique Value Prop clarity": self.content_unique_value_prop_clarity,
            "Contact Info presence": self.content_contact_info_presence,
            "Next-Step clarity (CTA)": self.content_next_step_clarity,
            "Social-Proof presence": self.content_social_proof_presence,
            "Content Quality Score": self.content_quality_score,
            "Brand Voice Consistency": self.content_brand_voice_consistency,
            "Spam Score Assessment": self.content_spam_score_assessment,
        }
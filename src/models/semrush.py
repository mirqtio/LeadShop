"""
SEMrush Domain Analytics Data Models
Comprehensive models for storing SEMrush SEO analysis data
"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, Text, JSON, ForeignKey, DateTime, func, UniqueConstraint, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from src.core.database import Base


class IssueSeverity(str, enum.Enum):
    """Severity levels for technical issues"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueType(str, enum.Enum):
    """Types of technical issues"""
    SEO = "SEO"
    TRAFFIC = "Traffic"
    TECHNICAL = "Technical"


class SEMrushAnalysis(Base):
    """
    Main SEMrush domain analysis results
    Stores domain authority, traffic metrics, and comprehensive SEO data
    """
    __tablename__ = "semrush_analysis"
    
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
    
    # Domain identification
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    analysis_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Authority and trust metrics
    authority_score: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 0-100
    backlink_toxicity_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0-100 percentage
    
    # Traffic and visibility metrics
    organic_traffic_estimate: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # Monthly estimate
    ranking_keywords_count: Mapped[int] = mapped_column(Integer, nullable=False)  # Total ranking keywords
    site_health_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0-100 percentage
    
    # Backlink metrics
    referring_domains_count: Mapped[Optional[int]] = mapped_column(Integer)
    total_backlinks_count: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Performance and cost tracking
    extraction_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    api_cost_units: Mapped[float] = mapped_column(Float, nullable=False)  # API units consumed
    cost_cents: Mapped[Optional[float]] = mapped_column(Float)  # Cost in cents
    
    # API metadata
    api_database: Mapped[str] = mapped_column(String(10), default="us")  # SEMrush database used
    api_balance_remaining: Mapped[Optional[int]] = mapped_column(Integer)  # API units remaining after call
    
    # Raw data storage
    raw_domain_overview: Mapped[Optional[dict]] = mapped_column(JSON)  # Raw API response data
    raw_backlinks_data: Mapped[Optional[dict]] = mapped_column(JSON)  # Raw backlinks response
    raw_organic_data: Mapped[Optional[dict]] = mapped_column(JSON)  # Raw organic search data
    
    # Relationships
    assessment: Mapped["Assessment"] = relationship("Assessment", backref="semrush_analyses")
    technical_issues: Mapped[List["SEMrushTechnicalIssue"]] = relationship(
        "SEMrushTechnicalIssue",
        back_populates="analysis",
        cascade="all, delete-orphan"
    )
    keyword_rankings: Mapped[List["SEMrushKeywordRanking"]] = relationship(
        "SEMrushKeywordRanking",
        back_populates="analysis",
        cascade="all, delete-orphan"
    )
    competitor_insights: Mapped[List["SEMrushCompetitorInsight"]] = relationship(
        "SEMrushCompetitorInsight",
        back_populates="analysis",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<SEMrushAnalysis(id={self.id}, domain='{self.domain}', authority={self.authority_score})>"


class SEMrushTechnicalIssue(Base):
    """
    Technical SEO issues identified during SEMrush analysis
    Stores individual issues with severity and recommendations
    """
    __tablename__ = "semrush_technical_issues"
    __table_args__ = (
        UniqueConstraint('semrush_analysis_id', 'issue_type', 'category', name='uq_semrush_issue'),
    )
    
    # Primary key and relationships
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    semrush_analysis_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("semrush_analysis.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Issue details
    issue_type: Mapped[str] = mapped_column(Enum(IssueType), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(Enum(IssueSeverity), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # Issue category
    description: Mapped[str] = mapped_column(Text, nullable=False)  # Human-readable description
    
    # Impact and recommendations
    affected_pages_count: Mapped[Optional[int]] = mapped_column(Integer)
    estimated_impact: Mapped[Optional[str]] = mapped_column(String(50))  # low, medium, high
    recommendation: Mapped[Optional[str]] = mapped_column(Text)
    priority_score: Mapped[Optional[int]] = mapped_column(Integer)  # 1-10 priority
    
    # Additional metadata
    first_detected: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolution_time_estimate_hours: Mapped[Optional[float]] = mapped_column(Float)
    technical_details: Mapped[Optional[dict]] = mapped_column(JSON)  # Additional technical data
    
    # Relationships
    analysis: Mapped["SEMrushAnalysis"] = relationship("SEMrushAnalysis", back_populates="technical_issues")
    
    def __repr__(self) -> str:
        return f"<SEMrushTechnicalIssue(id={self.id}, type='{self.issue_type}', severity='{self.severity}')>"


class SEMrushKeywordRanking(Base):
    """
    Top keyword rankings from SEMrush organic search data
    Stores keyword performance metrics and opportunities
    """
    __tablename__ = "semrush_keyword_rankings"
    
    # Primary key and relationships
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    semrush_analysis_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("semrush_analysis.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Keyword identification
    keyword: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)  # SERP position
    
    # Traffic and value metrics
    search_volume: Mapped[int] = mapped_column(Integer, nullable=False)  # Monthly searches
    cpc: Mapped[Optional[float]] = mapped_column(Float)  # Cost per click in USD
    competition_level: Mapped[Optional[float]] = mapped_column(Float)  # 0-1 competition score
    traffic_percentage: Mapped[Optional[float]] = mapped_column(Float)  # % of total organic traffic
    
    # Trend and opportunity data
    position_change: Mapped[Optional[int]] = mapped_column(Integer)  # Position change vs previous period
    trend: Mapped[Optional[str]] = mapped_column(String(20))  # rising, falling, stable
    difficulty_score: Mapped[Optional[int]] = mapped_column(Integer)  # 0-100 keyword difficulty
    
    # SERP features
    serp_features: Mapped[Optional[List[str]]] = mapped_column(JSON)  # Featured snippets, etc.
    url: Mapped[Optional[str]] = mapped_column(String(1024))  # Ranking URL
    
    # Relationships
    analysis: Mapped["SEMrushAnalysis"] = relationship("SEMrushAnalysis", back_populates="keyword_rankings")
    
    def __repr__(self) -> str:
        return f"<SEMrushKeywordRanking(id={self.id}, keyword='{self.keyword}', position={self.position})>"


class SEMrushCompetitorInsight(Base):
    """
    Competitor analysis insights from SEMrush
    Stores competitive positioning and gap analysis data
    """
    __tablename__ = "semrush_competitor_insights"
    
    # Primary key and relationships
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    semrush_analysis_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("semrush_analysis.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Competitor identification
    competitor_domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    competition_level: Mapped[str] = mapped_column(String(20), nullable=False)  # high, medium, low
    
    # Competitive metrics
    common_keywords_count: Mapped[int] = mapped_column(Integer, nullable=False)
    competitor_authority_score: Mapped[Optional[int]] = mapped_column(Integer)  # 0-100
    competitor_traffic_estimate: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Gap analysis
    keyword_gap_count: Mapped[Optional[int]] = mapped_column(Integer)  # Keywords competitor ranks for
    traffic_gap_percentage: Mapped[Optional[float]] = mapped_column(Float)  # Traffic difference %
    authority_gap: Mapped[Optional[int]] = mapped_column(Integer)  # Authority score difference
    
    # Opportunity scoring
    opportunity_score: Mapped[Optional[float]] = mapped_column(Float)  # 0-100 opportunity rating
    recommended_actions: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # Relationships
    analysis: Mapped["SEMrushAnalysis"] = relationship("SEMrushAnalysis", back_populates="competitor_insights")
    
    def __repr__(self) -> str:
        return f"<SEMrushCompetitorInsight(id={self.id}, competitor='{self.competitor_domain}', level='{self.competition_level}')>"
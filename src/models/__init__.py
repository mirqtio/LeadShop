# Database models for LeadFactory

from src.models.lead import Lead, Assessment, Campaign, Sale
from src.models.assessment_results import AssessmentResults
from src.models.assessment_cost import AssessmentCost
from src.models.pagespeed import (
    PageSpeedAnalysis,
    PageSpeedAudit,
    PageSpeedScreenshot,
    PageSpeedElement,
    PageSpeedEntity,
    PageSpeedOpportunity
)
from src.models.security import (
    SecurityAnalysis,
    SecurityHeader,
    SecurityVulnerability,
    SecurityCookie,
    SecurityRecommendation
)
from src.models.gbp import (
    GBPAnalysis,
    GBPBusinessHours,
    GBPReviews,
    GBPPhotos
)
from src.models.screenshot import (
    Screenshot,
    ScreenshotRegion,
    ScreenshotComparison,
    ScreenshotType,
    ScreenshotStatus
)
from src.models.visual_analysis import (
    VisualAnalysis,
    DesignElement,
    UXIssue,
    VisualBenchmark,
    AnalysisStatus
)
from src.models.semrush import (
    SEMrushAnalysis,
    SEMrushTechnicalIssue,
    SEMrushKeywordRanking,
    SEMrushCompetitorInsight,
    IssueSeverity,
    IssueType
)

__all__ = [
    "Lead",
    "Assessment",
    "AssessmentResults",
    "Campaign", 
    "Sale",
    "AssessmentCost",
    "PageSpeedAnalysis",
    "PageSpeedAudit",
    "PageSpeedScreenshot",
    "PageSpeedElement",
    "PageSpeedEntity",
    "PageSpeedOpportunity",
    "SecurityAnalysis",
    "SecurityHeader",
    "SecurityVulnerability",
    "SecurityCookie",
    "SecurityRecommendation",
    "GBPAnalysis",
    "GBPBusinessHours",
    "GBPReviews",
    "GBPPhotos",
    "Screenshot",
    "ScreenshotRegion",
    "ScreenshotComparison",
    "ScreenshotType",
    "ScreenshotStatus",
    "VisualAnalysis",
    "DesignElement",
    "UXIssue",
    "VisualBenchmark",
    "AnalysisStatus",
    "SEMrushAnalysis",
    "SEMrushTechnicalIssue",
    "SEMrushKeywordRanking",
    "SEMrushCompetitorInsight",
    "IssueSeverity",
    "IssueType"
]
"""
PageSpeed Data Retrieval Helpers
Helper functions to retrieve and format PageSpeed data from new database tables
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.models.pagespeed import (
    PageSpeedAnalysis, PageSpeedAudit, PageSpeedScreenshot,
    PageSpeedElement, PageSpeedEntity, PageSpeedOpportunity
)
from src.models.assessment_results import AssessmentResults


async def get_pagespeed_data_for_assessment(db: AsyncSession, assessment_id: int) -> Dict[str, Any]:
    """
    Retrieve all PageSpeed data from new tables for a given assessment
    
    Args:
        db: Database session
        assessment_id: Assessment ID to retrieve data for
        
    Returns:
        Dict containing formatted PageSpeed data for UI display
    """
    # Query PageSpeed analyses with related data
    result = await db.execute(
        select(PageSpeedAnalysis)
        .options(
            selectinload(PageSpeedAnalysis.audits),
            selectinload(PageSpeedAnalysis.screenshots),
            selectinload(PageSpeedAnalysis.entities),
            selectinload(PageSpeedAnalysis.opportunities)
        )
        .where(PageSpeedAnalysis.assessment_id == assessment_id)
    )
    analyses = result.scalars().all()
    
    # Separate mobile and desktop analyses
    mobile_analysis = None
    desktop_analysis = None
    
    for analysis in analyses:
        if analysis.strategy == 'mobile':
            mobile_analysis = analysis
        elif analysis.strategy == 'desktop':
            desktop_analysis = analysis
    
    # Format data for UI consumption
    pagespeed_data = {
        "mobile_analysis": format_pagespeed_analysis(mobile_analysis) if mobile_analysis else None,
        "desktop_analysis": format_pagespeed_analysis(desktop_analysis) if desktop_analysis else None,
        "primary_strategy": "mobile",
        "has_data": bool(mobile_analysis or desktop_analysis)
    }
    
    # Add core web vitals from mobile (primary) analysis
    if mobile_analysis:
        pagespeed_data["core_web_vitals"] = {
            "first_contentful_paint": mobile_analysis.first_contentful_paint_ms,
            "largest_contentful_paint": mobile_analysis.largest_contentful_paint_ms,
            "cumulative_layout_shift": mobile_analysis.cumulative_layout_shift,
            "total_blocking_time": mobile_analysis.total_blocking_time_ms,
            "time_to_interactive": mobile_analysis.time_to_interactive_ms,
            "speed_index": mobile_analysis.speed_index_ms,
            "performance_score": mobile_analysis.performance_score
        }
        pagespeed_data["performance_score"] = mobile_analysis.performance_score
    
    return pagespeed_data


def format_pagespeed_analysis(analysis: PageSpeedAnalysis) -> Dict[str, Any]:
    """
    Format a PageSpeedAnalysis object for UI display
    
    Args:
        analysis: PageSpeedAnalysis object
        
    Returns:
        Dict containing formatted analysis data
    """
    if not analysis:
        return None
    
    formatted = {
        "url": analysis.url,
        "strategy": analysis.strategy,
        "analysis_timestamp": analysis.analysis_timestamp.isoformat() if analysis.analysis_timestamp else None,
        "analysis_duration_ms": analysis.analysis_duration_ms,
        "cost_cents": analysis.cost_cents,
        
        # Core Web Vitals
        "core_web_vitals": {
            "first_contentful_paint": analysis.first_contentful_paint_ms,
            "largest_contentful_paint": analysis.largest_contentful_paint_ms,
            "cumulative_layout_shift": analysis.cumulative_layout_shift,
            "total_blocking_time": analysis.total_blocking_time_ms,
            "time_to_interactive": analysis.time_to_interactive_ms,
            "speed_index": analysis.speed_index_ms,
            "performance_score": analysis.performance_score
        },
        
        # Category scores
        "category_scores": {
            "performance": analysis.performance_score,
            "accessibility": analysis.accessibility_score,
            "best_practices": analysis.best_practices_score,
            "seo": analysis.seo_score,
            "pwa": analysis.pwa_score
        },
        
        # Metadata
        "lighthouse_version": analysis.lighthouse_version,
        "user_agent": analysis.user_agent,
        
        # Detailed audit results
        "audits": format_audits(analysis.audits),
        
        # Screenshots
        "screenshots": format_screenshots(analysis.screenshots),
        
        # Third-party entities
        "entities": format_entities(analysis.entities),
        
        # Performance opportunities
        "opportunities": format_opportunities(analysis.opportunities),
        
        # URLs
        "urls": {
            "requested": analysis.requested_url,
            "final": analysis.final_url,
            "main_document": analysis.main_document_url,
            "displayed": analysis.final_displayed_url
        }
    }
    
    # Add lighthouse result if needed (for backward compatibility)
    if hasattr(analysis, 'raw_lighthouse_result') and analysis.raw_lighthouse_result:
        formatted["lighthouse_result"] = analysis.raw_lighthouse_result
    
    return formatted


def format_audits(audits: List[PageSpeedAudit]) -> Dict[str, Any]:
    """Format audit results for UI display"""
    formatted_audits = {}
    
    for audit in audits:
        formatted_audits[audit.audit_id] = {
            "title": audit.title,
            "description": audit.description,
            "score": audit.score,
            "scoreDisplayMode": audit.score_display_mode,
            "displayValue": audit.display_value,
            "explanation": audit.explanation,
            "errorMessage": audit.error_message,
            "warnings": audit.warnings,
            "details": audit.details,
            "numericValue": audit.numeric_value,
            "numericUnit": audit.numeric_unit
        }
    
    return formatted_audits


def format_screenshots(screenshots: List[PageSpeedScreenshot]) -> List[Dict[str, Any]]:
    """Format screenshots for UI display"""
    formatted_screenshots = []
    
    for screenshot in screenshots:
        formatted_screenshots.append({
            "type": screenshot.screenshot_type,
            "data": screenshot.data,
            "data_url": screenshot.data_url,
            "dimensions": {
                "width": screenshot.width,
                "height": screenshot.height
            },
            "mime_type": screenshot.mime_type,
            "timestamp_ms": screenshot.timestamp_ms
        })
    
    return formatted_screenshots


def format_entities(entities: List[PageSpeedEntity]) -> List[Dict[str, Any]]:
    """Format third-party entities for UI display"""
    formatted_entities = []
    
    for entity in entities:
        formatted_entities.append({
            "name": entity.name,
            "homepage": entity.homepage,
            "category": entity.category,
            "is_first_party": entity.is_first_party,
            "is_unrecognized": entity.is_unrecognized,
            "metrics": {
                "total_bytes": entity.total_bytes,
                "total_tasks": entity.total_tasks,
                "total_task_time_ms": entity.total_task_time_ms,
                "main_thread_time_ms": entity.main_thread_time_ms,
                "blocking_time_ms": entity.blocking_time_ms,
                "transfer_size_bytes": entity.transfer_size_bytes
            }
        })
    
    return formatted_entities


def format_opportunities(opportunities: List[PageSpeedOpportunity]) -> List[Dict[str, Any]]:
    """Format performance opportunities for UI display"""
    formatted_opportunities = []
    
    for opportunity in opportunities:
        formatted_opportunities.append({
            "audit_id": opportunity.audit_id,
            "title": opportunity.title,
            "description": opportunity.description,
            "savings": {
                "ms": opportunity.savings_ms,
                "bytes": opportunity.savings_bytes
            },
            "rating": opportunity.rating,
            "details": opportunity.details
        })
    
    # Sort by savings_ms descending
    formatted_opportunities.sort(key=lambda x: x["savings"]["ms"] or 0, reverse=True)
    
    return formatted_opportunities


async def update_assessment_results_pagespeed_metrics(
    db: AsyncSession, 
    assessment_id: int, 
    mobile_analysis: Optional[PageSpeedAnalysis]
) -> None:
    """
    Update AssessmentResults table with PageSpeed metrics
    
    Args:
        db: Database session
        assessment_id: Assessment ID
        mobile_analysis: Mobile PageSpeed analysis (primary)
    """
    # Get or create AssessmentResults record
    result = await db.execute(
        select(AssessmentResults).where(AssessmentResults.assessment_id == assessment_id)
    )
    assessment_results = result.scalar_one_or_none()
    
    if not assessment_results:
        assessment_results = AssessmentResults(assessment_id=assessment_id)
        db.add(assessment_results)
    
    # Update PageSpeed metrics if mobile analysis available
    if mobile_analysis:
        assessment_results.pagespeed_fcp_ms = mobile_analysis.first_contentful_paint_ms
        assessment_results.pagespeed_lcp_ms = mobile_analysis.largest_contentful_paint_ms
        assessment_results.pagespeed_cls = mobile_analysis.cumulative_layout_shift
        assessment_results.pagespeed_tbt_ms = mobile_analysis.total_blocking_time_ms
        assessment_results.pagespeed_tti_ms = mobile_analysis.time_to_interactive_ms
        assessment_results.pagespeed_speed_index = mobile_analysis.speed_index_ms
        assessment_results.pagespeed_performance_score = mobile_analysis.performance_score
    
    await db.flush()
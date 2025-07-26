"""
PRP-014: Decompose Assessment Metrics
Extracts individual metrics from JSON blobs and stores them in assessment_results table
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.lead import Assessment
from src.models.assessment_results import AssessmentResults

logger = logging.getLogger(__name__)


async def extract_pagespeed_metrics_from_new_tables(db: AsyncSession, assessment_id: int) -> Dict[str, Any]:
    """Extract PageSpeed metrics from the new PageSpeedAnalysis table"""
    from src.models.pagespeed import PageSpeedAnalysis
    
    try:
        # Get mobile analysis (primary)
        result = await db.execute(
            select(PageSpeedAnalysis).where(
                PageSpeedAnalysis.assessment_id == assessment_id,
                PageSpeedAnalysis.strategy == 'mobile'
            )
        )
        mobile_analysis = result.scalar_one_or_none()
        
        if not mobile_analysis:
            return {}
        
        metrics = {
            'pagespeed_fcp_ms': mobile_analysis.first_contentful_paint_ms,
            'pagespeed_lcp_ms': mobile_analysis.largest_contentful_paint_ms,
            'pagespeed_cls': mobile_analysis.cumulative_layout_shift,
            'pagespeed_tbt_ms': mobile_analysis.total_blocking_time_ms,
            'pagespeed_tti_ms': mobile_analysis.time_to_interactive_ms,
            'pagespeed_speed_index': mobile_analysis.speed_index_ms,
            'pagespeed_performance_score': mobile_analysis.performance_score
        }
        
        # Remove None values
        return {k: v for k, v in metrics.items() if v is not None}
        
    except Exception as e:
        logger.error(f"Failed to extract PageSpeed metrics: {e}")
        return {}


def extract_pagespeed_metrics(pagespeed_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract individual PageSpeed metrics from JSON data"""
    if not pagespeed_data:
        return {}
    
    metrics = {}
    
    # Try new format first (from assessment orchestrator)
    if 'mobile_analysis' in pagespeed_data and 'core_web_vitals' in pagespeed_data.get('mobile_analysis', {}):
        cwv = pagespeed_data['mobile_analysis']['core_web_vitals']
        metrics['pagespeed_fcp_ms'] = int(round(float(cwv.get('first_contentful_paint', 0)))) if cwv.get('first_contentful_paint') else None
        metrics['pagespeed_lcp_ms'] = int(round(float(cwv.get('largest_contentful_paint', 0)))) if cwv.get('largest_contentful_paint') else None
        metrics['pagespeed_cls'] = float(cwv.get('cumulative_layout_shift', 0)) if cwv.get('cumulative_layout_shift') is not None else None
        metrics['pagespeed_tbt_ms'] = int(round(float(cwv.get('total_blocking_time', 0)))) if cwv.get('total_blocking_time') else None
        metrics['pagespeed_tti_ms'] = int(round(float(cwv.get('time_to_interactive', 0)))) if cwv.get('time_to_interactive') else None
        metrics['pagespeed_performance_score'] = int(cwv.get('performance_score', 0)) if cwv.get('performance_score') is not None else None
        
        # Get speed index from lighthouse_result audits
        mobile_audits = pagespeed_data['mobile_analysis'].get('lighthouse_result', {}).get('audits', {})
        if 'speed-index' in mobile_audits and mobile_audits['speed-index'].get('numericValue') is not None:
            metrics['pagespeed_speed_index'] = int(round(float(mobile_audits['speed-index']['numericValue'])))
        
    # Also check desktop_analysis if available
    elif 'desktop_analysis' in pagespeed_data and 'core_web_vitals' in pagespeed_data.get('desktop_analysis', {}):
        cwv = pagespeed_data['desktop_analysis']['core_web_vitals']
        metrics['pagespeed_fcp_ms'] = int(round(float(cwv.get('first_contentful_paint', 0)))) if cwv.get('first_contentful_paint') else None
        metrics['pagespeed_lcp_ms'] = int(round(float(cwv.get('largest_contentful_paint', 0)))) if cwv.get('largest_contentful_paint') else None
        metrics['pagespeed_cls'] = float(cwv.get('cumulative_layout_shift', 0)) if cwv.get('cumulative_layout_shift') is not None else None
        metrics['pagespeed_tbt_ms'] = int(round(float(cwv.get('total_blocking_time', 0)))) if cwv.get('total_blocking_time') else None
        metrics['pagespeed_tti_ms'] = int(round(float(cwv.get('time_to_interactive', 0)))) if cwv.get('time_to_interactive') else None
        metrics['pagespeed_performance_score'] = int(cwv.get('performance_score', 0)) if cwv.get('performance_score') is not None else None
        
        # Get speed index from lighthouse_result audits
        desktop_audits = pagespeed_data['desktop_analysis'].get('lighthouse_result', {}).get('audits', {})
        if 'speed-index' in desktop_audits and desktop_audits['speed-index'].get('numericValue') is not None:
            metrics['pagespeed_speed_index'] = int(round(float(desktop_audits['speed-index']['numericValue'])))
        
    # Fall back to old format (lighthouseResult)
    else:
        audits = pagespeed_data.get('lighthouseResult', {}).get('audits', {})
        
        # Extract core web vitals
        if 'first-contentful-paint' in audits and audits['first-contentful-paint'].get('numericValue') is not None:
            metrics['pagespeed_fcp_ms'] = int(round(float(audits['first-contentful-paint']['numericValue'])))
        
        if 'largest-contentful-paint' in audits and audits['largest-contentful-paint'].get('numericValue') is not None:
            metrics['pagespeed_lcp_ms'] = int(round(float(audits['largest-contentful-paint']['numericValue'])))
        
        if 'cumulative-layout-shift' in audits and audits['cumulative-layout-shift'].get('numericValue') is not None:
            metrics['pagespeed_cls'] = float(audits['cumulative-layout-shift']['numericValue'])
        
        if 'total-blocking-time' in audits and audits['total-blocking-time'].get('numericValue') is not None:
            metrics['pagespeed_tbt_ms'] = int(round(float(audits['total-blocking-time']['numericValue'])))
        
        if 'interactive' in audits and audits['interactive'].get('numericValue') is not None:
            metrics['pagespeed_tti_ms'] = int(round(float(audits['interactive']['numericValue'])))
        
        if 'speed-index' in audits and audits['speed-index'].get('numericValue') is not None:
            metrics['pagespeed_speed_index'] = int(round(float(audits['speed-index']['numericValue'])))
        
        # Get overall performance score
        categories = pagespeed_data.get('lighthouseResult', {}).get('categories', {})
        if 'performance' in categories and categories['performance'].get('score') is not None:
            metrics['pagespeed_performance_score'] = int(round(categories['performance']['score'] * 100))
    
    return metrics


async def extract_security_metrics_from_new_tables(db: AsyncSession, assessment_id: int) -> Dict[str, Any]:
    """Extract Security metrics from the new SecurityAnalysis table"""
    from src.models.security import SecurityAnalysis, SecurityHeader
    from sqlalchemy.orm import selectinload
    
    try:
        result = await db.execute(
            select(SecurityAnalysis)
            .options(selectinload(SecurityAnalysis.headers))
            .where(SecurityAnalysis.assessment_id == assessment_id)
        )
        security_analysis = result.scalar_one_or_none()
        
        if not security_analysis:
            return {}
        
        metrics = {
            'security_https_enforced': security_analysis.has_https,
            'security_tls_version': security_analysis.ssl_protocol or '',
            'security_hsts_header_present': False,
            'security_csp_header_present': False,
            'security_xframe_options_header': False,
        }
        
        # Check specific headers
        for header in security_analysis.headers:
            if header.header_name.lower() == 'strict-transport-security':
                metrics['security_hsts_header_present'] = header.is_present
            elif header.header_name.lower() == 'content-security-policy':
                metrics['security_csp_header_present'] = header.is_present
            elif header.header_name.lower() == 'x-frame-options':
                metrics['security_xframe_options_header'] = header.is_present
        
        # Add placeholders for tech metrics (these might come from elsewhere)
        metrics['tech_robots_txt_found'] = False
        metrics['tech_sitemap_xml_found'] = False
        metrics['tech_broken_internal_links_count'] = 0
        metrics['tech_js_console_errors_count'] = 0
        
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to extract Security metrics: {e}")
        return {}


def extract_security_metrics(security_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract individual security metrics from JSON data"""
    if not security_data:
        return {}
    
    metrics = {}
    
    # Extract security headers and technical checks
    # Handle both old and new format
    metrics['security_https_enforced'] = security_data.get('https_enforced', security_data.get('has_https', False))
    metrics['security_tls_version'] = security_data.get('tls_version', security_data.get('ssl_protocol', ''))
    
    # Check headers_analysis for detailed header info
    headers_analysis = security_data.get('headers_analysis', {})
    metrics['security_hsts_header_present'] = security_data.get('hsts_present', headers_analysis.get('hsts', {}).get('present', False))
    metrics['security_csp_header_present'] = security_data.get('csp_present', headers_analysis.get('csp', {}).get('present', False))
    metrics['security_xframe_options_header'] = security_data.get('x_frame_options_present', headers_analysis.get('x_frame_options', {}).get('present', False))
    
    # Technical checks - these are typically not in security data but we'll check anyway
    metrics['tech_robots_txt_found'] = security_data.get('robots_txt_found', False)
    metrics['tech_sitemap_xml_found'] = security_data.get('sitemap_xml_found', False)
    metrics['tech_broken_internal_links_count'] = security_data.get('broken_links_count', 0)
    metrics['tech_js_console_errors_count'] = security_data.get('console_errors_count', 0)
    
    return metrics


async def extract_gbp_metrics_from_new_tables(db: AsyncSession, assessment_id: int) -> Dict[str, Any]:
    """Extract GBP metrics from the new GBPAnalysis table"""
    from src.models.gbp import GBPAnalysis
    
    try:
        result = await db.execute(
            select(GBPAnalysis).where(GBPAnalysis.assessment_id == assessment_id)
        )
        gbp_analysis = result.scalar_one_or_none()
        
        if not gbp_analysis:
            return {}
        
        metrics = {
            'gbp_hours': {'available': not gbp_analysis.is_24_hours},  # Simple availability indicator
            'gbp_review_count': gbp_analysis.total_reviews,
            'gbp_rating': gbp_analysis.average_rating,
            'gbp_photos_count': gbp_analysis.total_photos,
            'gbp_total_reviews': gbp_analysis.total_reviews,
            'gbp_avg_rating': gbp_analysis.average_rating,
            'gbp_recent_90d': gbp_analysis.recent_90d_reviews,
            'gbp_rating_trend': gbp_analysis.rating_trend or 'stable',
            'gbp_is_closed': gbp_analysis.is_permanently_closed
        }
        
        # Remove None values
        return {k: v for k, v in metrics.items() if v is not None}
        
    except Exception as e:
        logger.error(f"Failed to extract GBP metrics: {e}")
        return {}


def extract_gbp_metrics(gbp_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract individual Google Business Profile metrics from JSON data"""
    if not gbp_data:
        return {}
    
    metrics = {}
    
    # Extract GBP metrics - handle different formats
    # Check if business was found
    if gbp_data.get('found', False):
        metrics['gbp_hours'] = gbp_data.get('hours', gbp_data.get('opening_hours', {}))
        metrics['gbp_review_count'] = gbp_data.get('review_count', gbp_data.get('user_ratings_total', 0))
        metrics['gbp_rating'] = gbp_data.get('rating', 0.0)
        metrics['gbp_photos_count'] = gbp_data.get('photos_count', 0)
        metrics['gbp_total_reviews'] = gbp_data.get('total_reviews', gbp_data.get('user_ratings_total', 0))
        metrics['gbp_avg_rating'] = gbp_data.get('avg_rating', gbp_data.get('rating', 0.0))
        metrics['gbp_recent_90d'] = gbp_data.get('recent_90d', 0)
        metrics['gbp_rating_trend'] = gbp_data.get('rating_trend', 'unknown')
        metrics['gbp_is_closed'] = gbp_data.get('is_closed', gbp_data.get('business_status', '') == 'CLOSED_PERMANENTLY')
    else:
        # Business not found - set default values
        metrics['gbp_hours'] = {}
        metrics['gbp_review_count'] = 0
        metrics['gbp_rating'] = 0.0
        metrics['gbp_photos_count'] = 0
        metrics['gbp_total_reviews'] = 0
        metrics['gbp_avg_rating'] = 0.0
        metrics['gbp_recent_90d'] = 0
        metrics['gbp_rating_trend'] = 'unknown'
        metrics['gbp_is_closed'] = False
    
    return metrics


async def extract_semrush_metrics_from_new_tables(db: AsyncSession, assessment_id: int) -> Dict[str, Any]:
    """Extract SEMrush metrics from the new SEMrushAnalysis table"""
    from src.models.semrush import SEMrushAnalysis
    
    try:
        result = await db.execute(
            select(SEMrushAnalysis).where(SEMrushAnalysis.assessment_id == assessment_id)
        )
        semrush_analysis = result.scalar_one_or_none()
        
        if not semrush_analysis:
            return {}
        
        metrics = {
            'semrush_site_health_score': semrush_analysis.site_health_score,
            'semrush_backlink_toxicity_score': semrush_analysis.backlink_toxicity_score,
            'semrush_organic_traffic_est': semrush_analysis.organic_traffic_estimate,
            'semrush_ranking_keywords_count': semrush_analysis.ranking_keywords_count,
            'semrush_domain_authority_score': semrush_analysis.authority_score,
            'semrush_top_issue_categories': []  # Would need to extract from technical_issues
        }
        
        # Remove None values
        return {k: v for k, v in metrics.items() if v is not None}
        
    except Exception as e:
        logger.error(f"Failed to extract SEMrush metrics: {e}")
        return {}


async def extract_screenshot_metrics_from_new_tables(db: AsyncSession, assessment_id: int) -> Dict[str, Any]:
    """Extract Screenshot metrics from the new Screenshot table"""
    from src.models.screenshot import Screenshot
    
    try:
        result = await db.execute(
            select(Screenshot).where(Screenshot.assessment_id == assessment_id)
        )
        screenshots = result.scalars().all()
        
        if not screenshots:
            return {}
        
        # Check if we have both desktop and mobile screenshots
        has_desktop = any(s.screenshot_type == 'desktop' for s in screenshots)
        has_mobile = any(s.screenshot_type == 'mobile' for s in screenshots)
        
        metrics = {
            'screenshots_captured': len(screenshots) > 0,
            'screenshots_quality_assessment': 85 if screenshots else 0  # Default quality score
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to extract Screenshot metrics: {e}")
        return {}


def extract_semrush_metrics(semrush_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract individual SEMrush metrics from JSON data"""
    if not semrush_data:
        return {}
    
    metrics = {}
    
    # Extract SEMrush metrics - handle different formats
    # Direct fields
    metrics['semrush_site_health_score'] = semrush_data.get('site_health_score', 0)
    metrics['semrush_backlink_toxicity_score'] = semrush_data.get('backlink_toxicity_score', 0)
    metrics['semrush_organic_traffic_est'] = semrush_data.get('organic_traffic_estimate', semrush_data.get('organic_traffic', 0))
    metrics['semrush_ranking_keywords_count'] = semrush_data.get('ranking_keywords_count', semrush_data.get('organic_keywords', 0))
    metrics['semrush_domain_authority_score'] = semrush_data.get('domain_authority_score', semrush_data.get('domain_score', 0))
    metrics['semrush_top_issue_categories'] = semrush_data.get('top_issue_categories', [])
    
    return metrics


def extract_visual_metrics(visual_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract individual visual assessment metrics from JSON data"""
    if not visual_data:
        return {}
    
    metrics = {}
    
    # Handle different possible formats of visual data
    # Check if we have scores directly or nested under 'scores'
    if 'scores' in visual_data and isinstance(visual_data['scores'], list):
        # New format with scores array
        scores = visual_data['scores']
        if len(scores) >= 9:
            metrics['visual_above_fold_clarity'] = scores[0]
            metrics['visual_cta_prominence'] = scores[1]
            metrics['visual_trust_signals'] = scores[2]
            metrics['visual_hierarchy_contrast'] = scores[3]
            metrics['visual_text_readability'] = scores[4]
            metrics['visual_brand_cohesion'] = scores[5]
            metrics['visual_image_quality'] = scores[6]
            metrics['visual_mobile_responsive'] = scores[7]
            metrics['visual_clutter_balance'] = scores[8]
    
    # Extract lighthouse-style scores
    metrics['visual_performance_score'] = visual_data.get('performance_score', 0)
    metrics['visual_accessibility_score'] = visual_data.get('accessibility_score', 0)
    metrics['visual_best_practices_score'] = visual_data.get('best_practices_score', 0)
    metrics['visual_seo_score'] = visual_data.get('seo_score', 0)
    
    # Extract visual rubrics (1-9) - fallback to old format
    if 'visual_rubrics' in visual_data:
        rubrics = visual_data.get('visual_rubrics', {})
        metrics['visual_above_fold_clarity'] = rubrics.get('above_fold_clarity', metrics.get('visual_above_fold_clarity', 0))
        metrics['visual_cta_prominence'] = rubrics.get('cta_prominence', metrics.get('visual_cta_prominence', 0))
        metrics['visual_trust_signals'] = rubrics.get('trust_signals', metrics.get('visual_trust_signals', 0))
        metrics['visual_hierarchy_contrast'] = rubrics.get('visual_hierarchy', metrics.get('visual_hierarchy_contrast', 0))
        metrics['visual_text_readability'] = rubrics.get('text_readability', metrics.get('visual_text_readability', 0))
        metrics['visual_brand_cohesion'] = rubrics.get('brand_cohesion', metrics.get('visual_brand_cohesion', 0))
        metrics['visual_image_quality'] = rubrics.get('image_quality', metrics.get('visual_image_quality', 0))
        metrics['visual_mobile_responsive'] = rubrics.get('mobile_responsiveness', metrics.get('visual_mobile_responsive', 0))
        metrics['visual_clutter_balance'] = rubrics.get('clutter_balance', metrics.get('visual_clutter_balance', 0))
    
    # Screenshots (from visual analysis results)
    metrics['screenshots_captured'] = visual_data.get('screenshots_captured', False)
    metrics['screenshots_quality_assessment'] = visual_data.get('screenshot_quality', 0)
    
    return metrics


def extract_content_metrics(llm_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract individual content generator metrics from JSON data"""
    if not llm_data:
        return {}
    
    metrics = {}
    
    # Extract content quality metrics
    content_analysis = llm_data.get('content_analysis', {})
    metrics['content_unique_value_prop_clarity'] = content_analysis.get('unique_value_prop_clarity', 0)
    metrics['content_contact_info_presence'] = content_analysis.get('contact_info_presence', 0)
    metrics['content_next_step_clarity'] = content_analysis.get('next_step_clarity', 0)
    metrics['content_social_proof_presence'] = content_analysis.get('social_proof_presence', 0)
    metrics['content_quality_score'] = content_analysis.get('content_quality_score', 0)
    metrics['content_brand_voice_consistency'] = content_analysis.get('brand_voice_consistency', 0)
    metrics['content_spam_score_assessment'] = content_analysis.get('spam_score_assessment', 0)
    
    return metrics


async def extract_pagespeed_metrics_from_db(db: AsyncSession, assessment_id: int) -> Dict[str, Any]:
    """
    Extract PageSpeed metrics from the new pagespeed_analysis table
    
    Args:
        db: Database session
        assessment_id: ID of the assessment
        
    Returns:
        Dict with PageSpeed metrics or empty dict if not found
    """
    from src.models.pagespeed import PageSpeedAnalysis
    
    try:
        # Get mobile analysis (primary) from new table
        result = await db.execute(
            select(PageSpeedAnalysis).where(
                PageSpeedAnalysis.assessment_id == assessment_id,
                PageSpeedAnalysis.strategy == 'mobile'
            )
        )
        mobile_analysis = result.scalar_one_or_none()
        
        if not mobile_analysis:
            return {}
        
        metrics = {
            'pagespeed_fcp_ms': mobile_analysis.first_contentful_paint_ms,
            'pagespeed_lcp_ms': mobile_analysis.largest_contentful_paint_ms,
            'pagespeed_cls': mobile_analysis.cumulative_layout_shift,
            'pagespeed_tbt_ms': mobile_analysis.total_blocking_time_ms,
            'pagespeed_tti_ms': mobile_analysis.time_to_interactive_ms,
            'pagespeed_speed_index': mobile_analysis.speed_index_ms,
            'pagespeed_performance_score': mobile_analysis.performance_score
        }
        
        # Remove None values
        metrics = {k: v for k, v in metrics.items() if v is not None}
        
        logger.info(f"Extracted {len(metrics)} PageSpeed metrics from database for assessment {assessment_id}")
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to extract PageSpeed metrics from database: {e}")
        return {}


async def decompose_and_store_metrics(
    db: AsyncSession,
    assessment_id: int
) -> Optional[AssessmentResults]:
    """
    Extract all individual metrics from assessment JSON blobs and store in assessment_results table
    
    Args:
        db: Database session
        assessment_id: ID of the assessment to decompose
        
    Returns:
        AssessmentResults object if successful, None if failed
    """
    try:
        # Get the assessment
        result = await db.execute(
            select(Assessment).where(Assessment.id == assessment_id)
        )
        assessment = result.scalar_one_or_none()
        
        if not assessment:
            logger.error(f"Assessment {assessment_id} not found")
            return None
        
        # Check if results already exist
        existing_result = await db.execute(
            select(AssessmentResults).where(AssessmentResults.assessment_id == assessment_id)
        )
        assessment_result = existing_result.scalar_one_or_none()
        
        if not assessment_result:
            # Create new assessment results record
            assessment_result = AssessmentResults(assessment_id=assessment_id)
            db.add(assessment_result)
        
        # Extract metrics from each component
        all_metrics = {}
        
        # PageSpeed metrics - check new table first, then fall back to JSON
        pagespeed_metrics = await extract_pagespeed_metrics_from_new_tables(db, assessment_id)
        if not pagespeed_metrics:
            # Fall back to JSON extraction
            pagespeed_metrics = extract_pagespeed_metrics(assessment.pagespeed_data)
        all_metrics.update(pagespeed_metrics)
        
        # Security/Technical metrics - check new table first, then fall back to JSON
        security_metrics = await extract_security_metrics_from_new_tables(db, assessment_id)
        if not security_metrics:
            # Fall back to JSON extraction
            security_metrics = extract_security_metrics(assessment.security_headers)
        all_metrics.update(security_metrics)
        
        # Google Business Profile metrics - check new table first, then fall back to JSON
        gbp_metrics = await extract_gbp_metrics_from_new_tables(db, assessment_id)
        if not gbp_metrics:
            # Fall back to JSON extraction
            gbp_metrics = extract_gbp_metrics(assessment.gbp_data)
        all_metrics.update(gbp_metrics)
        
        # SEMrush metrics - check new table first, then fall back to JSON
        semrush_metrics = await extract_semrush_metrics_from_new_tables(db, assessment_id)
        if not semrush_metrics:
            # Fall back to JSON extraction
            semrush_metrics = extract_semrush_metrics(assessment.semrush_data)
        all_metrics.update(semrush_metrics)
        
        # Visual analysis metrics
        visual_metrics = extract_visual_metrics(assessment.visual_analysis)
        all_metrics.update(visual_metrics)
        
        # Screenshot metrics - check new table
        screenshot_metrics = await extract_screenshot_metrics_from_new_tables(db, assessment_id)
        all_metrics.update(screenshot_metrics)
        
        # Content generator metrics (stored in llm_insights)
        content_metrics = extract_content_metrics(assessment.llm_insights)
        all_metrics.update(content_metrics)
        
        # Set all extracted metrics on the assessment_result object
        for metric_name, metric_value in all_metrics.items():
            if hasattr(assessment_result, metric_name):
                setattr(assessment_result, metric_name, metric_value)
            else:
                logger.warning(f"Unknown metric: {metric_name}")
        
        # Track which components had errors
        error_components = []
        if assessment.status == 'failed' and assessment.error_message:
            error_components.append(assessment.error_message)
        
        assessment_result.error_components = str(error_components) if error_components else None
        
        # Commit the changes
        await db.commit()
        await db.refresh(assessment_result)
        
        logger.info(f"Successfully decomposed {len(all_metrics)} metrics for assessment {assessment_id}")
        return assessment_result
        
    except Exception as e:
        logger.error(f"Failed to decompose metrics for assessment {assessment_id}: {e}")
        await db.rollback()
        return None


def sync_decompose_and_store_metrics(assessment_id: int) -> bool:
    """
    Synchronous wrapper for decompose_and_store_metrics
    Used by Celery tasks
    
    Args:
        assessment_id: ID of the assessment to decompose
        
    Returns:
        True if successful, False if failed
    """
    import asyncio
    from src.core.database import AsyncSessionLocal
    
    async def _decompose():
        async with AsyncSessionLocal() as db:
            result = await decompose_and_store_metrics(db, assessment_id)
            return result is not None
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_decompose())
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Sync decompose failed for assessment {assessment_id}: {e}")
        return False
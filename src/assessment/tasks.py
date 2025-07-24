"""
PRP-002: Assessment Tasks
Individual assessment task implementations with retry logic and error handling
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from celery.exceptions import Retry
from sqlalchemy import select

from src.core.celery_app import celery_app
from src.core.database import get_db
from src.models.lead import Lead, Assessment
from src.core.logging import get_logger
from .orchestrator import (
    update_assessment_field, 
    update_assessment_status, 
    ASSESSMENT_STATUS,
    AssessmentError
)

logger = get_logger(__name__)

# Task completion tracking for aggregation
ASSESSMENT_TASKS = [
    'pagespeed_task',
    'security_task', 
    'gbp_task',
    'screenshot_task',
    'semrush_task',
    'visual_task',
    'score_calculation_task',
    'content_generation_task',
    'report_generation_task',
    'email_formatting_task',
    'testing_dashboard_task',
    'full_assessment_orchestrator_task'
]

@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, AssessmentError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={'max_retries': 3},
    soft_time_limit=90,  # 90 second limit per task
    time_limit=120
)
def pagespeed_task(self, lead_id: int) -> Dict[str, Any]:
    """
    Execute PageSpeed Insights assessment with retry logic.
    
    Args:
        lead_id: Database ID of the lead to assess
        
    Returns:
        Dict containing PageSpeed assessment results
    """
    task_start = datetime.now(timezone.utc)
    
    try:
        logger.info(f"Starting PageSpeed assessment for lead {lead_id}")
        
        # Get lead information
        async def get_lead_url():
            async with get_db() as db:
                result = await db.execute(select(Lead).where(Lead.id == lead_id))
                lead = result.scalar_one_or_none()
                if not lead:
                    raise AssessmentError(f"Lead {lead_id} not found")
                if not lead.url:
                    raise AssessmentError(f"Lead {lead_id} has no URL for PageSpeed analysis")
                return lead.url, lead.company
        
        url, company = asyncio.run(get_lead_url())
        
        # PRP-003: Use actual PageSpeed API client
        from src.assessments.pagespeed import assess_pagespeed, PageSpeedError
        
        try:
            # Execute PageSpeed assessment with mobile-first strategy and cost tracking
            pagespeed_results = asyncio.run(assess_pagespeed(url, company, lead_id))
            
            # Extract performance score from Core Web Vitals
            performance_score = pagespeed_results.get("performance_score", 0)
            
            # Store cost records in database
            if pagespeed_results.get("cost_records"):
                async def store_cost_records():
                    async with get_db() as db:
                        for cost_record in pagespeed_results["cost_records"]:
                            db.add(cost_record)
                        await db.commit()
                
                asyncio.run(store_cost_records())
            
        except PageSpeedError as api_exc:
            # Log specific PageSpeed API errors
            logger.error(f"PageSpeed API error for lead {lead_id}: {api_exc}")
            raise AssessmentError(f"PageSpeed API failed: {api_exc}")
        except Exception as exc:
            # Handle any other errors from PageSpeed assessment
            logger.error(f"PageSpeed assessment error for lead {lead_id}: {exc}")
            raise AssessmentError(f"PageSpeed assessment failed: {exc}")
        
        # Store results in database
        asyncio.run(update_assessment_field(
            lead_id,
            'pagespeed_data',
            pagespeed_results,
            'pagespeed_score',
            performance_score
        ))
        
        task_result = {
            "lead_id": lead_id,
            "task": "pagespeed",
            "status": "completed",
            "score": performance_score,
            "url_analyzed": url,
            "company": company,
            "duration_ms": pagespeed_results["analysis_duration_ms"],
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "worker_id": self.request.hostname
        }
        
        logger.info(f"PageSpeed assessment completed for lead {lead_id}: score {performance_score}")
        return task_result
        
    except Exception as exc:
        error_msg = f"PageSpeed assessment failed for lead {lead_id}: {exc}"
        logger.error(error_msg)
        
        # Store error in database
        try:
            asyncio.run(update_assessment_field(
                lead_id,
                'pagespeed_data',
                {"error": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()},
                'pagespeed_score',
                0
            ))
        except Exception as db_exc:
            logger.error(f"Failed to store PageSpeed error: {db_exc}")
        
        # Retry with exponential backoff
        if self.request.retries < 3:
            retry_countdown = 2 ** self.request.retries
            logger.warning(f"Retrying PageSpeed assessment for lead {lead_id} in {retry_countdown}s")
            raise self.retry(countdown=retry_countdown, exc=exc)
        else:
            logger.error(f"Max retries reached for PageSpeed assessment of lead {lead_id}")
            return {
                "lead_id": lead_id,
                "task": "pagespeed",
                "status": "failed",
                "error": str(exc),
                "retries": self.request.retries
            }

@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, AssessmentError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={'max_retries': 3},
    soft_time_limit=90,
    time_limit=120
)
def security_task(self, lead_id: int) -> Dict[str, Any]:
    """
    Execute technical security analysis with Playwright scraper.
    
    Args:
        lead_id: Database ID of the lead to assess
        
    Returns:
        Dict containing technical security assessment results
    """
    task_start = datetime.now(timezone.utc)
    
    try:
        logger.info(f"Starting technical security assessment for lead {lead_id}")
        
        # Get lead information
        async def get_lead_url():
            async with get_db() as db:
                result = await db.execute(select(Lead).where(Lead.id == lead_id))
                lead = result.scalar_one_or_none()
                if not lead:
                    raise AssessmentError(f"Lead {lead_id} not found")
                if not lead.url:
                    raise AssessmentError(f"Lead {lead_id} has no URL for security analysis")
                return lead.url, lead.company
        
        url, company = asyncio.run(get_lead_url())
        
        # PRP-004: Use actual Technical/Security Scraper
        from src.assessments.technical_scraper import assess_technical_security, TechnicalScraperError
        
        try:
            # Execute technical security assessment with Playwright
            technical_results = asyncio.run(assess_technical_security(url, company, lead_id))
            
            # Calculate security score based on security headers and HTTPS enforcement
            security_headers = technical_results.security_headers
            https_enforcement = technical_results.https_enforcement
            seo_signals = technical_results.seo_signals
            js_errors = technical_results.javascript_errors
            
            # Score calculation based on security factors
            headers_score = 0
            security_header_weights = {
                'hsts': 20,
                'csp': 25, 
                'x_frame_options': 15,
                'x_content_type_options': 10,
                'referrer_policy': 15,
                'permissions_policy': 15
            }
            
            for header, weight in security_header_weights.items():
                if getattr(security_headers, header) is not None:
                    headers_score += weight
            
            # HTTPS enforcement score (up to 30 points)
            https_score = 0
            if https_enforcement.enforced:
                https_score += 15
            if https_enforcement.certificate_valid:
                https_score += 10
            if https_enforcement.tls_version_secure:
                https_score += 5
            
            # SEO signals bonus (up to 10 points)
            seo_score = 0
            if seo_signals.robots_txt.get('present', False):
                seo_score += 5
            if seo_signals.sitemap_xml.get('present', False):
                seo_score += 5
            
            # JavaScript error penalty (subtract up to 10 points)
            js_penalty = min(10, js_errors.error_count * 2)
            
            final_security_score = max(0, min(100, headers_score + https_score + seo_score - js_penalty))
            
            # Store cost records in database
            if technical_results.cost_records:
                async def store_cost_records():
                    async with get_db() as db:
                        for cost_record in technical_results.cost_records:
                            db.add(cost_record)
                        await db.commit()
                
                asyncio.run(store_cost_records())
            
        except TechnicalScraperError as scraper_exc:
            # Log specific technical scraper errors
            logger.error(f"Technical scraper error for lead {lead_id}: {scraper_exc}")
            raise AssessmentError(f"Technical scraper failed: {scraper_exc}")
        except Exception as exc:
            # Handle any other errors from technical assessment
            logger.error(f"Technical assessment error for lead {lead_id}: {exc}")
            raise AssessmentError(f"Technical assessment failed: {exc}")
        
        # Convert technical results to dict for database storage
        technical_data = {
            "url": url,
            "scan_timestamp": technical_results.analysis_timestamp,
            "security_headers": {
                "hsts": security_headers.hsts,
                "csp": security_headers.csp,
                "x_frame_options": security_headers.x_frame_options,
                "x_content_type_options": security_headers.x_content_type_options,
                "referrer_policy": security_headers.referrer_policy,
                "permissions_policy": security_headers.permissions_policy
            },
            "https_enforcement": {
                "scheme": https_enforcement.scheme,
                "enforced": https_enforcement.enforced,
                "tls_version": https_enforcement.tls_version,
                "tls_version_secure": https_enforcement.tls_version_secure,
                "certificate_valid": https_enforcement.certificate_valid,
                "hsts_enabled": https_enforcement.hsts_enabled,
                "hsts_max_age": https_enforcement.hsts_max_age
            },
            "seo_signals": {
                "robots_txt": seo_signals.robots_txt,
                "sitemap_xml": seo_signals.sitemap_xml
            },
            "javascript_errors": {
                "error_count": js_errors.error_count,
                "warning_count": js_errors.warning_count,
                "details": js_errors.details[:5]  # Limit stored details
            },
            "performance_metrics": technical_results.performance_metrics,
            "analysis_duration_ms": technical_results.performance_metrics.get('load_time_ms', 0)
        }
        
        # Store results in database
        asyncio.run(update_assessment_field(
            lead_id,
            'security_headers',
            technical_data,
            'security_score',
            final_security_score
        ))
        
        task_result = {
            "lead_id": lead_id,
            "task": "security",
            "status": "completed",
            "score": final_security_score,
            "headers_found": sum(1 for h in technical_data["security_headers"].values() if h is not None),
            "https_enforced": https_enforcement.enforced,
            "tls_secure": https_enforcement.tls_version_secure,
            "js_errors": js_errors.error_count,
            "duration_ms": technical_data["analysis_duration_ms"],
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "worker_id": self.request.hostname
        }
        
        logger.info(f"Technical security assessment completed for lead {lead_id}: score {final_security_score}")
        return task_result
        
    except Exception as exc:
        error_msg = f"Technical security assessment failed for lead {lead_id}: {exc}"
        logger.error(error_msg)
        
        # Store error in database
        try:
            asyncio.run(update_assessment_field(
                lead_id,
                'security_headers',
                {"error": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()},
                'security_score',
                0
            ))
        except Exception as db_exc:
            logger.error(f"Failed to store security error: {db_exc}")
        
        # Retry with exponential backoff
        if self.request.retries < 3:
            retry_countdown = 2 ** self.request.retries
            logger.warning(f"Retrying technical security assessment for lead {lead_id} in {retry_countdown}s")
            raise self.retry(countdown=retry_countdown, exc=exc)
        else:
            logger.error(f"Max retries reached for technical security assessment of lead {lead_id}")
            return {
                "lead_id": lead_id,
                "task": "security",
                "status": "failed",
                "error": str(exc),
                "retries": self.request.retries
            }

@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, AssessmentError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={'max_retries': 3},
    soft_time_limit=90,
    time_limit=120
)
def gbp_task(self, lead_id: int) -> Dict[str, Any]:
    """
    Execute Google Business Profile data collection using PRP-005 integration.
    
    Args:
        lead_id: Database ID of the lead to assess
        
    Returns:
        Dict containing GBP assessment results
    """
    task_start = datetime.now(timezone.utc)
    
    try:
        logger.info(f"Starting GBP assessment for lead {lead_id}")
        
        # Get lead information
        async def get_lead_info():
            async with get_db() as db:
                result = await db.execute(select(Lead).where(Lead.id == lead_id))
                lead = result.scalar_one_or_none()
                if not lead:
                    raise AssessmentError(f"Lead {lead_id} not found")
                return lead.company, lead.address, lead.city, lead.state
        
        company, address, city, state = asyncio.run(get_lead_info())
        
        if not company:
            raise AssessmentError(f"Lead {lead_id} has no company name for GBP search")
        
        # PRP-005: Use actual Google Business Profile integration
        from src.assessments.gbp_integration import assess_google_business_profile, GBPIntegrationError
        
        try:
            # Execute GBP assessment with fuzzy matching and cost tracking
            gbp_results = asyncio.run(assess_google_business_profile(
                business_name=company,
                address=address,
                city=city,
                state=state,
                lead_id=lead_id
            ))
            
            # Extract GBP data and calculate mobile score based on profile completeness
            gbp_data = gbp_results.get("gbp_data", {})
            match_confidence = gbp_results.get("match_confidence", 0.0)
            
            # Calculate mobile score based on GBP profile completeness
            mobile_score = 0
            
            if gbp_results.get("match_found", False) and match_confidence >= 0.5:
                # Score based on data completeness
                completeness_factors = {
                    'hours': 25 if gbp_data.get('hours', {}).get('regular_hours') else 0,
                    'reviews': min(25, gbp_data.get('reviews', {}).get('total_reviews', 0) * 2.5),  # Max 25 points for 10+ reviews
                    'photos': min(20, gbp_data.get('photos', {}).get('total_photos', 0) * 2),      # Max 20 points for 10+ photos
                    'verified': 15 if gbp_data.get('status', {}).get('verified', False) else 0,
                    'address': 10 if gbp_data.get('formatted_address') else 0,
                    'phone': 5 if gbp_data.get('phone_number') else 0
                }
                
                mobile_score = sum(completeness_factors.values())
                
                # Apply confidence penalty for low-confidence matches
                if match_confidence < 0.8:
                    mobile_score = int(mobile_score * match_confidence)
            else:
                # No listing found or low confidence match
                mobile_score = 10  # Minimal score for having some business presence
            
            # Store cost records in database
            if gbp_results.get("cost_records"):
                async def store_cost_records():
                    async with get_db() as db:
                        for cost_record in gbp_results["cost_records"]:
                            db.add(cost_record)
                        await db.commit()
                
                asyncio.run(store_cost_records())
            
        except GBPIntegrationError as gbp_exc:
            # Log specific GBP integration errors
            logger.error(f"GBP integration error for lead {lead_id}: {gbp_exc}")
            raise AssessmentError(f"GBP integration failed: {gbp_exc}")
        except Exception as exc:
            # Handle any other errors from GBP assessment
            logger.error(f"GBP assessment error for lead {lead_id}: {exc}")
            raise AssessmentError(f"GBP assessment failed: {exc}")
        
        # Store results in database
        asyncio.run(update_assessment_field(
            lead_id,
            'gbp_data',
            gbp_results,
            'mobile_score',
            mobile_score
        ))
        
        task_result = {
            "lead_id": lead_id,
            "task": "gbp",
            "status": "completed",
            "score": mobile_score,
            "match_found": gbp_results.get("match_found", False),
            "match_confidence": match_confidence,
            "search_results_count": gbp_results.get("search_results_count", 0),
            "business_verified": gbp_data.get('status', {}).get('verified', False),
            "review_count": gbp_data.get('reviews', {}).get('total_reviews', 0),
            "avg_rating": gbp_data.get('reviews', {}).get('average_rating', 0.0),
            "photos_count": gbp_data.get('photos', {}).get('total_photos', 0),
            "duration_ms": gbp_results.get("analysis_duration_ms", 0),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "worker_id": self.request.hostname
        }
        
        logger.info(f"GBP assessment completed for lead {lead_id}: score {mobile_score}, confidence {match_confidence:.2f}")
        return task_result
        
    except Exception as exc:
        error_msg = f"GBP assessment failed for lead {lead_id}: {exc}"
        logger.error(error_msg)
        
        # Store error in database
        try:
            asyncio.run(update_assessment_field(
                lead_id,
                'gbp_data',
                {"error": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()},
                'mobile_score',
                0
            ))
        except Exception as db_exc:
            logger.error(f"Failed to store GBP error: {db_exc}")
        
        # Retry with exponential backoff
        if self.request.retries < 3:
            retry_countdown = 2 ** self.request.retries
            logger.warning(f"Retrying GBP assessment for lead {lead_id} in {retry_countdown}s")
            raise self.retry(countdown=retry_countdown, exc=exc)
        else:
            return {
                "lead_id": lead_id,
                "task": "gbp",
                "status": "failed",
                "error": str(exc),
                "retries": self.request.retries
            }

@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, AssessmentError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={'max_retries': 3},
    soft_time_limit=120,  # Screenshots may take longer
    time_limit=150
)
def screenshot_task(self, lead_id: int) -> Dict[str, Any]:
    """
    Execute website screenshot capture using PRP-006 integration.
    
    Args:
        lead_id: Database ID of the lead to assess
        
    Returns:
        Dict containing screenshot capture results
    """
    task_start = datetime.now(timezone.utc)
    
    try:
        logger.info(f"Starting screenshot capture for lead {lead_id}")
        
        # Get lead information
        async def get_lead_url():
            async with get_db() as db:
                result = await db.execute(select(Lead).where(Lead.id == lead_id))
                lead = result.scalar_one_or_none()
                if not lead:
                    raise AssessmentError(f"Lead {lead_id} not found")
                if not lead.url:
                    raise AssessmentError(f"Lead {lead_id} has no URL for screenshot capture")
                return lead.url, lead.company
        
        url, company = asyncio.run(get_lead_url())
        
        # PRP-006: Use actual ScreenshotOne integration
        from src.assessments.screenshot_capture import capture_website_screenshots, ScreenshotCaptureError
        
        try:
            # Execute screenshot capture with desktop and mobile viewports
            screenshot_results = asyncio.run(capture_website_screenshots(url, lead_id))
            
            # Calculate visual score based on screenshot success and quality
            visual_score = 0
            
            if screenshot_results.success:
                # Base score for successful capture
                base_score = 50
                
                # Bonus for both viewports captured
                if screenshot_results.desktop_screenshot and screenshot_results.mobile_screenshot:
                    base_score += 30
                elif screenshot_results.desktop_screenshot or screenshot_results.mobile_screenshot:
                    base_score += 15
                
                # Quality bonuses
                if screenshot_results.desktop_screenshot:
                    if screenshot_results.desktop_screenshot.file_size_bytes < 400000:  # <400KB
                        base_score += 10
                    if screenshot_results.desktop_screenshot.capture_duration_ms < 20000:  # <20s
                        base_score += 10
                
                if screenshot_results.mobile_screenshot:
                    if screenshot_results.mobile_screenshot.file_size_bytes < 300000:  # <300KB
                        base_score += 10
                    if screenshot_results.mobile_screenshot.capture_duration_ms < 20000:  # <20s
                        base_score += 10
                
                visual_score = min(100, base_score)
            else:
                # Minimal score for failed capture
                visual_score = 5
            
            # Store cost records in database
            if screenshot_results.cost_records:
                async def store_cost_records():
                    async with get_db() as db:
                        for cost_record in screenshot_results.cost_records:
                            db.add(cost_record)
                        await db.commit()
                
                asyncio.run(store_cost_records())
            
        except ScreenshotCaptureError as screenshot_exc:
            # Log specific screenshot capture errors
            logger.error(f"Screenshot capture error for lead {lead_id}: {screenshot_exc}")
            raise AssessmentError(f"Screenshot capture failed: {screenshot_exc}")
        except Exception as exc:
            # Handle any other errors from screenshot capture
            logger.error(f"Screenshot capture error for lead {lead_id}: {exc}")
            raise AssessmentError(f"Screenshot capture failed: {exc}")
        
        # Convert screenshot results to dict for database storage
        screenshot_data = {
            "url": url,
            "capture_timestamp": task_start.isoformat(),
            "success": screenshot_results.success,
            "total_duration_ms": screenshot_results.total_duration_ms,
            "desktop_screenshot": screenshot_results.desktop_screenshot.dict() if screenshot_results.desktop_screenshot else None,
            "mobile_screenshot": screenshot_results.mobile_screenshot.dict() if screenshot_results.mobile_screenshot else None,
            "error_message": screenshot_results.error_message
        }
        
        # Store results in database
        asyncio.run(update_assessment_field(
            lead_id,
            'visual_analysis',
            screenshot_data
            # Note: visual analysis doesn't map to a specific score field in our current schema
            # The overall score will be calculated in aggregate_results
        ))
        
        task_result = {
            "lead_id": lead_id,
            "task": "screenshot",
            "status": "completed",
            "score": visual_score,
            "desktop_captured": screenshot_results.desktop_screenshot is not None,
            "mobile_captured": screenshot_results.mobile_screenshot is not None,
            "total_file_size": (
                (screenshot_results.desktop_screenshot.file_size_bytes if screenshot_results.desktop_screenshot else 0) +
                (screenshot_results.mobile_screenshot.file_size_bytes if screenshot_results.mobile_screenshot else 0)
            ),
            "duration_ms": screenshot_results.total_duration_ms,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "worker_id": self.request.hostname
        }
        
        logger.info(f"Screenshot capture completed for lead {lead_id}: score {visual_score}, desktop={'✅' if screenshot_results.desktop_screenshot else '❌'}, mobile={'✅' if screenshot_results.mobile_screenshot else '❌'}")
        return task_result
        
    except Exception as exc:
        error_msg = f"Screenshot capture failed for lead {lead_id}: {exc}"
        logger.error(error_msg)
        
        # Store error in database
        try:
            asyncio.run(update_assessment_field(
                lead_id,
                'visual_analysis',
                {"error": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()}
            ))
        except Exception as db_exc:
            logger.error(f"Failed to store screenshot error: {db_exc}")
        
        # Retry with exponential backoff
        if self.request.retries < 3:
            retry_countdown = 2 ** self.request.retries
            logger.warning(f"Retrying screenshot capture for lead {lead_id} in {retry_countdown}s")
            raise self.retry(countdown=retry_countdown, exc=exc)
        else:
            return {
                "lead_id": lead_id,
                "task": "screenshot",
                "status": "failed",
                "error": str(exc),
                "retries": self.request.retries
            }

@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, AssessmentError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={'max_retries': 3},
    soft_time_limit=120,  # SEMrush may take longer
    time_limit=150
)
def semrush_task(self, lead_id: int) -> Dict[str, Any]:
    """
    Execute SEMrush SEO analysis using PRP-007 integration.
    
    Args:
        lead_id: Database ID of the lead to assess
        
    Returns:
        Dict containing SEMrush assessment results
    """
    task_start = datetime.now(timezone.utc)
    
    try:
        logger.info(f"Starting SEMrush assessment for lead {lead_id}")
        
        # Get lead information
        async def get_lead_info():
            async with get_db() as db:
                result = await db.execute(select(Lead).where(Lead.id == lead_id))
                lead = result.scalar_one_or_none()
                if not lead:
                    raise AssessmentError(f"Lead {lead_id} not found")
                if not lead.url:
                    raise AssessmentError(f"Lead {lead_id} has no URL for SEMrush analysis")
                return lead.url, lead.company
        
        url, company = asyncio.run(get_lead_info())
        
        # Extract domain from URL
        domain = url.replace('https://', '').replace('http://', '').split('/')[0]
        
        # PRP-007: Use actual SEMrush integration
        from src.assessments.semrush_integration import assess_semrush_domain, SEMrushIntegrationError
        
        try:
            # Execute SEMrush domain analysis
            semrush_results = asyncio.run(assess_semrush_domain(domain, lead_id))
            
            # Calculate SEO score based on SEMrush metrics
            seo_score = 0
            
            if semrush_results.success and semrush_results.metrics:
                metrics = semrush_results.metrics
                
                # Authority Score component (40%)
                authority_component = (metrics.authority_score / 100) * 40
                
                # Traffic component (30%) - normalized to reasonable scale
                traffic_normalized = min(metrics.organic_traffic_estimate / 10000, 1.0)  # Cap at 10K traffic
                traffic_component = traffic_normalized * 30
                
                # Keywords component (20%) - normalized to reasonable scale  
                keywords_normalized = min(metrics.ranking_keywords_count / 1000, 1.0)  # Cap at 1K keywords
                keywords_component = keywords_normalized * 20
                
                # Site health component (10%)
                health_component = (metrics.site_health_score / 100) * 10
                
                seo_score = int(authority_component + traffic_component + keywords_component + health_component)
                
                # Penalty for high toxicity
                if metrics.backlink_toxicity_score > 20:
                    seo_score = max(0, seo_score - int(metrics.backlink_toxicity_score / 5))
            else:
                # Minimal score for analysis failure
                seo_score = 5
            
            # Store cost records in database
            if semrush_results.cost_records:
                async def store_cost_records():
                    async with get_db() as db:
                        for cost_record in semrush_results.cost_records:
                            db.add(cost_record)
                        await db.commit()
                
                asyncio.run(store_cost_records())
            
        except SEMrushIntegrationError as semrush_exc:
            # Log specific SEMrush integration errors
            logger.error(f"SEMrush integration error for lead {lead_id}: {semrush_exc}")
            raise AssessmentError(f"SEMrush integration failed: {semrush_exc}")
        except Exception as exc:
            # Handle any other errors from SEMrush assessment
            logger.error(f"SEMrush assessment error for lead {lead_id}: {exc}")
            raise AssessmentError(f"SEMrush assessment failed: {exc}")
        
        # Convert SEMrush results to dict for database storage
        semrush_data = {
            "domain": domain,
            "analysis_timestamp": task_start.isoformat(),
            "success": semrush_results.success,
            "total_duration_ms": semrush_results.total_duration_ms,
            "error_message": semrush_results.error_message
        }
        
        if semrush_results.metrics:
            metrics = semrush_results.metrics
            semrush_data.update({
                "authority_score": metrics.authority_score,
                "backlink_toxicity_score": metrics.backlink_toxicity_score,
                "organic_traffic_estimate": metrics.organic_traffic_estimate,
                "ranking_keywords_count": metrics.ranking_keywords_count,
                "site_health_score": metrics.site_health_score,
                "technical_issues": [issue.dict() for issue in metrics.technical_issues],
                "api_cost_units": metrics.api_cost_units
            })
        
        # Store results in database
        asyncio.run(update_assessment_field(
            lead_id,
            'semrush_data',
            semrush_data,
            'seo_score',
            seo_score
        ))
        
        task_result = {
            "lead_id": lead_id,
            "task": "semrush",
            "status": "completed",
            "score": seo_score,
            "domain": domain,
            "authority_score": semrush_results.metrics.authority_score if semrush_results.metrics else 0,
            "organic_traffic": semrush_results.metrics.organic_traffic_estimate if semrush_results.metrics else 0,
            "ranking_keywords": semrush_results.metrics.ranking_keywords_count if semrush_results.metrics else 0,
            "toxicity_score": semrush_results.metrics.backlink_toxicity_score if semrush_results.metrics else 0.0,
            "technical_issues": len(semrush_results.metrics.technical_issues) if semrush_results.metrics else 0,
            "duration_ms": semrush_results.total_duration_ms,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "worker_id": self.request.hostname
        }
        
        logger.info(f"SEMrush assessment completed for lead {lead_id}: score {seo_score}, authority {task_result['authority_score']}")
        return task_result
        
    except Exception as exc:
        error_msg = f"SEMrush assessment failed for lead {lead_id}: {exc}"
        logger.error(error_msg)
        
        # Store error in database
        try:
            asyncio.run(update_assessment_field(
                lead_id,
                'semrush_data',
                {"error": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()},
                'seo_score',
                0
            ))
        except Exception as db_exc:
            logger.error(f"Failed to store SEMrush error: {db_exc}")
        
        # Retry with exponential backoff
        if self.request.retries < 3:
            retry_countdown = 2 ** self.request.retries
            logger.warning(f"Retrying SEMrush assessment for lead {lead_id} in {retry_countdown}s")
            raise self.retry(countdown=retry_countdown, exc=exc)
        else:
            return {
                "lead_id": lead_id,
                "task": "semrush",
                "status": "failed",
                "error": str(exc),
                "retries": self.request.retries
            }

@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, AssessmentError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={'max_retries': 3},
    soft_time_limit=120,  # 2 minutes for visual analysis
    time_limit=150
)
def visual_task(self, lead_id: int) -> Dict[str, Any]:
    """
    Execute GPT-4 Vision UX analysis with screenshot processing.
    
    Args:
        lead_id: Database ID of the lead to assess
        
    Returns:
        Dict containing visual UX assessment results
    """
    task_start = datetime.now(timezone.utc)
    
    try:
        logger.info(f"Starting visual assessment for lead {lead_id}")
        
        # Get lead information and screenshot URLs
        async def get_lead_data():
            async with get_db() as db:
                result = await db.execute(select(Lead).where(Lead.id == lead_id))
                lead = result.scalar_one_or_none()
                if not lead:
                    raise AssessmentError(f"Lead {lead_id} not found")
                if not lead.url:
                    raise AssessmentError(f"Lead {lead_id} has no URL for visual analysis")
                
                # Get screenshot assessment for screenshot URLs
                assessment_result = await db.execute(select(Assessment).where(Assessment.lead_id == lead_id))
                assessment = assessment_result.scalar_one_or_none()
                
                # Extract screenshot URLs from visual_analysis field (PRP-006 data)
                desktop_screenshot_url = None
                mobile_screenshot_url = None
                
                if assessment and assessment.visual_analysis:
                    visual_data = assessment.visual_analysis
                    if isinstance(visual_data, dict):
                        desktop_data = visual_data.get("desktop_screenshot", {})
                        mobile_data = visual_data.get("mobile_screenshot", {})
                        
                        # Build screenshot URLs (would be actual S3/CDN URLs in production)
                        if desktop_data.get("s3_url"):
                            desktop_screenshot_url = desktop_data["s3_url"]
                        if mobile_data.get("s3_url"):
                            mobile_screenshot_url = mobile_data["s3_url"]
                
                if not desktop_screenshot_url or not mobile_screenshot_url:
                    raise AssessmentError(f"Screenshots not available for lead {lead_id}. Run screenshot_task first.")
                
                return lead.url, lead.company, desktop_screenshot_url, mobile_screenshot_url
        
        url, company, desktop_url, mobile_url = asyncio.run(get_lead_data())
        
        # PRP-008: Use actual Visual Analysis integration
        from src.assessments.visual_analysis import assess_visual_analysis, VisualAnalysisError
        
        try:
            # Execute visual analysis with GPT-4 Vision
            visual_results = asyncio.run(assess_visual_analysis(url, desktop_url, mobile_url, lead_id))
            
            # Calculate visual UX score based on rubric evaluations
            visual_score = 0
            if visual_results.success and visual_results.metrics:
                metrics = visual_results.metrics
                
                # Convert 0-2 scale to 0-100 for consistency with other assessments
                visual_score = int((metrics.overall_ux_score / 2.0) * 100)
                
                # Prepare structured data for database storage
                visual_data = {
                    "url": url,
                    "analysis_timestamp": metrics.analysis_timestamp,
                    "success": True,
                    "overall_ux_score": metrics.overall_ux_score,
                    "visual_score_0_100": visual_score,
                    "rubric_scores": {
                        rubric.name: {
                            "score": rubric.score,
                            "explanation": rubric.explanation,
                            "recommendations": rubric.recommendations
                        }
                        for rubric in metrics.rubrics
                    },
                    "desktop_analysis": metrics.desktop_analysis,
                    "mobile_analysis": metrics.mobile_analysis,
                    "critical_issues": metrics.critical_issues,
                    "positive_elements": metrics.positive_elements,
                    "api_cost_dollars": metrics.api_cost_dollars,
                    "processing_time_ms": metrics.processing_time_ms
                }
            else:
                # Handle failed analysis
                visual_data = {
                    "url": url,
                    "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                    "success": False,
                    "error_message": visual_results.error_message,
                    "overall_ux_score": 0.0,
                    "visual_score_0_100": 0
                }
            
            # Update assessment record with visual analysis results
            asyncio.run(update_assessment_field(
                lead_id,
                'visual_analysis',
                visual_data,
                'visual_score',
                visual_score
            ))
            
            # Store cost records in database
            if visual_results.cost_records:
                async def store_cost_records():
                    async with get_db() as db:
                        for cost_record in visual_results.cost_records:
                            db.add(cost_record)
                        await db.commit()
                
                asyncio.run(store_cost_records())
                
        except VisualAnalysisError as api_exc:
            # Log specific Visual Analysis API errors
            logger.error(f"Visual Analysis API error for lead {lead_id}: {api_exc}")
            raise AssessmentError(f"Visual Analysis API failed: {api_exc}")
        except Exception as exc:
            # Handle any other errors from visual analysis
            logger.error(f"Visual analysis error for lead {lead_id}: {exc}")
            raise AssessmentError(f"Visual analysis failed: {exc}")
        
        # Mark task as completed
        task_duration = (datetime.now(timezone.utc) - task_start).total_seconds()
        
        # Update assessment status to completed
        asyncio.run(update_assessment_status(lead_id, ASSESSMENT_STATUS.VISUAL_COMPLETED))
        
        # Prepare task result
        task_result = {
            "lead_id": lead_id,
            "task": "visual",
            "status": "completed",
            "url": url,
            "visual_score": visual_score,
            "ux_score_0_2": visual_results.metrics.overall_ux_score if visual_results.metrics else 0.0,
            "rubrics_evaluated": len(visual_results.metrics.rubrics) if visual_results.metrics else 0,
            "critical_issues": len(visual_results.metrics.critical_issues) if visual_results.metrics else 0,
            "positive_elements": len(visual_results.metrics.positive_elements) if visual_results.metrics else 0,
            "api_cost": visual_results.metrics.api_cost_dollars if visual_results.metrics else 0.0,
            "duration_ms": visual_results.total_duration_ms,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "worker_id": self.request.hostname
        }
        
        logger.info(f"Visual assessment completed for lead {lead_id}: score {visual_score}, UX {task_result['ux_score_0_2']:.2f}")
        return task_result
        
    except Exception as exc:
        error_msg = f"Visual assessment failed for lead {lead_id}: {exc}"
        logger.error(error_msg)
        
        # Store error in database
        try:
            asyncio.run(update_assessment_field(
                lead_id,
                'visual_analysis',
                {"error": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()},
                'visual_score',
                0
            ))
        except Exception as db_exc:
            logger.error(f"Failed to store visual analysis error: {db_exc}")
        
        # Retry with exponential backoff
        if self.request.retries < 3:
            retry_countdown = 2 ** self.request.retries
            logger.warning(f"Retrying visual assessment for lead {lead_id} in {retry_countdown}s")
            raise self.retry(countdown=retry_countdown, exc=exc)
        else:
            return {
                "lead_id": lead_id,
                "task": "visual",
                "status": "failed",
                "error": str(exc),
                "retries": self.request.retries
            }

@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, AssessmentError),
    retry_backoff=True,  
    retry_jitter=True,
    retry_kwargs={'max_retries': 3},
    soft_time_limit=180,  # LLM tasks may take longer
    time_limit=240
)
def llm_analysis_task(self, lead_id: int, assessment_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Execute LLM-powered analysis based on completed assessments.
    
    Args:
        lead_id: Database ID of the lead to assess
        assessment_results: Results from other assessment tasks
        
    Returns:
        Dict containing LLM analysis results
    """
    task_start = datetime.now(timezone.utc)
    
    try:
        logger.info(f"Starting LLM analysis for lead {lead_id}")
        
        # TODO: Implement actual LLM analysis (will be in PRP-008 and PRP-010)
        # For now, simulate LLM analysis with placeholder insights
        import time
        import random
        
        time.sleep(random.uniform(8, 20))  # LLM analysis takes longer
        
        # Analyze completed assessment results to generate insights
        successful_assessments = [r for r in assessment_results if r.get('status') == 'completed']
        average_score = sum(r.get('score', 0) for r in successful_assessments) / len(successful_assessments) if successful_assessments else 0
        
        # Placeholder LLM insights
        llm_insights = {
            "overall_assessment": f"Based on analysis of {len(successful_assessments)} assessment areas",
            "strengths": [
                "Strong SSL certificate implementation",
                "Good organic search presence", 
                "Professional website design"
            ][:random.randint(1, 3)],
            "weaknesses": [
                "Missing security headers",
                "Slow page load times",
                "Limited mobile optimization",
                "Poor Google Business Profile completion"
            ][:random.randint(1, 4)],
            "recommendations": [
                "Implement Content Security Policy header",
                "Optimize images and enable compression",
                "Complete Google Business Profile information",
                "Add customer reviews and testimonials",
                "Improve mobile responsiveness"
            ][:random.randint(3, 5)],
            "priority_actions": [
                {"action": "Fix security headers", "impact": "High", "effort": "Low"},
                {"action": "Optimize page speed", "impact": "High", "effort": "Medium"},
                {"action": "Update mobile design", "impact": "Medium", "effort": "High"}
            ][:random.randint(2, 4)],
            "risk_assessment": random.choice(["Low", "Medium", "High"]),
            "improvement_potential": f"{random.randint(15, 35)}% score improvement possible",
            "competitive_position": random.choice(["Above Average", "Average", "Below Average"]),
            "analysis_timestamp": task_start.isoformat(),
            "input_assessments": [r.get('task', 'unknown') for r in assessment_results],
            "analysis_duration_ms": int((datetime.now(timezone.utc) - task_start).total_seconds() * 1000)
        }
        
        # Store results in database
        asyncio.run(update_assessment_field(
            lead_id,
            'llm_insights',
            llm_insights
        ))
        
        task_result = {
            "lead_id": lead_id,
            "task": "llm_analysis", 
            "status": "completed",
            "insights_generated": len(llm_insights["recommendations"]),
            "risk_level": llm_insights["risk_assessment"],
            "improvement_potential": llm_insights["improvement_potential"],
            "competitive_position": llm_insights["competitive_position"],
            "duration_ms": llm_insights["analysis_duration_ms"],
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "worker_id": self.request.hostname
        }
        
        logger.info(f"LLM analysis completed for lead {lead_id}: {len(llm_insights['recommendations'])} recommendations")
        return task_result
        
    except Exception as exc:
        error_msg = f"LLM analysis failed for lead {lead_id}: {exc}"
        logger.error(error_msg)
        
        # Store error in database
        try:
            asyncio.run(update_assessment_field(
                lead_id,
                'llm_insights',
                {"error": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()}
            ))
        except Exception as db_exc:
            logger.error(f"Failed to store LLM analysis error: {db_exc}")
        
        # Retry with exponential backoff
        if self.request.retries < 3:
            retry_countdown = 2 ** self.request.retries
            logger.warning(f"Retrying LLM analysis for lead {lead_id} in {retry_countdown}s")
            raise self.retry(countdown=retry_countdown, exc=exc)
        else:
            return {
                "lead_id": lead_id,
                "task": "llm_analysis",
                "status": "failed",
                "error": str(exc),
                "retries": self.request.retries
            }

@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, AssessmentError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={'max_retries': 3},
    soft_time_limit=60,  # Score calculation should be fast
    time_limit=90
)
def score_calculation_task(self, lead_id: int) -> Dict[str, Any]:
    """
    Execute business impact score calculation aggregating all assessment results.
    
    Args:
        lead_id: Database ID of the lead to calculate scores for
        
    Returns:
        Dict containing business impact scores and recommendations
    """
    task_start = datetime.now(timezone.utc)
    
    try:
        logger.info(f"Starting score calculation for lead {lead_id}")
        
        # Get lead data and all assessment results
        async def get_assessment_data():
            async with get_db() as db:
                # Get lead information
                lead_result = await db.execute(select(Lead).where(Lead.id == lead_id))
                lead = lead_result.scalar_one_or_none()
                if not lead:
                    raise AssessmentError(f"Lead {lead_id} not found")
                
                # Get assessment results
                assessment_result = await db.execute(select(Assessment).where(Assessment.lead_id == lead_id))
                assessment = assessment_result.scalar_one_or_none()
                if not assessment:
                    raise AssessmentError(f"Assessment data not found for lead {lead_id}")
                
                # Extract lead data
                lead_data = {
                    'company': lead.company,
                    'url': lead.url,
                    'description': getattr(lead, 'description', ''),
                    'naics_code': getattr(lead, 'naics_code', None),
                    'state': getattr(lead, 'state', None),
                    'county': getattr(lead, 'county', None)
                }
                
                # Extract assessment data from all PRPs
                assessment_data = {
                    'pagespeed_data': assessment.pagespeed_data or {},
                    'security_data': assessment.security_data or {},
                    'semrush_data': assessment.semrush_data or {},
                    'visual_analysis': assessment.visual_analysis or {}
                }
                
                return lead_data, assessment_data
        
        lead_data, assessment_data = asyncio.run(get_assessment_data())
        
        # PRP-009: Use actual Score Calculator integration
        from src.assessments.score_calculator import calculate_business_score, ScoreCalculatorError
        
        try:
            # Execute business impact score calculation
            business_score = asyncio.run(calculate_business_score(lead_id, assessment_data, lead_data))
            
            # Extract priority recommendations from all components
            priority_recommendations = []
            for component in [business_score.performance_score, business_score.security_score, 
                            business_score.seo_score, business_score.ux_score, business_score.visual_score]:
                if component.severity in ['P1', 'P2']:  # High priority only
                    priority_recommendations.extend(component.recommendations[:2])  # Top 2 per component
            
            # Prepare structured data for database storage
            score_data = {
                "lead_id": lead_id,
                "calculation_timestamp": business_score.calculation_timestamp,
                "overall_score": business_score.overall_score,
                "performance_grade": "A" if business_score.overall_score >= 90 else "B" if business_score.overall_score >= 80 else "C" if business_score.overall_score >= 70 else "D" if business_score.overall_score >= 60 else "F",
                "total_impact_estimate": business_score.total_impact_estimate,
                "confidence_interval": {
                    "lower": business_score.confidence_interval[0],
                    "upper": business_score.confidence_interval[1]
                },
                "component_scores": {
                    "performance": {
                        "raw_score": business_score.performance_score.raw_score,
                        "impact_estimate": business_score.performance_score.impact_estimate,
                        "severity": business_score.performance_score.severity,
                        "recommendations": business_score.performance_score.recommendations
                    },
                    "security": {
                        "raw_score": business_score.security_score.raw_score,
                        "impact_estimate": business_score.security_score.impact_estimate,
                        "severity": business_score.security_score.severity,
                        "recommendations": business_score.security_score.recommendations
                    },
                    "seo": {
                        "raw_score": business_score.seo_score.raw_score,
                        "impact_estimate": business_score.seo_score.impact_estimate,
                        "severity": business_score.seo_score.severity,
                        "recommendations": business_score.seo_score.recommendations
                    },
                    "ux": {
                        "raw_score": business_score.ux_score.raw_score,
                        "impact_estimate": business_score.ux_score.impact_estimate,
                        "severity": business_score.ux_score.severity,
                        "recommendations": business_score.ux_score.recommendations
                    },
                    "visual": {
                        "raw_score": business_score.visual_score.raw_score,
                        "impact_estimate": business_score.visual_score.impact_estimate,
                        "severity": business_score.visual_score.severity,
                        "recommendations": business_score.visual_score.recommendations
                    }
                },
                "business_factors": {
                    "industry_code": business_score.industry_code,
                    "industry_multiplier": business_score.industry_multiplier,
                    "geographic_factor": business_score.geographic_factor,
                    "market_adjustment": business_score.market_adjustment
                },
                "priority_recommendations": priority_recommendations[:10],  # Top 10 priorities
                "processing_time_ms": business_score.processing_time_ms,
                "validation_status": business_score.validation_status
            }
            
            # Update assessment record with business score
            asyncio.run(update_assessment_field(
                lead_id,
                'business_score',
                score_data,
                'overall_score',
                business_score.overall_score
            ))
            
            # Store cost records (internal calculation - no external API cost)
            cost_record = AssessmentCost.create_scoring_cost(
                lead_id=lead_id,
                cost_cents=0.0,  # No external cost for internal calculation
                response_status="success",
                response_time_ms=business_score.processing_time_ms
            )
            
            async def store_cost_record():
                async with get_db() as db:
                    db.add(cost_record)
                    await db.commit()
            
            asyncio.run(store_cost_record())
                
        except ScoreCalculatorError as api_exc:
            # Log specific Score Calculator errors
            logger.error(f"Score Calculator error for lead {lead_id}: {api_exc}")
            raise AssessmentError(f"Score Calculator failed: {api_exc}")
        except Exception as exc:
            # Handle any other errors from score calculation
            logger.error(f"Score calculation error for lead {lead_id}: {exc}")
            raise AssessmentError(f"Score calculation failed: {exc}")
        
        # Mark task as completed
        task_duration = (datetime.now(timezone.utc) - task_start).total_seconds()
        
        # Update assessment status to scoring completed
        asyncio.run(update_assessment_status(lead_id, ASSESSMENT_STATUS.SCORING_COMPLETED))
        
        # Count critical and high priority issues
        critical_issues = sum(1 for score in [business_score.performance_score, business_score.security_score, 
                                            business_score.seo_score, business_score.ux_score, business_score.visual_score]
                            if score.severity == 'P1')
        high_priority_issues = sum(1 for score in [business_score.performance_score, business_score.security_score,
                                                 business_score.seo_score, business_score.ux_score, business_score.visual_score]
                                 if score.severity == 'P2')
        
        # Prepare task result
        task_result = {
            "lead_id": lead_id,
            "task": "score_calculation",
            "status": "completed",
            "overall_score": business_score.overall_score,
            "performance_grade": score_data["performance_grade"],
            "total_impact_estimate": business_score.total_impact_estimate,
            "confidence_lower": business_score.confidence_interval[0],
            "confidence_upper": business_score.confidence_interval[1],
            "industry_code": business_score.industry_code,
            "market_adjustment": business_score.market_adjustment,
            "critical_issues": critical_issues,
            "high_priority_issues": high_priority_issues,
            "priority_recommendations": len(priority_recommendations),
            "processing_time_ms": business_score.processing_time_ms,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "worker_id": self.request.hostname
        }
        
        logger.info(f"Score calculation completed for lead {lead_id}: {business_score.overall_score:.1f} score, ${business_score.total_impact_estimate:.2f} impact")
        return task_result
        
    except Exception as exc:
        error_msg = f"Score calculation failed for lead {lead_id}: {exc}"
        logger.error(error_msg)
        
        # Store error in database
        try:
            asyncio.run(update_assessment_field(
                lead_id,
                'business_score',
                {"error": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()},
                'overall_score',
                0
            ))
        except Exception as db_exc:
            logger.error(f"Failed to store score calculation error: {db_exc}")
        
        # Retry with exponential backoff
        if self.request.retries < 3:
            retry_countdown = 2 ** self.request.retries
            logger.warning(f"Retrying score calculation for lead {lead_id} in {retry_countdown}s")
            raise self.retry(countdown=retry_countdown, exc=exc)
        else:
            return {
                "lead_id": lead_id,
                "task": "score_calculation",
                "status": "failed",
                "error": str(exc),
                "retries": self.request.retries
            }

@celery_app.task(
    bind=True,
    soft_time_limit=60,
    time_limit=90
)
def aggregate_results(self, assessment_results: List[Dict[str, Any]], lead_id: int) -> Dict[str, Any]:
    """
    Aggregate results from parallel assessment tasks and calculate final scores.
    
    This task is called as the callback from the chord of parallel assessments.
    
    Args:
        assessment_results: List of results from parallel assessment tasks
        lead_id: Database ID of the lead
        
    Returns:
        Dict containing aggregated assessment results
    """
    aggregation_start = datetime.now(timezone.utc)
    
    try:
        logger.info(f"Starting result aggregation for lead {lead_id}")
        
        # Separate successful and failed assessments
        successful_results = [r for r in assessment_results if r.get('status') == 'completed']
        failed_results = [r for r in assessment_results if r.get('status') == 'failed']
        
        logger.info(f"Aggregating {len(successful_results)} successful and {len(failed_results)} failed assessments")
        
        # Calculate total score from available assessment scores
        scores = []
        score_details = {}
        
        for result in successful_results:
            if 'score' in result and result['score'] is not None:
                task_name = result.get('task', 'unknown')
                score = result['score']
                scores.append(score)
                score_details[task_name] = score
        
        # Calculate weighted average (all assessments weighted equally for now)
        total_score = int(sum(scores) / len(scores)) if scores else 0
        
        # Trigger LLM analysis with assessment results
        llm_result = llm_analysis_task.delay(lead_id, assessment_results)
        
        # Determine final status
        if len(failed_results) == 0:
            final_status = ASSESSMENT_STATUS['COMPLETED']
        elif len(successful_results) > 0:
            final_status = ASSESSMENT_STATUS['PARTIAL']
        else:
            final_status = ASSESSMENT_STATUS['FAILED']
        
        # Update assessment record with final results
        total_duration_ms = int((datetime.now(timezone.utc) - aggregation_start).total_seconds() * 1000)
        
        asyncio.run(update_assessment_status(
            lead_id,
            final_status,
            total_score=total_score,
            completed_at=datetime.now(timezone.utc),
            assessment_duration_ms=total_duration_ms
        ))
        
        aggregation_result = {
            "lead_id": lead_id,
            "status": final_status,
            "total_score": total_score,
            "score_breakdown": score_details,
            "successful_assessments": len(successful_results),
            "failed_assessments": len(failed_results),
            "llm_task_id": llm_result.id,
            "aggregation_duration_ms": total_duration_ms,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "assessment_details": {
                "successful": [{"task": r.get('task'), "score": r.get('score'), "duration_ms": r.get('duration_ms')} for r in successful_results],
                "failed": [{"task": r.get('task'), "error": r.get('error')} for r in failed_results]
            }
        }
        
        logger.info(f"Assessment aggregation completed for lead {lead_id}: final score {total_score}, status {final_status}")
        return aggregation_result
        
    except Exception as exc:
        error_msg = f"Result aggregation failed for lead {lead_id}: {exc}"
        logger.error(error_msg)
        
        # Update assessment status to failed
        try:
            asyncio.run(update_assessment_status(
                lead_id,
                ASSESSMENT_STATUS['FAILED'],
                error_message=str(exc),
                completed_at=datetime.now(timezone.utc)
            ))
        except Exception as db_exc:
            logger.error(f"Failed to update assessment status after aggregation failure: {db_exc}")
        
        return {
            "lead_id": lead_id,
            "status": "aggregation_failed",
            "error": str(exc),
            "assessment_results": assessment_results
        }

# Health monitoring tasks
@celery_app.task
def health_check() -> Dict[str, Any]:
    """Periodic health check task"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "worker_id": celery_app.control.inspect().active()
    }

@celery_app.task
def cleanup_expired_results() -> Dict[str, Any]:
    """Clean up expired task results"""
    # TODO: Implement cleanup logic
    return {
        "cleaned_results": 0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@celery_app.task
def monitor_assessment_queues() -> Dict[str, Any]:
    """Monitor assessment queue health"""
    # TODO: Implement queue monitoring
    inspect = celery_app.control.inspect()
    return {
        "active_tasks": len(inspect.active() or {}),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, AssessmentError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={'max_retries': 3},
    soft_time_limit=120,  # Content generation may take time
    time_limit=150
)
def content_generation_task(self, lead_id: int) -> Dict[str, Any]:
    """
    Execute LLM content generation for marketing materials using PRP-010.
    
    Args:
        lead_id: Database ID of the lead to generate content for
        
    Returns:
        Dict containing generated marketing content results
    """
    task_start = datetime.now(timezone.utc)
    
    try:
        logger.info(f"Starting content generation for lead {lead_id}")
        
        # Get lead data and assessment results
        async def get_content_data():
            async with get_db() as db:
                # Get lead information
                lead_result = await db.execute(select(Lead).where(Lead.id == lead_id))
                lead = lead_result.scalar_one_or_none()
                if not lead:
                    raise AssessmentError(f"Lead {lead_id} not found")
                
                # Get assessment results
                assessment_result = await db.execute(select(Assessment).where(Assessment.lead_id == lead_id))
                assessment = assessment_result.scalar_one_or_none()
                if not assessment:
                    raise AssessmentError(f"Assessment data not found for lead {lead_id}")
                
                # Extract business data
                business_data = {
                    'company': lead.company,
                    'url': lead.url,
                    'description': getattr(lead, 'description', ''),
                    'naics_code': getattr(lead, 'naics_code', None),
                    'contact_name': getattr(lead, 'contact_name', None),
                    'state': getattr(lead, 'state', None)
                }
                
                # Extract complete assessment data
                assessment_data = {
                    'pagespeed_data': assessment.pagespeed_data or {},
                    'security_data': assessment.security_data or {},
                    'semrush_data': assessment.semrush_data or {},
                    'visual_analysis': assessment.visual_analysis or {},
                    'business_score': assessment.business_score or {}
                }
                
                return business_data, assessment_data
        
        business_data, assessment_data = asyncio.run(get_content_data())
        
        # PRP-010: Use actual Content Generator integration
        from src.assessments.content_generator import generate_marketing_content, ContentGeneratorError
        
        try:
            # Execute marketing content generation
            marketing_content = asyncio.run(generate_marketing_content(lead_id, business_data, assessment_data))
            
            # Prepare structured data for database storage
            content_data = {
                "lead_id": marketing_content.lead_id,
                "generation_timestamp": marketing_content.generation_timestamp,
                "template_version": marketing_content.template_version,
                
                # Email content
                "subject_line": marketing_content.subject_line,
                "email_body": marketing_content.email_body,
                
                # Report content
                "executive_summary": marketing_content.executive_summary,
                "issue_insights": marketing_content.issue_insights,
                "recommended_actions": marketing_content.recommended_actions,
                "urgency_indicators": marketing_content.urgency_indicators,
                
                # Quality metrics
                "spam_score": marketing_content.spam_score,
                "brand_voice_score": marketing_content.brand_voice_score,
                "content_quality_score": marketing_content.content_quality_score,
                "api_cost_dollars": marketing_content.api_cost_dollars,
                "processing_time_ms": marketing_content.processing_time_ms
            }
            
            # Update assessment record with marketing content
            asyncio.run(update_assessment_field(
                lead_id,
                'marketing_content',
                content_data
            ))
            
            # Store cost records (OpenAI API cost)
            cost_record = AssessmentCost.create_content_cost(
                lead_id=lead_id,
                cost_cents=marketing_content.api_cost_dollars * 100,  # Convert dollars to cents
                response_status="success",
                response_time_ms=marketing_content.processing_time_ms
            )
            
            async def store_cost_record():
                async with get_db() as db:
                    db.add(cost_record)
                    await db.commit()
            
            asyncio.run(store_cost_record())
                
        except ContentGeneratorError as api_exc:
            # Log specific Content Generator errors
            logger.error(f"Content Generator error for lead {lead_id}: {api_exc}")
            raise AssessmentError(f"Content Generator failed: {api_exc}")
        except Exception as exc:
            # Handle any other errors from content generation
            logger.error(f"Content generation error for lead {lead_id}: {exc}")
            raise AssessmentError(f"Content generation failed: {exc}")
        
        # Mark task as completed
        task_duration = (datetime.now(timezone.utc) - task_start).total_seconds()
        
        # Update assessment status to content generation completed
        asyncio.run(update_assessment_status(lead_id, ASSESSMENT_STATUS.CONTENT_COMPLETED))
        
        # Prepare task result
        task_result = {
            "lead_id": lead_id,
            "task": "content_generation",
            "status": "completed",
            "subject_line_length": len(marketing_content.subject_line),
            "email_body_words": len(marketing_content.email_body.split()),
            "insights_count": len(marketing_content.issue_insights),
            "actions_count": len(marketing_content.recommended_actions),
            "urgency_indicators": len(marketing_content.urgency_indicators),
            "spam_score": marketing_content.spam_score,
            "brand_voice_score": marketing_content.brand_voice_score,
            "content_quality_score": marketing_content.content_quality_score,
            "api_cost_dollars": marketing_content.api_cost_dollars,
            "processing_time_ms": marketing_content.processing_time_ms,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "worker_id": self.request.hostname
        }
        
        logger.info(f"Content generation completed for lead {lead_id}: quality {marketing_content.content_quality_score:.1f}, cost ${marketing_content.api_cost_dollars:.4f}")
        return task_result
        
    except Exception as exc:
        error_msg = f"Content generation failed for lead {lead_id}: {exc}"
        logger.error(error_msg)
        
        # Store error in database
        try:
            asyncio.run(update_assessment_field(
                lead_id,
                'marketing_content',
                {"error": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()}
            ))
        except Exception as db_exc:
            logger.error(f"Failed to store content generation error: {db_exc}")
        
        # Retry with exponential backoff
        if self.request.retries < 3:
            retry_countdown = 2 ** self.request.retries
            logger.warning(f"Retrying content generation for lead {lead_id} in {retry_countdown}s")
            raise self.retry(countdown=retry_countdown, exc=exc)
        else:
            return {
                "lead_id": lead_id,
                "task": "content_generation",
                "status": "failed",
                "error": str(exc),
                "retries": self.request.retries
            }

@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, AssessmentError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={'max_retries': 2},
    soft_time_limit=600,  # 10 minutes for full orchestration
    time_limit=720
)
def full_assessment_orchestrator_task(self, lead_id: int) -> Dict[str, Any]:
    """
    Execute complete assessment workflow orchestration using PRP-011.
    
    This task coordinates all assessment components in the correct order
    and provides comprehensive error handling and retry logic.
    
    Args:
        lead_id: Database ID of the lead to assess
        
    Returns:
        Dict containing complete assessment orchestration results
    """
    task_start = datetime.now(timezone.utc)
    
    try:
        logger.info(f"Starting full assessment orchestration for lead {lead_id}")
        
        # Get lead data
        async def get_lead_data():
            async with get_db() as db:
                result = await db.execute(select(Lead).where(Lead.id == lead_id))
                lead = result.scalar_one_or_none()
                if not lead:
                    raise AssessmentError(f"Lead {lead_id} not found")
                
                return {
                    'company': lead.company,
                    'url': lead.url,
                    'description': getattr(lead, 'description', ''),
                    'naics_code': getattr(lead, 'naics_code', None),
                    'state': getattr(lead, 'state', None),
                    'county': getattr(lead, 'county', None),
                    'contact_name': getattr(lead, 'contact_name', None)
                }
        
        lead_data = asyncio.run(get_lead_data())
        
        # PRP-011: Use actual Assessment Orchestrator
        from src.assessments.assessment_orchestrator import execute_full_assessment, AssessmentOrchestratorError
        
        try:
            # Execute complete assessment workflow
            execution_result = asyncio.run(execute_full_assessment(lead_id, lead_data))
            
            # Extract summary metrics
            success_rate = execution_result.success_rate
            total_cost = execution_result.total_cost_cents
            total_duration = execution_result.total_duration_ms
            
            # Count component successes and failures
            components = [
                execution_result.pagespeed_result,
                execution_result.security_result,
                execution_result.gbp_result,
                execution_result.screenshots_result,
                execution_result.semrush_result,
                execution_result.visual_analysis_result,
                execution_result.score_calculation_result,
                execution_result.content_generation_result
            ]
            
            successful_components = sum(1 for comp in components if comp.status.value == "success")
            failed_components = sum(1 for comp in components if comp.status.value == "failed")
            
            # Update assessment record with orchestration results
            orchestration_data = {
                "execution_id": execution_result.execution_id,
                "status": execution_result.status.value,
                "start_time": execution_result.start_time.isoformat(),
                "end_time": execution_result.end_time.isoformat() if execution_result.end_time else None,
                "total_duration_ms": execution_result.total_duration_ms,
                "total_cost_cents": execution_result.total_cost_cents,
                "success_rate": execution_result.success_rate,
                "error_summary": execution_result.error_summary,
                "component_summary": {
                    "successful": successful_components,
                    "failed": failed_components,
                    "total": len(components)
                }
            }
            
            asyncio.run(update_assessment_field(
                lead_id,
                'orchestration_result',
                orchestration_data
            ))
            
            # Store orchestration cost record
            cost_record = AssessmentCost.create_orchestration_cost(
                lead_id=lead_id,
                cost_cents=0.0,  # Orchestration itself has no direct cost
                response_status=execution_result.status.value,
                response_time_ms=execution_result.total_duration_ms
            )
            
            async def store_cost_record():
                async with get_db() as db:
                    db.add(cost_record)
                    await db.commit()
            
            asyncio.run(store_cost_record())
                
        except AssessmentOrchestratorError as orchestrator_exc:
            # Log specific orchestrator errors
            logger.error(f"Assessment Orchestrator error for lead {lead_id}: {orchestrator_exc}")
            raise AssessmentError(f"Assessment Orchestrator failed: {orchestrator_exc}")
        except Exception as exc:
            # Handle any other errors from orchestration
            logger.error(f"Assessment orchestration error for lead {lead_id}: {exc}")
            raise AssessmentError(f"Assessment orchestration failed: {exc}")
        
        # Mark task as completed
        task_duration = (datetime.now(timezone.utc) - task_start).total_seconds()
        
        # Update assessment status based on orchestration result
        final_status = ASSESSMENT_STATUS.COMPLETED if success_rate >= 0.8 else ASSESSMENT_STATUS.PARTIAL if success_rate >= 0.5 else ASSESSMENT_STATUS.FAILED
        asyncio.run(update_assessment_status(lead_id, final_status))
        
        # Prepare task result
        task_result = {
            "lead_id": lead_id,
            "task": "full_assessment_orchestrator",
            "status": "completed",
            "execution_id": execution_result.execution_id,
            "orchestration_status": execution_result.status.value,
            "success_rate": execution_result.success_rate,
            "successful_components": successful_components,
            "failed_components": failed_components,
            "total_cost_cents": execution_result.total_cost_cents,
            "total_cost_dollars": execution_result.total_cost_cents / 100,
            "total_duration_ms": execution_result.total_duration_ms,
            "error_count": len(execution_result.error_summary),
            "business_score": execution_result.business_score.overall_score if execution_result.business_score else None,
            "marketing_content_generated": execution_result.marketing_content is not None,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "worker_id": self.request.hostname
        }
        
        logger.info(f"Full assessment orchestration completed for lead {lead_id}: {success_rate:.1%} success, ${total_cost/100:.4f} cost, {total_duration}ms")
        return task_result
        
    except Exception as exc:
        error_msg = f"Full assessment orchestration failed for lead {lead_id}: {exc}"
        logger.error(error_msg)
        
        # Store error in database
        try:
            asyncio.run(update_assessment_field(
                lead_id,
                'orchestration_result',
                {"error": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()}
            ))
        except Exception as db_exc:
            logger.error(f"Failed to store orchestration error: {db_exc}")
        
        # Retry with exponential backoff
        if self.request.retries < 2:
            retry_countdown = 60 * (2 ** self.request.retries)  # 1 min, 2 min delays
            logger.warning(f"Retrying full assessment orchestration for lead {lead_id} in {retry_countdown}s")
            raise self.retry(countdown=retry_countdown, exc=exc)
        else:
            return {
                "lead_id": lead_id,
                "task": "full_assessment_orchestrator",
                "status": "failed",
                "error": str(exc),
                "retries": self.request.retries
            }

@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, AssessmentError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={'max_retries': 3},
    soft_time_limit=300,  # 5 minutes for report generation
    time_limit=360
)
def report_generation_task(self, lead_id: int) -> Dict[str, Any]:
    """
    Execute PDF/HTML report generation using PRP-011.
    
    Args:
        lead_id: Database ID of the lead to generate report for
        
    Returns:
        Dict containing report generation results
    """
    task_start = datetime.now(timezone.utc)
    
    try:
        logger.info(f"Starting report generation for lead {lead_id}")
        
        # Get lead data
        async def get_lead_data():
            async with get_db() as db:
                result = await db.execute(select(Lead).where(Lead.id == lead_id))
                lead = result.scalar_one_or_none()
                if not lead:
                    raise AssessmentError(f"Lead {lead_id} not found")
                return lead
        
        lead = asyncio.run(get_lead_data())
        
        # PRP-011: Use actual Report Builder integration
        from src.reports.builder import generate_assessment_report, ReportBuilderError
        
        try:
            # Execute report generation
            report_result = asyncio.run(generate_assessment_report(lead_id))
            
            # Prepare structured data for database storage
            report_data = {
                "report_id": report_result.report_id,
                "generation_timestamp": report_result.generation_timestamp,
                "report_type": report_result.report_type,
                "format": report_result.format,
                "html_url": report_result.html_url,
                "pdf_url": report_result.pdf_url,
                "file_size_bytes": report_result.file_size_bytes,
                "page_count": report_result.page_count,
                "generation_time_ms": report_result.generation_time_ms,
                "template_version": report_result.template_version,
                "sections_included": report_result.sections_included,
                "business_name": lead.company,
                "report_status": "completed"
            }
            
            # Update assessment record with report data
            asyncio.run(update_assessment_field(
                lead_id,
                'report_data',
                report_data
            ))
            
            # Store cost record (internal generation - no external API cost)
            cost_record = AssessmentCost.create_report_cost(
                lead_id=lead_id,
                cost_cents=0.0,  # Internal report generation
                response_status="success",
                response_time_ms=report_result.generation_time_ms
            )
            
            async def store_cost_record():
                async with get_db() as db:
                    db.add(cost_record)
                    await db.commit()
            
            asyncio.run(store_cost_record())
                
        except ReportBuilderError as report_exc:
            logger.error(f"Report Builder error for lead {lead_id}: {report_exc}")
            raise AssessmentError(f"Report Builder failed: {report_exc}")
        except Exception as exc:
            logger.error(f"Report generation error for lead {lead_id}: {exc}")
            raise AssessmentError(f"Report generation failed: {exc}")
        
        # Prepare task result
        task_result = {
            "lead_id": lead_id,
            "task": "report_generation",
            "status": "completed",
            "report_id": report_result.report_id,
            "format": report_result.format,
            "file_size_bytes": report_result.file_size_bytes,
            "page_count": report_result.page_count,
            "html_available": report_result.html_url is not None,
            "pdf_available": report_result.pdf_url is not None,
            "sections_count": len(report_result.sections_included),
            "generation_time_ms": report_result.generation_time_ms,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "worker_id": self.request.hostname
        }
        
        logger.info(f"Report generation completed for lead {lead_id}: {report_result.format}, {report_result.file_size_bytes} bytes, {report_result.page_count} pages")
        return task_result
        
    except Exception as exc:
        error_msg = f"Report generation failed for lead {lead_id}: {exc}"
        logger.error(error_msg)
        
        # Store error in database
        try:
            asyncio.run(update_assessment_field(
                lead_id,
                'report_data',
                {"error": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()}
            ))
        except Exception as db_exc:
            logger.error(f"Failed to store report generation error: {db_exc}")
        
        # Retry with exponential backoff
        if self.request.retries < 3:
            retry_countdown = 30 * (2 ** self.request.retries)
            logger.warning(f"Retrying report generation for lead {lead_id} in {retry_countdown}s")
            raise self.retry(countdown=retry_countdown, exc=exc)
        else:
            return {
                "lead_id": lead_id,
                "task": "report_generation",
                "status": "failed",
                "error": str(exc),
                "retries": self.request.retries
            }

@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, AssessmentError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={'max_retries': 3},
    soft_time_limit=60,  # Email formatting should be fast
    time_limit=90
)
def email_formatting_task(self, lead_id: int) -> Dict[str, Any]:
    """
    Execute email formatting using PRP-012.
    
    Args:
        lead_id: Database ID of the lead to format email for
        
    Returns:
        Dict containing email formatting results
    """
    task_start = datetime.now(timezone.utc)
    
    try:
        logger.info(f"Starting email formatting for lead {lead_id}")
        
        # Get marketing content data
        async def get_content_data():
            async with get_db() as db:
                # Get assessment with marketing content
                assessment_result = await db.execute(select(Assessment).where(Assessment.lead_id == lead_id))
                assessment = assessment_result.scalar_one_or_none()
                if not assessment or not assessment.marketing_content:
                    raise AssessmentError(f"Marketing content not available for lead {lead_id}")
                
                return assessment.marketing_content
        
        content_data = asyncio.run(get_content_data())
        
        # PRP-012: Use actual Email Formatter integration
        from src.email.formatter import format_business_email, EmailFormattingError
        
        try:
            # Execute email formatting
            formatted_email = asyncio.run(format_business_email(lead_id, content_data))
            
            # Prepare structured data for database storage
            email_data = {
                "email_id": formatted_email.id,
                "lead_id": formatted_email.lead_id,
                "to_address": formatted_email.to_address,
                "from_address": formatted_email.from_address,
                "reply_to": formatted_email.reply_to,
                "subject": formatted_email.subject,
                "html_body_size": len(formatted_email.html_body),
                "text_body_size": len(formatted_email.text_body),
                "headers": formatted_email.headers,
                "compliance_metadata": formatted_email.compliance_metadata,
                "spam_score": formatted_email.spam_score,
                "created_at": formatted_email.created_at.isoformat(),
                "formatting_status": "completed"
            }
            
            # Update assessment record with email data
            asyncio.run(update_assessment_field(
                lead_id,
                'formatted_email',
                email_data
            ))
            
            # Store cost record (internal formatting - no external API cost)
            cost_record = AssessmentCost.create_email_cost(
                lead_id=lead_id,
                cost_cents=0.0,  # Internal email formatting
                response_status="success",
                response_time_ms=int((datetime.now(timezone.utc) - task_start).total_seconds() * 1000)
            )
            
            async def store_cost_record():
                async with get_db() as db:
                    db.add(cost_record)
                    await db.commit()
            
            asyncio.run(store_cost_record())
                
        except EmailFormattingError as email_exc:
            logger.error(f"Email Formatter error for lead {lead_id}: {email_exc}")
            raise AssessmentError(f"Email Formatter failed: {email_exc}")
        except Exception as exc:
            logger.error(f"Email formatting error for lead {lead_id}: {exc}")
            raise AssessmentError(f"Email formatting failed: {exc}")
        
        # Prepare task result
        task_result = {
            "lead_id": lead_id,
            "task": "email_formatting",
            "status": "completed",
            "email_id": formatted_email.id,
            "to_address": formatted_email.to_address,
            "subject_length": len(formatted_email.subject),
            "html_body_size": len(formatted_email.html_body),
            "text_body_size": len(formatted_email.text_body),
            "compliance_score": formatted_email.compliance_metadata.get('compliance_score', 0),
            "spam_score": formatted_email.spam_score,
            "headers_count": len(formatted_email.headers),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "worker_id": self.request.hostname
        }
        
        logger.info(f"Email formatting completed for lead {lead_id}: spam score {formatted_email.spam_score:.1f}, compliance {task_result['compliance_score']}")
        return task_result
        
    except Exception as exc:
        error_msg = f"Email formatting failed for lead {lead_id}: {exc}"
        logger.error(error_msg)
        
        # Store error in database
        try:
            asyncio.run(update_assessment_field(
                lead_id,
                'formatted_email',
                {"error": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()}
            ))
        except Exception as db_exc:
            logger.error(f"Failed to store email formatting error: {db_exc}")
        
        # Retry with exponential backoff
        if self.request.retries < 3:
            retry_countdown = 10 * (2 ** self.request.retries)
            logger.warning(f"Retrying email formatting for lead {lead_id} in {retry_countdown}s")
            raise self.retry(countdown=retry_countdown, exc=exc)
        else:
            return {
                "lead_id": lead_id,
                "task": "email_formatting",
                "status": "failed",
                "error": str(exc),
                "retries": self.request.retries
            }

@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, AssessmentError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={'max_retries': 2},
    soft_time_limit=120,  # Testing dashboard operations
    time_limit=150
)
def testing_dashboard_task(self, lead_id: int) -> Dict[str, Any]:
    """
    Execute testing dashboard validation using PRP-013.
    
    Args:
        lead_id: Database ID of the lead to test
        
    Returns:
        Dict containing testing dashboard results
    """
    task_start = datetime.now(timezone.utc)
    
    try:
        logger.info(f"Starting testing dashboard validation for lead {lead_id}")
        
        # Get lead data
        async def get_lead_data():
            async with get_db() as db:
                result = await db.execute(select(Lead).where(Lead.id == lead_id))
                lead = result.scalar_one_or_none()
                if not lead:
                    raise AssessmentError(f"Lead {lead_id} not found")
                
                return {
                    'business_name': lead.company,
                    'website_url': lead.url,
                    'email': getattr(lead, 'email', ''),
                    'contact_name': getattr(lead, 'contact_name', ''),
                    'industry': getattr(lead, 'naics_code', ''),
                    'location': f"{getattr(lead, 'state', '')}, {getattr(lead, 'county', '')}"
                }
        
        lead_data = asyncio.run(get_lead_data())
        
        # PRP-013: Use actual Testing Dashboard integration
        from src.testing.dashboard import run_full_pipeline_test, TestingDashboardError
        
        try:
            # Execute complete pipeline test
            test_result = asyncio.run(run_full_pipeline_test(lead_data, user_id=1))
            
            # Prepare structured data for database storage
            testing_data = {
                "test_id": test_result.id,
                "test_type": test_result.test_type,
                "status": test_result.status.value,
                "success_rate": test_result.success_rate,
                "execution_time_ms": test_result.execution_time_ms,
                "pipeline_steps": len(test_result.pipeline_results),
                "successful_steps": sum(1 for step in test_result.pipeline_results if step.status.value == "success"),
                "failed_steps": sum(1 for step in test_result.pipeline_results if step.status.value == "failed"),
                "created_at": test_result.created_at.isoformat(),
                "completed_at": test_result.completed_at.isoformat() if test_result.completed_at else None,
                "error_message": test_result.error_message,
                "pipeline_results": [
                    {
                        "step_name": step.step_name,
                        "step_number": step.step_number,
                        "status": step.status.value,
                        "duration_ms": step.duration_ms,
                        "error_message": step.error_message
                    }
                    for step in test_result.pipeline_results
                ],
                "testing_status": "completed"
            }
            
            # Update assessment record with testing data
            asyncio.run(update_assessment_field(
                lead_id,
                'testing_results',
                testing_data
            ))
            
            # Store cost record (internal testing - no external API cost)
            cost_record = AssessmentCost.create_dashboard_cost(
                lead_id=lead_id,
                cost_cents=0.0,  # Internal testing dashboard
                response_status=test_result.status.value,
                response_time_ms=test_result.execution_time_ms
            )
            
            async def store_cost_record():
                async with get_db() as db:
                    db.add(cost_record)
                    await db.commit()
            
            asyncio.run(store_cost_record())
                
        except TestingDashboardError as testing_exc:
            logger.error(f"Testing Dashboard error for lead {lead_id}: {testing_exc}")
            raise AssessmentError(f"Testing Dashboard failed: {testing_exc}")
        except Exception as exc:
            logger.error(f"Testing dashboard error for lead {lead_id}: {exc}")
            raise AssessmentError(f"Testing dashboard failed: {exc}")
        
        # Prepare task result
        task_result = {
            "lead_id": lead_id,
            "task": "testing_dashboard",
            "status": "completed",
            "test_id": test_result.id,
            "test_status": test_result.status.value,
            "success_rate": test_result.success_rate,
            "pipeline_steps": len(test_result.pipeline_results),
            "successful_steps": testing_data["successful_steps"],
            "failed_steps": testing_data["failed_steps"],
            "execution_time_ms": test_result.execution_time_ms,
            "validation_passed": test_result.success_rate >= 80.0,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "worker_id": self.request.hostname
        }
        
        logger.info(f"Testing dashboard validation completed for lead {lead_id}: {test_result.success_rate:.1f}% success, {len(test_result.pipeline_results)} steps")
        return task_result
        
    except Exception as exc:
        error_msg = f"Testing dashboard validation failed for lead {lead_id}: {exc}"
        logger.error(error_msg)
        
        # Store error in database
        try:
            asyncio.run(update_assessment_field(
                lead_id,
                'testing_results',
                {"error": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()}
            ))
        except Exception as db_exc:
            logger.error(f"Failed to store testing dashboard error: {db_exc}")
        
        # Retry with exponential backoff
        if self.request.retries < 2:
            retry_countdown = 30 * (2 ** self.request.retries)
            logger.warning(f"Retrying testing dashboard validation for lead {lead_id} in {retry_countdown}s")
            raise self.retry(countdown=retry_countdown, exc=exc)
        else:
            return {
                "lead_id": lead_id,
                "task": "testing_dashboard",
                "status": "failed",
                "error": str(exc),
                "retries": self.request.retries
            }
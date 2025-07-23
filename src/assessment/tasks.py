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
    'semrush_task',
    'visual_task'
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
        
        # TODO: Implement actual PageSpeed API client (will be in PRP-003)
        # For now, simulate assessment with placeholder data
        import time
        import random
        
        # Simulate API call delay
        time.sleep(random.uniform(2, 8))
        
        # Placeholder PageSpeed results
        pagespeed_results = {
            "url": url,
            "strategy": "mobile",
            "lighthouse_result": {
                "categories": {
                    "performance": {"score": random.uniform(0.3, 0.9)},
                    "accessibility": {"score": random.uniform(0.7, 1.0)},
                    "best_practices": {"score": random.uniform(0.6, 1.0)},
                    "seo": {"score": random.uniform(0.8, 1.0)}
                },
                "audits": {
                    "first_contentful_paint": {"displayValue": f"{random.randint(1200, 3000)}ms"},
                    "largest_contentful_paint": {"displayValue": f"{random.randint(2000, 5000)}ms"},
                    "cumulative_layout_shift": {"displayValue": random.uniform(0.05, 0.25)},
                    "speed_index": {"displayValue": f"{random.randint(2000, 6000)}ms"}
                }
            },
            "loading_experience": {
                "metrics": {
                    "CUMULATIVE_LAYOUT_SHIFT_SCORE": {"percentile": random.randint(30, 90)},
                    "FIRST_CONTENTFUL_PAINT_MS": {"percentile": random.randint(1000, 3500)},
                    "LARGEST_CONTENTFUL_PAINT_MS": {"percentile": random.randint(2000, 5500)}
                }
            },
            "analysis_timestamp": task_start.isoformat(),
            "analysis_duration_ms": int((datetime.now(timezone.utc) - task_start).total_seconds() * 1000)
        }
        
        # Calculate performance score (0-100)
        performance_score = int(pagespeed_results["lighthouse_result"]["categories"]["performance"]["score"] * 100)
        
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
    Execute security header analysis assessment.
    
    Args:
        lead_id: Database ID of the lead to assess
        
    Returns:
        Dict containing security assessment results
    """
    task_start = datetime.now(timezone.utc)
    
    try:
        logger.info(f"Starting security assessment for lead {lead_id}")
        
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
        
        # TODO: Implement actual security scanner (will be in PRP-004)
        # For now, simulate assessment with placeholder data
        import time
        import random
        
        time.sleep(random.uniform(3, 10))
        
        # Placeholder security results
        security_headers = {
            "url": url,
            "scan_timestamp": task_start.isoformat(),
            "headers": {
                "content_security_policy": random.choice([True, False]),
                "strict_transport_security": random.choice([True, False]),
                "x_frame_options": random.choice([True, False]),
                "x_content_type_options": random.choice([True, False]),
                "referrer_policy": random.choice([True, False]),
                "permissions_policy": random.choice([True, False])
            },
            "ssl_info": {
                "valid_certificate": True,
                "certificate_grade": random.choice(['A+', 'A', 'B', 'C']),
                "tls_version": random.choice(['TLS 1.3', 'TLS 1.2']),
                "cipher_strength": random.choice(['Strong', 'Medium', 'Weak'])
            },
            "vulnerabilities": {
                "missing_security_headers": random.randint(0, 3),
                "insecure_configurations": random.randint(0, 2),
                "outdated_libraries": random.randint(0, 5)
            },
            "analysis_duration_ms": int((datetime.now(timezone.utc) - task_start).total_seconds() * 1000)
        }
        
        # Calculate security score based on headers and SSL
        headers_present = sum(1 for present in security_headers["headers"].values() if present)
        ssl_grade_scores = {'A+': 100, 'A': 90, 'B': 75, 'C': 60}
        
        security_score = int(
            (headers_present / 6 * 70) +  # 70% weight for headers
            (ssl_grade_scores.get(security_headers["ssl_info"]["certificate_grade"], 50) * 0.3)  # 30% weight for SSL
        )
        
        # Store results in database
        asyncio.run(update_assessment_field(
            lead_id,
            'security_headers',
            security_headers,
            'security_score',
            security_score
        ))
        
        task_result = {
            "lead_id": lead_id,
            "task": "security",
            "status": "completed",
            "score": security_score,
            "headers_found": headers_present,
            "ssl_grade": security_headers["ssl_info"]["certificate_grade"],
            "duration_ms": security_headers["analysis_duration_ms"],
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "worker_id": self.request.hostname
        }
        
        logger.info(f"Security assessment completed for lead {lead_id}: score {security_score}")
        return task_result
        
    except Exception as exc:
        error_msg = f"Security assessment failed for lead {lead_id}: {exc}"
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
            logger.warning(f"Retrying security assessment for lead {lead_id} in {retry_countdown}s")
            raise self.retry(countdown=retry_countdown, exc=exc)
        else:
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
    Execute Google Business Profile data collection.
    
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
                return lead.company, lead.city, lead.state
        
        company, city, state = asyncio.run(get_lead_info())
        
        # TODO: Implement actual GBP API client (will be in PRP-005)
        # For now, simulate assessment with placeholder data
        import time
        import random
        
        time.sleep(random.uniform(2, 6))
        
        # Placeholder GBP results
        gbp_data = {
            "business_name": company,
            "search_location": f"{city}, {state}" if city and state else "Unknown",
            "found_listing": random.choice([True, False]),
            "listing_data": {
                "name": company,
                "address": f"123 Main St, {city}, {state}" if city and state else None,
                "phone": f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}",
                "website": f"https://{company.lower().replace(' ', '')}.com",
                "rating": round(random.uniform(3.5, 5.0), 1),
                "review_count": random.randint(10, 500),
                "categories": ["Business Service", "Professional Service"],
                "hours": {
                    "monday": "9:00 AM – 5:00 PM",
                    "tuesday": "9:00 AM – 5:00 PM",
                    "wednesday": "9:00 AM – 5:00 PM",
                    "thursday": "9:00 AM – 5:00 PM",
                    "friday": "9:00 AM – 5:00 PM",
                    "saturday": "Closed",
                    "sunday": "Closed"
                }
            },
            "completeness_score": random.randint(60, 95),
            "missing_fields": random.choice([[], ["photos", "description"], ["hours"], ["website", "phone"]]),
            "search_timestamp": task_start.isoformat(),
            "analysis_duration_ms": int((datetime.now(timezone.utc) - task_start).total_seconds() * 1000)
        }
        
        # Use completeness score as the mobile score (GBP affects mobile search)
        mobile_score = gbp_data["completeness_score"]
        
        # Store results in database
        asyncio.run(update_assessment_field(
            lead_id,
            'gbp_data',
            gbp_data,
            'mobile_score',
            mobile_score
        ))
        
        task_result = {
            "lead_id": lead_id,
            "task": "gbp",
            "status": "completed",
            "score": mobile_score,
            "listing_found": gbp_data["found_listing"],
            "rating": gbp_data["listing_data"]["rating"] if gbp_data["found_listing"] else None,
            "review_count": gbp_data["listing_data"]["review_count"] if gbp_data["found_listing"] else None,
            "duration_ms": gbp_data["analysis_duration_ms"],
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "worker_id": self.request.hostname
        }
        
        logger.info(f"GBP assessment completed for lead {lead_id}: score {mobile_score}")
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
    soft_time_limit=90,
    time_limit=120
)
def semrush_task(self, lead_id: int) -> Dict[str, Any]:
    """
    Execute SEMrush SEO analysis.
    
    Args:
        lead_id: Database ID of the lead to assess
        
    Returns:
        Dict containing SEMrush assessment results
    """
    task_start = datetime.now(timezone.utc)
    
    try:
        logger.info(f"Starting SEMrush assessment for lead {lead_id}")
        
        # Get lead information
        async def get_lead_url():
            async with get_db() as db:
                result = await db.execute(select(Lead).where(Lead.id == lead_id))
                lead = result.scalar_one_or_none()
                if not lead:
                    raise AssessmentError(f"Lead {lead_id} not found")
                if not lead.url:
                    raise AssessmentError(f"Lead {lead_id} has no URL for SEMrush analysis")
                return lead.url, lead.company
        
        url, company = asyncio.run(get_lead_url())
        
        # TODO: Implement actual SEMrush API client (will be in PRP-007)
        # For now, simulate assessment with placeholder data
        import time
        import random
        
        time.sleep(random.uniform(4, 12))
        
        # Placeholder SEMrush results
        semrush_data = {
            "domain": url.replace('https://', '').replace('http://', ''),
            "overview": {
                "organic_keywords": random.randint(50, 5000),
                "organic_traffic": random.randint(100, 50000),
                "organic_cost": random.randint(500, 25000),
                "adwords_keywords": random.randint(10, 1000),
                "adwords_traffic": random.randint(50, 5000),
                "adwords_cost": random.randint(100, 10000)
            },
            "top_keywords": [
                {"keyword": f"{company.lower()} services", "position": random.randint(1, 10), "volume": random.randint(100, 1000)},
                {"keyword": f"{company.lower()} company", "position": random.randint(5, 20), "volume": random.randint(50, 500)},
                {"keyword": "business solutions", "position": random.randint(10, 50), "volume": random.randint(200, 2000)},
            ],
            "competitors": [
                {"domain": "competitor1.com", "common_keywords": random.randint(10, 100)},
                {"domain": "competitor2.com", "common_keywords": random.randint(5, 80)},
                {"domain": "competitor3.com", "common_keywords": random.randint(15, 120)},
            ],
            "backlinks": {
                "total_backlinks": random.randint(100, 10000),
                "referring_domains": random.randint(20, 1000),
                "authority_score": random.randint(30, 80)
            },
            "search_timestamp": task_start.isoformat(),
            "analysis_duration_ms": int((datetime.now(timezone.utc) - task_start).total_seconds() * 1000)
        }
        
        # Calculate SEO score based on keyword performance and backlinks
        keyword_score = min(100, semrush_data["overview"]["organic_keywords"] / 50)  # Max at 50+ keywords
        traffic_score = min(100, semrush_data["overview"]["organic_traffic"] / 500)  # Max at 500+ traffic
        authority_score = semrush_data["backlinks"]["authority_score"]
        
        seo_score = int((keyword_score * 0.4) + (traffic_score * 0.3) + (authority_score * 0.3))
        
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
            "organic_keywords": semrush_data["overview"]["organic_keywords"],
            "organic_traffic": semrush_data["overview"]["organic_traffic"],
            "authority_score": semrush_data["backlinks"]["authority_score"],
            "duration_ms": semrush_data["analysis_duration_ms"],
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "worker_id": self.request.hostname
        }
        
        logger.info(f"SEMrush assessment completed for lead {lead_id}: score {seo_score}")
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
    soft_time_limit=90,
    time_limit=120
)
def visual_task(self, lead_id: int) -> Dict[str, Any]:
    """
    Execute visual website analysis.
    
    Args:
        lead_id: Database ID of the lead to assess
        
    Returns:
        Dict containing visual assessment results
    """
    task_start = datetime.now(timezone.utc)
    
    try:
        logger.info(f"Starting visual assessment for lead {lead_id}")
        
        # Get lead information
        async def get_lead_url():
            async with get_db() as db:
                result = await db.execute(select(Lead).where(Lead.id == lead_id))
                lead = result.scalar_one_or_none()
                if not lead:
                    raise AssessmentError(f"Lead {lead_id} not found")
                if not lead.url:
                    raise AssessmentError(f"Lead {lead_id} has no URL for visual analysis")
                return lead.url, lead.company
        
        url, company = asyncio.run(get_lead_url())
        
        # TODO: Implement actual visual analysis (will be in PRP-006 and PRP-008)
        # For now, simulate assessment with placeholder data
        import time
        import random
        
        time.sleep(random.uniform(5, 15))  # Visual analysis takes longer
        
        # Placeholder visual analysis results
        visual_analysis = {
            "url": url,
            "screenshot_metadata": {
                "desktop_screenshot": f"screenshots/{lead_id}/desktop_{int(datetime.now().timestamp())}.png",
                "mobile_screenshot": f"screenshots/{lead_id}/mobile_{int(datetime.now().timestamp())}.png",
                "resolution": "1920x1080",
                "mobile_resolution": "375x667"
            },
            "design_analysis": {
                "color_scheme": random.choice(["professional", "modern", "outdated", "inconsistent"]),
                "layout_quality": random.choice(["excellent", "good", "fair", "poor"]),
                "mobile_responsiveness": random.choice(["fully responsive", "partially responsive", "not responsive"]),
                "typography": random.choice(["modern", "standard", "outdated"]),
                "whitespace_usage": random.choice(["optimal", "good", "cluttered"])
            },
            "technical_issues": {
                "broken_images": random.randint(0, 3),
                "layout_issues": random.randint(0, 2),
                "mobile_issues": random.randint(0, 4)
            },
            "user_experience": {
                "navigation_clarity": random.randint(60, 95),
                "content_readability": random.randint(70, 95),
                "call_to_action_visibility": random.randint(50, 90),
                "loading_experience": random.randint(60, 90)
            },
            "screenshot_timestamp": task_start.isoformat(),
            "analysis_duration_ms": int((datetime.now(timezone.utc) - task_start).total_seconds() * 1000)
        }
        
        # Calculate visual score based on design quality and UX factors
        design_scores = {"excellent": 95, "good": 80, "fair": 65, "poor": 40}
        layout_score = design_scores.get(visual_analysis["design_analysis"]["layout_quality"], 50)
        
        # Average UX scores
        ux_scores = visual_analysis["user_experience"]
        avg_ux_score = sum(ux_scores.values()) / len(ux_scores)
        
        # Penalize for technical issues
        issue_penalty = (visual_analysis["technical_issues"]["broken_images"] * 5 + 
                        visual_analysis["technical_issues"]["layout_issues"] * 10 +
                        visual_analysis["technical_issues"]["mobile_issues"] * 3)
        
        visual_score = max(0, int((layout_score * 0.4) + (avg_ux_score * 0.6) - issue_penalty))
        
        # Store results in database
        asyncio.run(update_assessment_field(
            lead_id,
            'visual_analysis',
            visual_analysis
            # Note: visual analysis doesn't map to a specific score field in our current schema
            # The overall score will be calculated in aggregate_results
        ))
        
        task_result = {
            "lead_id": lead_id,
            "task": "visual",
            "status": "completed",
            "score": visual_score,
            "layout_quality": visual_analysis["design_analysis"]["layout_quality"],
            "mobile_responsive": visual_analysis["design_analysis"]["mobile_responsiveness"],
            "technical_issues": sum(visual_analysis["technical_issues"].values()),
            "duration_ms": visual_analysis["analysis_duration_ms"],
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "worker_id": self.request.hostname
        }
        
        logger.info(f"Visual assessment completed for lead {lead_id}: score {visual_score}")
        return task_result
        
    except Exception as exc:
        error_msg = f"Visual assessment failed for lead {lead_id}: {exc}"
        logger.error(error_msg)
        
        # Store error in database
        try:
            asyncio.run(update_assessment_field(
                lead_id,
                'visual_analysis',
                {"error": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()}
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
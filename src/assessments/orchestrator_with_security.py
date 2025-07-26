"""
Assessment Orchestrator - Complete Assessment Pipeline
Runs PageSpeed, Security, GBP, SEMrush, Screenshot Capture, and Visual Analysis assessments
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


async def run_assessments(url: str, business_name: str = "", assessment_id: Optional[int] = None, 
                         address: Optional[str] = None, city: Optional[str] = None, 
                         state: Optional[str] = None) -> Dict[str, Any]:
    """
    Run complete assessment pipeline: PageSpeed, Security, GBP, SEMrush, Screenshots, and Visual Analysis
    
    The assessments run in two phases:
    - Phase 1: PageSpeed, Security, GBP, SEMrush, and Screenshot Capture run in parallel
    - Phase 2: Visual Analysis runs after screenshots are captured (depends on screenshot URLs)
    
    Args:
        url: Website URL to assess
        business_name: Business name
        assessment_id: Optional assessment ID for database storage (also used as lead_id)
        address: Business address (optional, for GBP)
        city: Business city (optional, for GBP)
        state: Business state (optional, for GBP)
        
    Returns:
        Dict with assessment results, including formatted data for UI display:
        - pagespeed_data: Mobile and desktop PageSpeed scores
        - security_data: Security headers and vulnerabilities
        - gbp_data/gbp_summary: Google Business Profile info
        - semrush_data/semrush_summary: SEMrush domain metrics and SEO data
        - screenshot_data: Screenshot capture results and URLs
        - visual_analysis_data: UX analysis scores and recommendations
    """
    try:
        logger.info(f"Starting assessments for {url}")
        
        results = {
            "status": "success",
            "url": url,
            "business_name": business_name,
            "assessment_id": assessment_id,
            "assessments": {}
        }
        
        # Run assessments in two phases
        # Phase 1: Run assessments that don't depend on screenshots in parallel
        phase1_tasks = []
        
        # Use assessment_id as lead_id if available, otherwise use a default
        lead_id = assessment_id if assessment_id else 0
        
        # Extract domain from URL for SEMrush
        parsed_url = urlparse(url)
        domain = parsed_url.netloc or parsed_url.path  # Handle URLs with or without scheme
        if domain:
            # Remove www. prefix if present
            domain = domain.replace('www.', '')
        
        # PageSpeed assessment
        from src.assessments.pagespeed import get_pagespeed_client
        client = get_pagespeed_client()
        pagespeed_task = asyncio.create_task(client.analyze_mobile_first(url))
        phase1_tasks.append(("pagespeed", pagespeed_task))
        
        # Security assessment
        from src.assessments.security_analysis import assess_security_headers
        security_task = asyncio.create_task(assess_security_headers(url))
        phase1_tasks.append(("security", security_task))
        
        # Google Business Profile assessment
        if business_name:
            from src.assessments.gbp_integration import assess_google_business_profile
            gbp_task = asyncio.create_task(assess_google_business_profile(
                business_name=business_name,
                address=address,
                city=city,
                state=state,
                lead_id=lead_id,
                assessment_id=assessment_id
            ))
            phase1_tasks.append(("gbp", gbp_task))
        
        # Screenshot capture assessment
        from src.assessments.screenshot_capture import capture_website_screenshots
        screenshot_task = asyncio.create_task(capture_website_screenshots(url, lead_id))
        phase1_tasks.append(("screenshot", screenshot_task))
        
        # SEMrush assessment
        if domain:
            from src.assessments.semrush_integration import assess_semrush_domain
            semrush_task = asyncio.create_task(assess_semrush_domain(domain, lead_id, assessment_id))
            phase1_tasks.append(("semrush", semrush_task))
        
        # Wait for Phase 1 assessments to complete
        screenshot_results = None
        for assessment_name, task in phase1_tasks:
            try:
                result = await task
                results["assessments"][assessment_name] = {
                    "status": "success",
                    "data": result
                }
                logger.info(f"{assessment_name} assessment completed for {url}")
                
                # Store screenshot results for visual analysis
                if assessment_name == "screenshot":
                    screenshot_results = result
            except Exception as e:
                logger.error(f"{assessment_name} assessment failed for {url}: {e}")
                results["assessments"][assessment_name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # Phase 2: Run visual analysis if screenshots were captured
        if screenshot_results and screenshot_results.success:
            # Check for URLs in the screenshot results
            desktop_url = None
            mobile_url = None
            
            if screenshot_results.desktop_screenshot:
                desktop_url = (screenshot_results.desktop_screenshot.s3_url or 
                              screenshot_results.desktop_screenshot.signed_url or
                              f"https://screenshotone.com/image/{url}/desktop.webp")  # Fallback URL
            
            if screenshot_results.mobile_screenshot:
                mobile_url = (screenshot_results.mobile_screenshot.s3_url or 
                             screenshot_results.mobile_screenshot.signed_url or
                             f"https://screenshotone.com/image/{url}/mobile.webp")  # Fallback URL
            
            if desktop_url and mobile_url:
                try:
                    from src.assessments.visual_analysis import assess_visual_analysis
                    visual_result = await assess_visual_analysis(url, desktop_url, mobile_url, lead_id)
                    results["assessments"]["visual_analysis"] = {
                        "status": "success",
                        "data": visual_result
                    }
                    logger.info(f"visual_analysis assessment completed for {url}")
                except Exception as e:
                    logger.error(f"visual_analysis assessment failed for {url}: {e}")
                    results["assessments"]["visual_analysis"] = {
                        "status": "error",
                        "error": str(e)
                    }
            else:
                logger.warning(f"Visual analysis skipped - missing screenshot URLs for {url}")
                results["assessments"]["visual_analysis"] = {
                    "status": "skipped",
                    "error": "Missing screenshot URLs"
                }
        else:
            logger.warning(f"Visual analysis skipped - screenshot capture failed for {url}")
            results["assessments"]["visual_analysis"] = {
                "status": "skipped",
                "error": "Screenshot capture failed"
            }
        
        # Format PageSpeed data for UI
        pagespeed_results = results["assessments"].get("pagespeed", {}).get("data", {})
        if pagespeed_results:
            mobile_result = pagespeed_results.get("mobile")
            desktop_result = pagespeed_results.get("desktop")
            
            results["pagespeed_data"] = {
                "mobile_analysis": {
                    "core_web_vitals": mobile_result.core_web_vitals.dict() if mobile_result else {},
                    "lighthouse_result": mobile_result.lighthouse_result if mobile_result else {},
                    "url": mobile_result.url if mobile_result else url,
                    "strategy": mobile_result.strategy if mobile_result else "mobile",
                    "analysis_timestamp": mobile_result.analysis_timestamp if mobile_result else datetime.now().isoformat()
                } if mobile_result else {},
                "desktop_analysis": {
                    "core_web_vitals": desktop_result.core_web_vitals.dict() if desktop_result else {},
                    "lighthouse_result": desktop_result.lighthouse_result if desktop_result else {},
                    "url": desktop_result.url if desktop_result else url,
                    "strategy": desktop_result.strategy if desktop_result else "desktop",
                    "analysis_timestamp": desktop_result.analysis_timestamp if desktop_result else datetime.now().isoformat()
                } if desktop_result else {},
                "mobile_score": mobile_result.core_web_vitals.performance_score if mobile_result else 0,
                "desktop_score": desktop_result.core_web_vitals.performance_score if desktop_result else 0,
                "analysis_timestamp": datetime.now().isoformat()
            }
            results["raw_pagespeed_results"] = pagespeed_results
        
        # Format Security data for UI
        security_results = results["assessments"].get("security", {}).get("data")
        if security_results:
            results["security_data"] = security_results.dict() if hasattr(security_results, 'dict') else security_results
        
        # Format GBP data for UI
        gbp_results = results["assessments"].get("gbp", {}).get("data")
        if gbp_results:
            results["gbp_data"] = gbp_results
            # Extract key metrics for easy access
            if gbp_data := gbp_results.get("gbp_data"):
                results["gbp_summary"] = {
                    "found": gbp_results.get("match_found", False),
                    "confidence": gbp_results.get("match_confidence", 0.0),
                    "name": gbp_data.get("name", ""),
                    "rating": gbp_data.get("reviews", {}).get("average_rating", 0),
                    "review_count": gbp_data.get("reviews", {}).get("total_reviews", 0),
                    "is_open": gbp_data.get("status", {}).get("is_open_now"),
                    "verified": gbp_data.get("status", {}).get("verified", False)
                }
        
        # Format Screenshot data for UI
        screenshot_results = results["assessments"].get("screenshot", {}).get("data")
        if screenshot_results and hasattr(screenshot_results, 'dict'):
            screenshot_data = screenshot_results.dict()
            results["screenshot_data"] = {
                "success": screenshot_data.get("success", False),
                "desktop": {
                    "captured": screenshot_data.get("desktop_screenshot") is not None,
                    "url": (screenshot_data.get("desktop_screenshot", {}).get("s3_url") or 
                           screenshot_data.get("desktop_screenshot", {}).get("signed_url") or
                           f"https://screenshotone.com/image/{url}/desktop.webp" if screenshot_data.get("desktop_screenshot") else None),
                    "width": screenshot_data.get("desktop_screenshot", {}).get("width"),
                    "height": screenshot_data.get("desktop_screenshot", {}).get("height"),
                    "file_size": screenshot_data.get("desktop_screenshot", {}).get("file_size_bytes"),
                    "capture_duration_ms": screenshot_data.get("desktop_screenshot", {}).get("capture_duration_ms")
                } if screenshot_data.get("desktop_screenshot") else {"captured": False},
                "mobile": {
                    "captured": screenshot_data.get("mobile_screenshot") is not None,
                    "url": (screenshot_data.get("mobile_screenshot", {}).get("s3_url") or 
                           screenshot_data.get("mobile_screenshot", {}).get("signed_url") or
                           f"https://screenshotone.com/image/{url}/mobile.webp" if screenshot_data.get("mobile_screenshot") else None),
                    "width": screenshot_data.get("mobile_screenshot", {}).get("width"),
                    "height": screenshot_data.get("mobile_screenshot", {}).get("height"),
                    "file_size": screenshot_data.get("mobile_screenshot", {}).get("file_size_bytes"),
                    "capture_duration_ms": screenshot_data.get("mobile_screenshot", {}).get("capture_duration_ms")
                } if screenshot_data.get("mobile_screenshot") else {"captured": False},
                "error_message": screenshot_data.get("error_message"),
                "total_duration_ms": screenshot_data.get("total_duration_ms")
            }
        
        # Format Visual Analysis data for UI
        visual_results = results["assessments"].get("visual_analysis", {}).get("data")
        if visual_results and hasattr(visual_results, 'dict'):
            visual_data = visual_results.dict()
            if visual_data.get("success") and visual_data.get("metrics"):
                metrics = visual_data["metrics"]
                results["visual_analysis_data"] = {
                    "success": True,
                    "overall_ux_score": metrics.get("overall_ux_score", 0),
                    "rubrics": metrics.get("rubrics", []),
                    "desktop_analysis": metrics.get("desktop_analysis", {}),
                    "mobile_analysis": metrics.get("mobile_analysis", {}),
                    "critical_issues": metrics.get("critical_issues", []),
                    "positive_elements": metrics.get("positive_elements", []),
                    "api_cost_dollars": metrics.get("api_cost_dollars", 0),
                    "processing_time_ms": metrics.get("processing_time_ms", 0)
                }
                
                # Create a simplified rubric summary for UI
                rubric_summary = {}
                for rubric in metrics.get("rubrics", []):
                    rubric_summary[rubric["name"]] = {
                        "score": rubric["score"],
                        "explanation": rubric["explanation"],
                        "recommendations": rubric["recommendations"]
                    }
                results["visual_analysis_data"]["rubric_summary"] = rubric_summary
            else:
                results["visual_analysis_data"] = {
                    "success": False,
                    "error_message": visual_data.get("error_message", "Visual analysis failed")
                }
        
        # Format SEMrush data for UI
        semrush_results = results["assessments"].get("semrush", {}).get("data")
        if semrush_results and hasattr(semrush_results, 'dict'):
            semrush_data = semrush_results.dict()
            if semrush_data.get("success") and semrush_data.get("metrics"):
                metrics = semrush_data["metrics"]
                results["semrush_data"] = {
                    "success": True,
                    "domain": metrics.get("domain", domain),
                    "authority_score": metrics.get("authority_score", 0),
                    "backlink_toxicity_score": metrics.get("backlink_toxicity_score", 0.0),
                    "organic_traffic_estimate": metrics.get("organic_traffic_estimate", 0),
                    "ranking_keywords_count": metrics.get("ranking_keywords_count", 0),
                    "site_health_score": metrics.get("site_health_score", 0.0),
                    "technical_issues": metrics.get("technical_issues", []),
                    "api_cost_units": metrics.get("api_cost_units", 0),
                    "extraction_duration_ms": metrics.get("extraction_duration_ms", 0)
                }
                
                # Create a simplified summary for UI
                results["semrush_summary"] = {
                    "authority": metrics.get("authority_score", 0),
                    "traffic": metrics.get("organic_traffic_estimate", 0),
                    "keywords": metrics.get("ranking_keywords_count", 0),
                    "health": metrics.get("site_health_score", 0.0),
                    "has_issues": len(metrics.get("technical_issues", [])) > 0
                }
            else:
                results["semrush_data"] = {
                    "success": False,
                    "error_message": semrush_data.get("error_message", "SEMrush analysis failed")
                }
        
        logger.info(f"All assessments completed for {url}")
        return results
        
    except Exception as e:
        logger.error(f"Assessment orchestration failed for {url}: {e}")
        return {
            "status": "error",
            "url": url,
            "business_name": business_name,
            "error": str(e)
        }
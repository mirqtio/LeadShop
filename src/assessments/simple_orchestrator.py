"""
Simple Assessment Orchestrator - PageSpeed Only
No database dependencies, just returns JSON
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def run_pagespeed_assessment(url: str, business_name: str = "") -> Dict[str, Any]:
    """
    Run PageSpeed assessment only and return JSON result.
    No database operations, no other assessments.
    """
    try:
        logger.info(f"Starting PageSpeed assessment for {url}")
        
        # Import PageSpeed client directly - bypass the assess_pagespeed wrapper that uses database
        from src.assessments.pagespeed import get_pagespeed_client
        
        # Get the PageSpeed client
        client = get_pagespeed_client()
        
        # Mobile-first analysis
        results = await client.analyze_mobile_first(url)
        
        # Extract mobile results as primary
        mobile_result = results.get("mobile")
        desktop_result = results.get("desktop")
        
        # Format the response to match what the UI expects
        pagespeed_data = {
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
        
        logger.info(f"PageSpeed assessment completed for {url}")
        
        # Also include raw data for debugging
        debug_data = {
            "mobile_raw": mobile_result.dict() if mobile_result else None,
            "desktop_raw": desktop_result.dict() if desktop_result else None
        }
        
        return {
            "status": "success",
            "url": url,
            "business_name": business_name,
            "pagespeed_data": pagespeed_data,
            "debug_data": debug_data,
            "raw_pagespeed_results": results  # Include raw results for database saving
        }
        
    except Exception as e:
        logger.error(f"PageSpeed assessment failed for {url}: {e}")
        return {
            "status": "error",
            "url": url,
            "business_name": business_name,
            "error": str(e)
        }
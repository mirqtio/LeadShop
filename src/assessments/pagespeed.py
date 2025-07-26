"""
PRP-003: PageSpeed Integration
Google PageSpeed Insights API v5 integration for Core Web Vitals capture
"""

import httpx
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class CoreWebVitals(BaseModel):
    """Core Web Vitals metrics from PageSpeed Insights"""
    first_contentful_paint: Optional[float] = Field(None, description="FCP in milliseconds")
    largest_contentful_paint: Optional[float] = Field(None, description="LCP in milliseconds") 
    cumulative_layout_shift: Optional[float] = Field(None, description="CLS score")
    total_blocking_time: Optional[float] = Field(None, description="TBT in milliseconds")
    time_to_interactive: Optional[float] = Field(None, description="TTI in milliseconds")
    performance_score: Optional[int] = Field(None, description="Performance score 0-100")


class PageSpeedResult(BaseModel):
    """Complete PageSpeed assessment result"""
    url: str
    strategy: str  # mobile or desktop
    core_web_vitals: CoreWebVitals
    lighthouse_result: Dict[str, Any]
    loading_experience: Optional[Dict[str, Any]] = None
    analysis_timestamp: str
    analysis_duration_ms: int
    cost_cents: float = Field(default=0.25, description="API call cost in cents")


class PageSpeedError(Exception):
    """Custom exception for PageSpeed API errors"""
    pass


class PageSpeedClient:
    """
    Google PageSpeed Insights API v5 client with rate limiting and cost tracking
    Implements PRP-003 requirements with mobile-first strategy
    """
    
    BASE_URL = "https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed"
    COST_PER_CALL = 0.25  # $0.0025 in cents
    FREE_QUOTA_DAILY = 25000
    RATE_LIMIT_PER_SECOND = 50
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize PageSpeed client with API key and rate limiting"""
        self.api_key = api_key or settings.GOOGLE_PAGESPEED_API_KEY
        if not self.api_key:
            raise PageSpeedError("Google PageSpeed API key not configured")
        
        # HTTP client with timeout configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),  # Increased to 60-second timeout for complex sites
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )
        
        logger.info("PageSpeed client initialized", api_key_configured=bool(self.api_key))
    
    async def analyze_url(
        self, 
        url: str, 
        strategy: str = "mobile",
        categories: List[str] = None
    ) -> PageSpeedResult:
        """
        Analyze URL with Google PageSpeed Insights API v5
        
        Args:
            url: URL to analyze
            strategy: "mobile" (default) or "desktop" - mobile-first per PRP-003
            categories: List of Lighthouse categories to include
            
        Returns:
            PageSpeedResult with Core Web Vitals and performance data
            
        Raises:
            PageSpeedError: If API call fails or times out
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Default categories for comprehensive analysis
            if categories is None:
                categories = ["performance", "accessibility", "best-practices", "seo"]
            
            # Build API request parameters
            params = {
                "url": url,
                "key": self.api_key,
                "strategy": strategy,
                "category": categories,
                "locale": "en_US"
            }
            
            logger.info(f"Making PageSpeed API request to {self.BASE_URL}", extra={
                "url": url, 
                "strategy": strategy,
                "api_key_configured": bool(self.api_key),
                "params": {k: v for k, v in params.items() if k != 'key'}  # Don't log API key
            })
            
            # Make API request with timeout
            response = await self.client.get(self.BASE_URL, params=params)
            
            logger.info(f"PageSpeed API response received", extra={
                "status_code": response.status_code,
                "response_size": len(response.content) if response.content else 0,
                "url": url
            })
            
            if response.status_code == 429:
                raise PageSpeedError("Rate limit exceeded - too many requests")
            elif response.status_code == 400:
                raise PageSpeedError(f"Invalid URL or request parameters: {url}")
            elif response.status_code != 200:
                raise PageSpeedError(f"API request failed with status {response.status_code}: {response.text}")
            
            api_data = response.json()
            
            # Calculate analysis duration
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            # Extract Core Web Vitals from Lighthouse result
            core_web_vitals = self._extract_core_web_vitals(api_data)
            
            # Build result object
            result = PageSpeedResult(
                url=url,
                strategy=strategy,
                core_web_vitals=core_web_vitals,
                lighthouse_result=api_data.get("lighthouseResult", {}),
                loading_experience=api_data.get("loadingExperience"),
                analysis_timestamp=start_time.isoformat(),
                analysis_duration_ms=duration_ms,
                cost_cents=self.COST_PER_CALL
            )
            
            logger.info(
                f"PageSpeed analysis completed",
                url=url,
                strategy=strategy,
                performance_score=core_web_vitals.performance_score,
                duration_ms=duration_ms,
                cost_cents=self.COST_PER_CALL
            )
            
            return result
            
        except httpx.TimeoutException:
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            logger.error(f"PageSpeed API timeout after {duration_ms}ms", url=url)
            raise PageSpeedError(f"API request timed out after 60 seconds for {url}")
            
        except httpx.RequestError as exc:
            logger.error(f"PageSpeed API request failed", url=url, error=str(exc))
            raise PageSpeedError(f"Network error during API request: {exc}")
            
        except Exception as exc:
            logger.error(f"PageSpeed analysis failed", url=url, error=str(exc))
            raise PageSpeedError(f"Unexpected error during PageSpeed analysis: {exc}")
    
    def _extract_core_web_vitals(self, api_data: Dict) -> CoreWebVitals:
        """
        Extract Core Web Vitals metrics from PageSpeed API response
        
        Args:
            api_data: Raw API response data
            
        Returns:
            CoreWebVitals object with extracted metrics
        """
        try:
            lighthouse_result = api_data.get("lighthouseResult", {})
            audits = lighthouse_result.get("audits", {})
            categories = lighthouse_result.get("categories", {})
            
            # Extract performance score (0-100)
            performance_score = None
            if "performance" in categories:
                score = categories["performance"].get("score")
                if score is not None:
                    performance_score = int(score * 100)
            
            # Extract Core Web Vitals from specific audits
            def get_numeric_value(audit_key: str) -> Optional[float]:
                audit = audits.get(audit_key, {})
                if "numericValue" in audit:
                    return float(audit["numericValue"])
                return None
            
            core_web_vitals = CoreWebVitals(
                first_contentful_paint=get_numeric_value("first-contentful-paint"),
                largest_contentful_paint=get_numeric_value("largest-contentful-paint"),
                cumulative_layout_shift=get_numeric_value("cumulative-layout-shift"),
                total_blocking_time=get_numeric_value("total-blocking-time"),
                time_to_interactive=get_numeric_value("interactive"),
                performance_score=performance_score
            )
            
            logger.debug(
                "Core Web Vitals extracted",
                fcp=core_web_vitals.first_contentful_paint,
                lcp=core_web_vitals.largest_contentful_paint,
                cls=core_web_vitals.cumulative_layout_shift,
                tbt=core_web_vitals.total_blocking_time,
                tti=core_web_vitals.time_to_interactive,
                performance_score=core_web_vitals.performance_score
            )
            
            return core_web_vitals
            
        except Exception as exc:
            logger.error("Failed to extract Core Web Vitals", error=str(exc))
            # Return empty metrics rather than fail the entire assessment
            return CoreWebVitals()
    
    async def analyze_mobile_first(self, url: str) -> Dict[str, PageSpeedResult]:
        """
        Mobile-first analysis with optional desktop fallback
        Implements PRP-003 mobile-first strategy
        
        Args:
            url: URL to analyze
            
        Returns:
            Dict with mobile results and optional desktop results
        """
        results = {}
        
        try:
            # Primary mobile analysis
            results["mobile"] = await self.analyze_url(url, strategy="mobile")
            
            # Optional desktop analysis if mobile succeeds
            try:
                results["desktop"] = await self.analyze_url(url, strategy="desktop")
            except PageSpeedError as exc:
                logger.warning(f"Desktop analysis failed, mobile-only result", url=url, error=str(exc))
                # Continue with mobile-only results
            
        except PageSpeedError:
            # If mobile analysis fails, this is a critical error
            raise
        
        return results
    
    async def close(self):
        """Close HTTP client connections"""
        await self.client.aclose()


# Global client instance for reuse
_pagespeed_client: Optional[PageSpeedClient] = None


def get_pagespeed_client() -> PageSpeedClient:
    """Get global PageSpeed client instance (singleton pattern)"""
    global _pagespeed_client
    
    if _pagespeed_client is None:
        _pagespeed_client = PageSpeedClient()
    
    return _pagespeed_client


async def assess_pagespeed(url: str, company: str = None, lead_id: int = None, assessment_id: int = None) -> Dict[str, Any]:
    """
    Convenience function for PageSpeed assessment with cost tracking
    
    Args:
        url: URL to analyze
        company: Optional company name for context
        lead_id: Optional lead ID for cost tracking
        assessment_id: Optional assessment ID for storing detailed results
        
    Returns:
        Dict containing assessment results for database storage
    """
    from src.core.database import get_db, AsyncSessionLocal
    from src.models.assessment_cost import AssessmentCost
    from src.models.pagespeed import (
        PageSpeedAnalysis, PageSpeedAudit, PageSpeedScreenshot,
        PageSpeedElement, PageSpeedEntity, PageSpeedOpportunity
    )
    
    cost_records = []
    
    try:
        client = get_pagespeed_client()
        
        # Mobile-first analysis per PRP-003
        results = await client.analyze_mobile_first(url)
        
        # Use mobile results as primary
        mobile_result = results["mobile"]
        desktop_result = results.get("desktop")
        
        # Create cost records for each API call
        if lead_id:
            for strategy, result in results.items():
                cost_record = AssessmentCost.create_pagespeed_cost(
                    lead_id=lead_id,
                    cost_cents=result.cost_cents,
                    response_status="success",
                    response_time_ms=result.analysis_duration_ms,
                    api_quota_used=False  # Assume paid tier for now
                )
                cost_records.append(cost_record)
        
        # Save detailed PageSpeed data to new tables if assessment_id provided
        if assessment_id:
            async with AsyncSessionLocal() as db:
                try:
                    await save_pagespeed_analysis_to_db(
                        db, assessment_id, mobile_result, desktop_result, cost_records
                    )
                    await db.commit()
                    logger.info(f"Saved detailed PageSpeed data for assessment {assessment_id}")
                except Exception as db_exc:
                    await db.rollback()
                    logger.error(f"Failed to save PageSpeed data to database: {db_exc}")
        
        # Prepare data for database storage (backward compatibility)
        assessment_data = {
            "url": url,
            "company": company,
            "mobile_analysis": mobile_result.dict(),
            "desktop_analysis": desktop_result.dict() if desktop_result else None,
            "primary_strategy": "mobile",
            "core_web_vitals": mobile_result.core_web_vitals.dict(),
            "performance_score": mobile_result.core_web_vitals.performance_score or 0,
            "analysis_timestamp": mobile_result.analysis_timestamp,
            "total_cost_cents": sum(r.cost_cents for r in results.values()),
            "api_calls_made": len(results),
            "cost_records": []  # Exclude SQLAlchemy objects to avoid serialization issues
        }
        
        return assessment_data
        
    except PageSpeedError as exc:
        # Create error cost record if lead_id provided
        if lead_id:
            error_cost = AssessmentCost.create_pagespeed_cost(
                lead_id=lead_id,
                cost_cents=0.0,  # No cost for failed requests
                response_status="error",
                error_code="pagespeed_api_error",
                error_message=str(exc)
            )
            cost_records.append(error_cost)
        
        logger.error(f"PageSpeed assessment failed", url=url, company=company, error=str(exc))
        raise
    except Exception as exc:
        # Create error cost record for unexpected errors
        if lead_id:
            error_cost = AssessmentCost.create_pagespeed_cost(
                lead_id=lead_id,
                cost_cents=0.0,
                response_status="error", 
                error_code="unexpected_error",
                error_message=str(exc)
            )
            cost_records.append(error_cost)
        
        logger.error(f"Unexpected error in PageSpeed assessment", url=url, error=str(exc))
        raise PageSpeedError(f"Assessment failed: {exc}")


async def save_pagespeed_analysis_to_db(
    db,
    assessment_id: int,
    mobile_result: PageSpeedResult,
    desktop_result: Optional[PageSpeedResult],
    cost_records: List[Any]
) -> None:
    """
    Save PageSpeed analysis results to the new database schema
    
    Args:
        db: Database session
        assessment_id: Assessment ID to link results to
        mobile_result: Mobile PageSpeed results
        desktop_result: Optional desktop PageSpeed results
        cost_records: Cost tracking records
    """
    from src.models.pagespeed import (
        PageSpeedAnalysis, PageSpeedAudit, PageSpeedScreenshot,
        PageSpeedElement, PageSpeedEntity, PageSpeedOpportunity
    )
    
    # Helper function to save analysis for a strategy
    async def save_strategy_analysis(result: PageSpeedResult, strategy: str):
        # Extract lighthouse result
        lighthouse = result.lighthouse_result
        
        # Create main analysis record
        analysis = PageSpeedAnalysis(
            assessment_id=assessment_id,
            url=result.url,
            strategy=strategy,
            analysis_timestamp=datetime.fromisoformat(result.analysis_timestamp),
            analysis_duration_ms=result.analysis_duration_ms,
            cost_cents=result.cost_cents,
            
            # URLs
            requested_url=lighthouse.get('requestedUrl'),
            final_url=lighthouse.get('finalUrl'),
            main_document_url=lighthouse.get('mainDocumentUrl'),
            final_displayed_url=lighthouse.get('finalDisplayedUrl'),
            
            # Core Web Vitals
            first_contentful_paint_ms=int(result.core_web_vitals.first_contentful_paint) if result.core_web_vitals.first_contentful_paint else None,
            largest_contentful_paint_ms=int(result.core_web_vitals.largest_contentful_paint) if result.core_web_vitals.largest_contentful_paint else None,
            cumulative_layout_shift=result.core_web_vitals.cumulative_layout_shift,
            total_blocking_time_ms=int(result.core_web_vitals.total_blocking_time) if result.core_web_vitals.total_blocking_time else None,
            time_to_interactive_ms=int(result.core_web_vitals.time_to_interactive) if result.core_web_vitals.time_to_interactive else None,
            performance_score=result.core_web_vitals.performance_score,
            
            # Category scores
            accessibility_score=extract_category_score(lighthouse, 'accessibility'),
            best_practices_score=extract_category_score(lighthouse, 'best-practices'),
            seo_score=extract_category_score(lighthouse, 'seo'),
            pwa_score=extract_category_score(lighthouse, 'pwa'),
            
            # Metadata
            lighthouse_version=lighthouse.get('lighthouseVersion'),
            user_agent=lighthouse.get('userAgent'),
            fetch_time=datetime.fromisoformat(lighthouse['fetchTime']) if lighthouse.get('fetchTime') else None,
            environment=lighthouse.get('environment'),
            config_settings=lighthouse.get('configSettings'),
            timing_total_ms=lighthouse.get('timing', {}).get('total'),
            
            # Benchmark and credits
            benchmark_index=lighthouse.get('benchmarkIndex'),
            credits=lighthouse.get('credits'),
            
            # Raw data
            raw_lighthouse_result=lighthouse,
            i18n_strings=lighthouse.get('i18n')
        )
        
        # Extract Speed Index if available
        audits = lighthouse.get('audits', {})
        if 'speed-index' in audits:
            analysis.speed_index_ms = int(audits['speed-index'].get('numericValue', 0))
        
        db.add(analysis)
        await db.flush()  # Get the ID
        
        # Save all audits
        for audit_id, audit_data in audits.items():
            audit = PageSpeedAudit(
                pagespeed_analysis_id=analysis.id,
                audit_id=audit_id,
                title=audit_data.get('title'),
                description=audit_data.get('description'),
                score=audit_data.get('score'),
                score_display_mode=audit_data.get('scoreDisplayMode'),
                display_value=audit_data.get('displayValue'),
                explanation=audit_data.get('explanation'),
                error_message=audit_data.get('errorMessage'),
                warnings=audit_data.get('warnings'),
                details=audit_data.get('details'),
                numeric_value=audit_data.get('numericValue'),
                numeric_unit=audit_data.get('numericUnit')
            )
            db.add(audit)
        
        # Save screenshots
        if 'audits' in lighthouse:
            # Full page screenshot
            if 'full-page-screenshot' in audits:
                screenshot_data = audits['full-page-screenshot'].get('details', {})
                if screenshot_data.get('screenshot'):
                    screenshot = PageSpeedScreenshot(
                        pagespeed_analysis_id=analysis.id,
                        screenshot_type='full_page',
                        data=screenshot_data['screenshot'].get('data'),
                        height=screenshot_data['screenshot'].get('height'),
                        width=screenshot_data['screenshot'].get('width'),
                        mime_type=screenshot_data['screenshot'].get('mimeType', 'image/webp')
                    )
                    db.add(screenshot)
            
            # Screenshot thumbnails from filmstrip
            if 'screenshot-thumbnails' in audits:
                filmstrip = audits['screenshot-thumbnails'].get('details', {}).get('items', [])
                for frame in filmstrip:
                    if frame.get('data'):
                        screenshot = PageSpeedScreenshot(
                            pagespeed_analysis_id=analysis.id,
                            screenshot_type='filmstrip',
                            data=frame.get('data'),
                            timestamp_ms=frame.get('timing'),
                            mime_type='image/jpeg'
                        )
                        db.add(screenshot)
        
        # Save element positioning data
        if 'full-page-screenshot' in audits:
            nodes = audits['full-page-screenshot'].get('details', {}).get('nodes', {})
            for node_id, node_data in nodes.items():
                element = PageSpeedElement(
                    pagespeed_analysis_id=analysis.id,
                    node_id=node_id,
                    selector=node_data.get('selector'),
                    snippet=node_data.get('snippet'),
                    bounding_rect=node_data.get('boundingRect'),
                    node_label=node_data.get('nodeLabel'),
                    element_type=node_data.get('type')
                )
                db.add(element)
        
        # Save third-party entities
        if 'third-party-summary' in audits:
            entities = audits['third-party-summary'].get('details', {}).get('items', [])
            for entity_data in entities:
                if entity_data.get('entity'):
                    entity_info = entity_data['entity']
                    entity = PageSpeedEntity(
                        pagespeed_analysis_id=analysis.id,
                        name=entity_info.get('text', entity_info.get('url', 'Unknown')),
                        homepage=entity_info.get('url'),
                        category=entity_data.get('category'),
                        is_first_party=entity_data.get('isFirstParty', False),
                        is_unrecognized=entity_data.get('isUnrecognized', False),
                        total_bytes=entity_data.get('transferSize'),
                        main_thread_time_ms=entity_data.get('mainThreadTime'),
                        blocking_time_ms=entity_data.get('blockingTime'),
                        transfer_size_bytes=entity_data.get('transferSize')
                    )
                    db.add(entity)
        
        # Save performance opportunities
        opportunities = []
        for audit_id, audit_data in audits.items():
            # Check if this audit represents an opportunity (has savings)
            details = audit_data.get('details', {})
            if details.get('type') == 'opportunity' and details.get('overallSavingsMs'):
                opportunity = PageSpeedOpportunity(
                    pagespeed_analysis_id=analysis.id,
                    audit_id=audit_id,
                    title=audit_data.get('title'),
                    description=audit_data.get('description'),
                    savings_ms=int(details.get('overallSavingsMs', 0)),
                    savings_bytes=int(details.get('overallSavingsBytes', 0)) if details.get('overallSavingsBytes') else None,
                    rating='fail' if audit_data.get('score', 1) < 0.5 else 'average' if audit_data.get('score', 1) < 0.9 else 'pass',
                    details=details
                )
                db.add(opportunity)
    
    # Save mobile analysis (always available)
    await save_strategy_analysis(mobile_result, 'mobile')
    
    # Save desktop analysis if available
    if desktop_result:
        await save_strategy_analysis(desktop_result, 'desktop')
    
    # Save cost records
    for cost_record in cost_records:
        db.add(cost_record)


def extract_category_score(lighthouse_result: Dict[str, Any], category: str) -> Optional[int]:
    """
    Extract category score from Lighthouse result
    
    Args:
        lighthouse_result: Lighthouse result data
        category: Category name (e.g., 'performance', 'accessibility')
        
    Returns:
        Score as integer (0-100) or None if not found
    """
    categories = lighthouse_result.get('categories', {})
    if category in categories:
        score = categories[category].get('score')
        if score is not None:
            return int(score * 100)
    return None
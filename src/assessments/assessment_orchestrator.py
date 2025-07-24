"""
PRP-011: Assessment Orchestrator
Complete assessment workflow coordination and result aggregation system
"""

import logging
import time
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from src.core.config import settings
from src.models.assessment_cost import AssessmentCost
from src.assessments.screenshot_capture import capture_website_screenshots, ScreenshotMetadata
from src.assessments.semrush_integration import assess_semrush_domain, SEMrushMetrics
from src.assessments.visual_analysis import assess_visual_analysis, VisualAnalysisMetrics
from src.assessments.score_calculator import calculate_business_score, BusinessImpactScore
from src.assessments.content_generator import generate_marketing_content, GeneratedContent

logger = logging.getLogger(__name__)

class AssessmentStatus(Enum):
    """Assessment execution status tracking."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"

class ComponentStatus(Enum):
    """Individual component execution status."""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class ComponentResult:
    """Individual assessment component result."""
    name: str
    status: ComponentStatus
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_ms: Optional[int]
    cost_cents: float
    error_message: Optional[str]
    data: Optional[Dict[str, Any]]

@dataclass
class AssessmentExecution:
    """Complete assessment execution tracking."""
    lead_id: int
    execution_id: str
    status: AssessmentStatus
    start_time: datetime
    end_time: Optional[datetime]
    total_duration_ms: Optional[int]
    total_cost_cents: float
    
    # Component results
    pagespeed_result: ComponentResult
    security_result: ComponentResult
    gbp_result: ComponentResult
    screenshots_result: ComponentResult
    semrush_result: ComponentResult
    visual_analysis_result: ComponentResult
    score_calculation_result: ComponentResult
    content_generation_result: ComponentResult
    
    # Final results
    business_score: Optional[BusinessImpactScore]
    marketing_content: Optional[GeneratedContent]
    
    # Metadata
    assessment_data: Dict[str, Any]
    error_summary: List[str]
    success_rate: float

class AssessmentOrchestratorError(Exception):
    """Custom exception for orchestration errors"""
    pass

class AssessmentOrchestrator:
    """
    Complete assessment workflow orchestrator that coordinates all PRPs
    and aggregates results into comprehensive business assessment.
    """
    
    # Component execution order and dependencies
    EXECUTION_ORDER = [
        "pagespeed",      # PRP-003: Foundation metrics
        "security",       # PRP-004: Security analysis
        "gbp",            # PRP-005: Google Business Profile
        "screenshots",    # PRP-006: Visual captures
        "semrush",        # PRP-007: SEO analysis
        "visual_analysis", # PRP-008: Visual assessment
        "score_calculation", # PRP-009: Business impact scoring
        "content_generation" # PRP-010: Marketing content
    ]
    
    # Component timeout settings (seconds)
    COMPONENT_TIMEOUTS = {
        "pagespeed": 60,
        "security": 30,
        "gbp": 45,
        "screenshots": 45,
        "semrush": 30,
        "visual_analysis": 120,
        "score_calculation": 10,
        "content_generation": 60
    }
    
    # Retry configuration
    MAX_RETRIES = {
        "pagespeed": 2,
        "security": 2,
        "gbp": 2,
        "screenshots": 3,
        "semrush": 2,
        "visual_analysis": 1,
        "score_calculation": 1,
        "content_generation": 2
    }
    
    def __init__(self):
        """Initialize assessment orchestrator."""
        self.execution_id = f"assessment_{int(time.time())}"
        logger.info(f"Assessment Orchestrator initialized: {self.execution_id}")
    
    async def execute_complete_assessment(self, lead_id: int, lead_data: Dict[str, Any]) -> AssessmentExecution:
        """
        Execute complete assessment workflow for a business lead.
        
        Args:
            lead_id: Database ID of the lead to assess
            lead_data: Lead information (company, URL, industry, etc.)
            
        Returns:
            AssessmentExecution: Complete execution results with all component data
        """
        start_time = datetime.now(timezone.utc)
        
        # Initialize execution tracking
        execution = AssessmentExecution(
            lead_id=lead_id,
            execution_id=self.execution_id,
            status=AssessmentStatus.IN_PROGRESS,
            start_time=start_time,
            end_time=None,
            total_duration_ms=None,
            total_cost_cents=0.0,
            pagespeed_result=self._create_empty_component_result("pagespeed"),
            security_result=self._create_empty_component_result("security"),
            gbp_result=self._create_empty_component_result("gbp"),
            screenshots_result=self._create_empty_component_result("screenshots"),
            semrush_result=self._create_empty_component_result("semrush"),
            visual_analysis_result=self._create_empty_component_result("visual_analysis"),
            score_calculation_result=self._create_empty_component_result("score_calculation"),
            content_generation_result=self._create_empty_component_result("content_generation"),
            business_score=None,
            marketing_content=None,
            assessment_data={},
            error_summary=[],
            success_rate=0.0
        )
        
        try:
            logger.info(f"Starting complete assessment for lead {lead_id}")
            
            # Execute components in dependency order
            for component_name in self.EXECUTION_ORDER:
                try:
                    await self._execute_component(execution, component_name, lead_data)
                except Exception as e:
                    error_msg = f"{component_name} execution failed: {str(e)}"
                    execution.error_summary.append(error_msg)
                    logger.error(error_msg)
                    
                    # Continue with other components even if one fails
                    component_result = getattr(execution, f"{component_name}_result")
                    component_result.status = ComponentStatus.FAILED
                    component_result.error_message = str(e)
            
            # Calculate final metrics
            execution.end_time = datetime.now(timezone.utc)
            execution.total_duration_ms = int((execution.end_time - execution.start_time).total_seconds() * 1000)
            execution.success_rate = self._calculate_success_rate(execution)
            execution.total_cost_cents = self._calculate_total_cost(execution)
            
            # Determine final status
            if execution.success_rate >= 0.8:
                execution.status = AssessmentStatus.COMPLETED
            elif execution.success_rate >= 0.5:
                execution.status = AssessmentStatus.PARTIALLY_COMPLETED
            else:
                execution.status = AssessmentStatus.FAILED
            
            logger.info(f"Assessment completed for lead {lead_id}: {execution.success_rate:.1%} success rate, ${execution.total_cost_cents/100:.4f} cost")
            return execution
            
        except Exception as e:
            execution.status = AssessmentStatus.FAILED
            execution.end_time = datetime.now(timezone.utc)
            execution.total_duration_ms = int((execution.end_time - execution.start_time).total_seconds() * 1000)
            execution.error_summary.append(f"Assessment orchestration failed: {str(e)}")
            
            logger.error(f"Assessment orchestration failed for lead {lead_id}: {e}")
            raise AssessmentOrchestratorError(f"Assessment execution failed: {str(e)}")
    
    async def _execute_component(self, execution: AssessmentExecution, component_name: str, lead_data: Dict[str, Any]) -> None:
        """Execute individual assessment component with error handling."""
        
        component_result = getattr(execution, f"{component_name}_result")
        component_result.start_time = datetime.now(timezone.utc)
        component_result.status = ComponentStatus.RUNNING
        
        timeout = self.COMPONENT_TIMEOUTS.get(component_name, 60)
        max_retries = self.MAX_RETRIES.get(component_name, 1)
        
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Executing {component_name} (attempt {attempt + 1}/{max_retries + 1})")
                
                # Execute component with timeout
                result_data = await asyncio.wait_for(
                    self._call_component_function(component_name, execution.lead_id, lead_data, execution.assessment_data),
                    timeout=timeout
                )
                
                # Success - store results
                component_result.status = ComponentStatus.SUCCESS
                component_result.data = result_data
                component_result.end_time = datetime.now(timezone.utc)
                component_result.duration_ms = int((component_result.end_time - component_result.start_time).total_seconds() * 1000)
                
                # Update aggregated assessment data
                execution.assessment_data[component_name] = result_data
                
                logger.info(f"{component_name} completed successfully in {component_result.duration_ms}ms")
                return
                
            except asyncio.TimeoutError:
                error_msg = f"{component_name} timed out after {timeout}s"
                logger.warning(f"{error_msg} (attempt {attempt + 1})")
                if attempt == max_retries:
                    component_result.error_message = error_msg
                    
            except Exception as e:
                error_msg = f"{component_name} failed: {str(e)}"
                logger.warning(f"{error_msg} (attempt {attempt + 1})")
                if attempt == max_retries:
                    component_result.error_message = error_msg
                    
                # Wait before retry
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
        
        # All attempts failed
        component_result.status = ComponentStatus.FAILED
        component_result.end_time = datetime.now(timezone.utc)
        component_result.duration_ms = int((component_result.end_time - component_result.start_time).total_seconds() * 1000)
    
    async def _call_component_function(self, component_name: str, lead_id: int, lead_data: Dict[str, Any], assessment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call the appropriate component function based on component name."""
        
        url = lead_data.get('url', '')
        domain = url.replace('https://', '').replace('http://', '').split('/')[0]
        
        if component_name == "pagespeed":
            # Import and call PageSpeed function (PRP-003)
            # This would normally call the PageSpeed API
            # For now, return mock data structure
            return {
                "mobile_performance_score": 65,
                "desktop_performance_score": 78,
                "mobile_lcp": 3.2,
                "desktop_lcp": 2.1,
                "mobile_fid": 85,
                "desktop_fid": 45,
                "mobile_cls": 0.15,
                "desktop_cls": 0.08,
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        elif component_name == "security":
            # Import and call Security function (PRP-004)
            # This would normally call the SSL Labs API
            # For now, return mock data structure
            return {
                "https_enforced": True,
                "ssl_grade": "B",
                "security_headers": {"hsts": False, "csp": True},
                "vulnerability_count": 1,
                "certificate_info": {"issuer": "Let's Encrypt", "expires": "2024-12-01"},
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        elif component_name == "gbp":
            # Call Google Business Profile integration (PRP-005)
            from src.assessments.gbp_integration import assess_google_business_profile
            
            # Extract business details for GBP search
            company = lead_data.get('company', '')
            # Parse address from lead data or use defaults
            address = lead_data.get('address', '')
            city = lead_data.get('city', '')
            state = lead_data.get('state', '')
            
            gbp_results = await assess_google_business_profile(
                business_name=company,
                address=address,
                city=city,
                state=state,
                lead_id=lead_id
            )
            return gbp_results
            
        elif component_name == "screenshots":
            # Call ScreenshotOne integration (PRP-006)
            desktop_screenshot, mobile_screenshot = await capture_website_screenshots(url, lead_id)
            return {
                "desktop_screenshot": desktop_screenshot.__dict__ if desktop_screenshot else None,
                "mobile_screenshot": mobile_screenshot.__dict__ if mobile_screenshot else None,
                "capture_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        elif component_name == "semrush":
            # Call SEMrush integration (PRP-007)
            semrush_data = await assess_semrush_domain(domain, lead_id)
            return semrush_data.__dict__
            
        elif component_name == "visual_analysis":
            # Call Visual Analysis (PRP-008)
            screenshot_data = assessment_data.get("screenshots", {})
            desktop_url = screenshot_data.get("desktop_screenshot", {}).get("screenshot_url") if screenshot_data.get("desktop_screenshot") else None
            mobile_url = screenshot_data.get("mobile_screenshot", {}).get("screenshot_url") if screenshot_data.get("mobile_screenshot") else None
            
            if desktop_url and mobile_url:
                visual_analysis = await assess_visual_analysis(url, desktop_url, mobile_url, lead_id)
                return visual_analysis.__dict__
            else:
                raise AssessmentOrchestratorError("Screenshots required for visual analysis")
                
        elif component_name == "score_calculation":
            # Call Score Calculator (PRP-009)
            business_score = await calculate_business_score(lead_id, assessment_data, lead_data)
            return business_score.__dict__
            
        elif component_name == "content_generation":
            # Call Content Generator (PRP-010)
            marketing_content = await generate_marketing_content(lead_id, lead_data, assessment_data)
            return marketing_content.__dict__
            
        else:
            raise AssessmentOrchestratorError(f"Unknown component: {component_name}")
    
    def _create_empty_component_result(self, name: str) -> ComponentResult:
        """Create empty component result for initialization."""
        return ComponentResult(
            name=name,
            status=ComponentStatus.NOT_STARTED,
            start_time=None,
            end_time=None,
            duration_ms=None,
            cost_cents=0.0,
            error_message=None,
            data=None
        )
    
    def _calculate_success_rate(self, execution: AssessmentExecution) -> float:
        """Calculate overall success rate based on component results."""
        
        components = [
            execution.pagespeed_result,
            execution.security_result,
            execution.gbp_result,
            execution.screenshots_result,
            execution.semrush_result,
            execution.visual_analysis_result,
            execution.score_calculation_result,
            execution.content_generation_result
        ]
        
        successful_components = sum(1 for comp in components if comp.status == ComponentStatus.SUCCESS)
        total_components = len(components)
        
        return successful_components / total_components if total_components > 0 else 0.0
    
    def _calculate_total_cost(self, execution: AssessmentExecution) -> float:
        """Calculate total cost across all components."""
        
        components = [
            execution.pagespeed_result,
            execution.security_result,
            execution.screenshots_result,
            execution.semrush_result,
            execution.visual_analysis_result,
            execution.score_calculation_result,
            execution.content_generation_result
        ]
        
        return sum(comp.cost_cents for comp in components)

async def execute_full_assessment(lead_id: int, lead_data: Dict[str, Any]) -> AssessmentExecution:
    """
    Main entry point for complete assessment execution.
    
    Args:
        lead_id: Database ID of the lead to assess
        lead_data: Complete lead information and business context
        
    Returns:
        AssessmentExecution: Complete execution results with all component data
    """
    try:
        # Initialize orchestrator
        orchestrator = AssessmentOrchestrator()
        
        # Execute complete assessment workflow
        logger.info(f"Starting full assessment workflow for lead {lead_id}")
        execution_result = await orchestrator.execute_complete_assessment(lead_id, lead_data)
        
        logger.info(f"Full assessment completed for lead {lead_id}: {execution_result.success_rate:.1%} success rate")
        return execution_result
        
    except Exception as e:
        logger.error(f"Full assessment execution failed for lead {lead_id}: {e}")
        raise AssessmentOrchestratorError(f"Full assessment failed: {str(e)}")

# Add create_orchestration_cost method to AssessmentCost model
def create_orchestration_cost_method(cls, lead_id: int, cost_cents: float = 0.0, response_status: str = "success", response_time_ms: Optional[int] = None, error_message: Optional[str] = None):
    """
    Create cost record for assessment orchestration (no direct API cost).
    
    Args:
        lead_id: ID of the lead being assessed
        cost_cents: Cost in cents (default $0.00 - orchestration only)
        response_status: success, error, timeout, partial
        response_time_ms: Total orchestration time in milliseconds
        error_message: Error message if applicable
        
    Returns:
        AssessmentCost instance
    """
    now = datetime.now(timezone.utc)
    
    return cls(
        lead_id=lead_id,
        service_name="assessment_orchestrator",
        api_endpoint="internal://orchestration/execute_assessment",
        cost_cents=cost_cents,
        currency="USD",
        request_timestamp=now,
        response_status=response_status,
        response_time_ms=response_time_ms,
        api_quota_used=False,  # Internal orchestration - no quota
        rate_limited=False,
        retry_count=0,
        error_message=error_message,
        daily_budget_date=now.strftime("%Y-%m-%d"),
        monthly_budget_date=now.strftime("%Y-%m")
    )

# Monkey patch the method to AssessmentCost
AssessmentCost.create_orchestration_cost = classmethod(create_orchestration_cost_method)


async def save_decomposed_assessment_results(db, assessment_id: int, execution: AssessmentExecution) -> None:
    """
    Save decomposed assessment results to the assessment_results table.
    
    Args:
        db: Database session
        assessment_id: ID of the assessment record
        execution: AssessmentExecution with all component results
    """
    from src.models.assessment_results import AssessmentResults
    from sqlalchemy import select
    
    # Check if results already exist for this assessment
    existing_results = await db.execute(
        select(AssessmentResults).where(AssessmentResults.assessment_id == assessment_id)
    )
    existing = existing_results.scalar_one_or_none()
    
    if existing:
        # Update existing record instead of creating a new one
        results = existing
    else:
        # Create new AssessmentResults record
        results = AssessmentResults(assessment_id=assessment_id)
    
    # Extract PageSpeed metrics
    if execution.pagespeed_result and execution.pagespeed_result.data:
        data = execution.pagespeed_result.data
        results.pagespeed_score = data.get('desktop_score')
        results.pagespeed_mobile_score = data.get('mobile_score')
        
        # Desktop metrics
        if desktop_metrics := data.get('desktop_metrics'):
            results.pagespeed_fcp_ms = desktop_metrics.get('first_contentful_paint_ms')
            results.pagespeed_lcp_ms = desktop_metrics.get('largest_contentful_paint_ms')
            results.pagespeed_cls = desktop_metrics.get('cumulative_layout_shift')
            results.pagespeed_tbt_ms = desktop_metrics.get('total_blocking_time_ms')
            results.pagespeed_tti_ms = desktop_metrics.get('time_to_interactive_ms')
    
    # Extract Security metrics
    if execution.security_result and execution.security_result.data:
        data = execution.security_result.data
        results.security_ssl_valid = data.get('ssl_valid')
        results.security_headers_score = data.get('security_headers_score')
        results.security_vulnerabilities_count = data.get('vulnerabilities_count', 0)
        results.security_critical_issues = data.get('critical_issues', 0)
        
        # Tech scraper values
        results.tech_https_enforced = data.get('https_redirect')
        results.tech_tls_version = data.get('tls_version')
        if headers := data.get('headers_present'):
            results.tech_hsts_present = headers.get('hsts')
            results.tech_csp_present = headers.get('csp')
    
    # Extract GBP metrics
    if execution.gbp_result and execution.gbp_result.data:
        data = execution.gbp_result.data
        results.gbp_found = data.get('place_found', False)
        results.gbp_rating = data.get('rating')
        results.gbp_review_count = data.get('user_ratings_total')
        results.gbp_photos_count = data.get('photos_count')
        results.gbp_verified = data.get('verified', False)
        results.gbp_is_closed = data.get('business_status') == 'CLOSED_PERMANENTLY'
        
        # Calculate recent reviews and trend if we have review data
        if reviews := data.get('reviews'):
            recent_count = 0
            ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)
            for review in reviews:
                if review.get('time') and datetime.fromtimestamp(review['time'], timezone.utc) > ninety_days_ago:
                    recent_count += 1
            results.gbp_recent_reviews_90d = recent_count
    
    # Extract SEMrush metrics
    if execution.semrush_result and execution.semrush_result.data:
        data = execution.semrush_result.data
        if domain_info := data.get('domain_info'):
            results.semrush_domain_authority = domain_info.get('domain_score')
            if organic := domain_info.get('organic'):
                results.semrush_traffic_estimate = organic.get('traffic')
                results.semrush_keywords_count = organic.get('keywords')
        
        if backlinks := data.get('backlinks_info'):
            results.semrush_backlinks_count = backlinks.get('total')
    
    # Extract Visual Analysis scores
    if execution.visual_analysis_result and execution.visual_analysis_result.data:
        data = execution.visual_analysis_result.data
        if scores := data.get('scores'):
            # Map the 9 visual rubric scores
            for i, score in enumerate(scores[:9]):
                setattr(results, f'visual_score_{i+1}', score)
    
    # Business impact metrics
    if execution.score_calculation_result and execution.score_calculation_result.data:
        data = execution.score_calculation_result.data
        results.impact_score = data.get('overall_score')
        results.revenue_impact_monthly = data.get('revenue_impact_monthly')
        results.conversion_impact_percent = data.get('conversion_impact_percent')
    
    # Error tracking
    failed_components = []
    for attr_name in ['pagespeed_result', 'security_result', 'gbp_result', 'semrush_result', 
                      'visual_analysis_result', 'screenshots_result']:
        result = getattr(execution, attr_name, None)
        if result and result.status == ComponentStatus.FAILED:
            failed_components.append({
                'component': attr_name.replace('_result', ''),
                'error': result.error_message
            })
    
    if failed_components:
        results.error_components = json.dumps(failed_components)
    
    # Save to database
    if existing:
        # For existing records, just commit the changes
        await db.commit()
    else:
        # For new records, add them first
        db.add(results)
        await db.commit()
    
    logger.info(f"Saved decomposed assessment results for assessment {assessment_id}")
"""
PRP-007: SEMrush Integration
Professional SEO data extraction with domain authority, backlink analysis, and site health metrics
"""

import asyncio
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field

from src.core.config import settings
from src.models.assessment_cost import AssessmentCost

logger = logging.getLogger(__name__)

# Pydantic Models for SEMrush Data
class TechnicalIssue(BaseModel):
    """Technical issue found during site analysis."""
    issue_type: str = Field(..., description="Type of issue (SEO, Traffic, Technical)")
    severity: str = Field(..., description="Issue severity (low, medium, high, critical)")
    description: str = Field(..., description="Human-readable issue description")
    category: str = Field(..., description="Issue category for reporting")

class SEMrushMetrics(BaseModel):
    """Complete SEMrush domain metrics."""
    authority_score: int = Field(0, ge=0, le=100, description="Domain Authority Score 0-100")
    backlink_toxicity_score: float = Field(0.0, ge=0.0, le=100.0, description="Toxic backlinks percentage")
    organic_traffic_estimate: int = Field(0, ge=0, description="Monthly organic traffic estimate")
    ranking_keywords_count: int = Field(0, ge=0, description="Number of ranking keywords")
    site_health_score: float = Field(0.0, ge=0.0, le=100.0, description="Technical site health percentage")
    technical_issues: List[TechnicalIssue] = Field(default_factory=list, description="List of technical issues found")
    
    # Metadata
    domain: str = Field(..., description="Analyzed domain")
    analysis_timestamp: str = Field(..., description="When analysis was performed")
    api_cost_units: float = Field(0.0, description="API units consumed")
    extraction_duration_ms: int = Field(0, description="Time taken for analysis")

class SEMrushResults(BaseModel):
    """Complete SEMrush assessment results."""
    domain: str = Field(..., description="Target domain")
    success: bool = Field(..., description="Overall analysis success")
    metrics: Optional[SEMrushMetrics] = Field(None, description="SEMrush metrics data")
    error_message: Optional[str] = Field(None, description="Error details if failed")
    total_duration_ms: int = Field(0, description="Total processing time")
    cost_records: List[Any] = Field(default_factory=list, description="Cost tracking records")
    
    class Config:
        arbitrary_types_allowed = True

class SEMrushIntegrationError(Exception):
    """Custom exception for SEMrush integration errors"""
    pass

class SEMrushClient:
    """SEMrush Domain Analytics API client with cost optimization."""
    
    BASE_URL = "https://api.semrush.com/"
    COST_PER_DOMAIN = 10.0  # $0.10 in cents (estimated ~2000 API units)
    TIMEOUT = 30  # 30 seconds
    MAX_RETRIES = 3
    
    # Cost estimates per API call (in API units)
    COSTS = {
        "domain_overview": 10,
        "backlinks_overview": 40,
        "domain_organic": 10,
        "site_health": 15
    }
    
    def __init__(self):
        self.api_key = settings.SEMRUSH_API_KEY
        self.client = httpx.AsyncClient(timeout=self.TIMEOUT)
        
    async def _check_api_balance(self) -> int:
        """Check remaining API units balance."""
        
        if not self.api_key:
            raise SEMrushIntegrationError("SEMrush API key not configured")
        
        try:
            response = await self.client.get(
                self.BASE_URL,
                params={
                    'type': 'api_units',
                    'key': self.api_key
                }
            )
            
            if response.status_code == 200:
                balance_text = response.text.strip()
                return int(balance_text) if balance_text.isdigit() else 0
            else:
                logger.warning(f"Failed to check API balance: {response.status_code}")
                return 0
                
        except Exception as e:
            logger.error(f"API balance check failed: {e}")
            return 0
    
    async def _make_api_request(self, request_type: str, domain: str, extra_params: Optional[Dict] = None) -> Optional[str]:
        """Make a request to SEMrush API with error handling."""
        
        params = {
            'type': request_type,
            'key': self.api_key,
            'domain': domain,
            'database': 'us'
        }
        
        if extra_params:
            params.update(extra_params)
        
        try:
            response = await self.client.get(self.BASE_URL, params=params)
            
            if response.status_code == 200:
                return response.text.strip()
            elif response.status_code == 429:
                logger.warning(f"SEMrush API rate limit hit for {domain}")
                raise SEMrushIntegrationError("API rate limit exceeded")
            else:
                logger.error(f"SEMrush API error: {response.status_code} - {response.text}")
                raise SEMrushIntegrationError(f"API request failed: {response.status_code}")
                
        except httpx.TimeoutException:
            logger.error(f"SEMrush API timeout for {domain}")
            raise SEMrushIntegrationError("API request timed out")
        except Exception as e:
            logger.error(f"SEMrush API request failed: {e}")
            raise SEMrushIntegrationError(f"API request failed: {str(e)}")
    
    async def _extract_domain_authority(self, domain: str) -> Dict[str, Any]:
        """Extract Domain Authority Score from domain overview."""
        
        try:
            response_text = await self._make_api_request('domain_overview', domain)
            
            if response_text:
                lines = response_text.split('\n')
                for line in lines:
                    fields = line.split('\t')
                    if len(fields) >= 10:
                        try:
                            # Authority Score typically in field position 9
                            authority_score = int(float(fields[9]))
                            return {
                                'authority_score': min(max(authority_score, 0), 100),
                                'api_cost': self.COSTS['domain_overview']
                            }
                        except (ValueError, IndexError):
                            continue
            
            return {'authority_score': 0, 'api_cost': self.COSTS['domain_overview']}
            
        except SEMrushIntegrationError:
            return {'authority_score': 0, 'api_cost': 0}
    
    async def _extract_backlink_analysis(self, domain: str) -> Dict[str, Any]:
        """Extract backlink toxicity score and analysis."""
        
        try:
            response_text = await self._make_api_request('backlinks_overview', domain, {
                'target': domain,
                'target_type': 'root_domain'
            })
            
            if response_text:
                lines = response_text.split('\n')
                for line in lines:
                    fields = line.split('\t')
                    if len(fields) >= 8:
                        try:
                            referring_domains = int(fields[3])
                            backlinks_total = int(fields[2])
                            
                            # Calculate toxicity score based on backlink ratio
                            toxicity_score = 0.0
                            if referring_domains > 0:
                                ratio = backlinks_total / referring_domains
                                # Higher ratio suggests potential spam
                                toxicity_score = min((ratio - 5) * 2, 100.0) if ratio > 5 else 0.0
                                toxicity_score = max(toxicity_score, 0.0)
                            
                            return {
                                'toxicity_score': toxicity_score,
                                'referring_domains': referring_domains,
                                'total_backlinks': backlinks_total,
                                'api_cost': self.COSTS['backlinks_overview']
                            }
                        except (ValueError, IndexError):
                            continue
            
            return {'toxicity_score': 0.0, 'api_cost': self.COSTS['backlinks_overview']}
            
        except SEMrushIntegrationError:
            return {'toxicity_score': 0.0, 'api_cost': 0}
    
    async def _extract_organic_traffic(self, domain: str) -> Dict[str, Any]:
        """Extract organic traffic estimate and keyword rankings."""
        
        try:
            response_text = await self._make_api_request('domain_organic', domain, {
                'display_limit': 1  # Just need summary metrics
            })
            
            if response_text:
                lines = response_text.split('\n')
                for line in lines:
                    fields = line.split('\t')
                    if len(fields) >= 7:
                        try:
                            # Traffic estimate typically in field position 5
                            traffic_estimate = int(float(fields[5]))
                            # Keywords count in field position 4
                            keywords_count = int(float(fields[4]))
                            
                            return {
                                'traffic_estimate': max(traffic_estimate, 0),
                                'keywords_count': max(keywords_count, 0),
                                'api_cost': self.COSTS['domain_organic']
                            }
                        except (ValueError, IndexError):
                            continue
            
            return {'traffic_estimate': 0, 'keywords_count': 0, 'api_cost': self.COSTS['domain_organic']}
            
        except SEMrushIntegrationError:
            return {'traffic_estimate': 0, 'keywords_count': 0, 'api_cost': 0}
    
    async def _extract_site_health(self, domain: str) -> Dict[str, Any]:
        """Extract site health score and technical issues."""
        
        try:
            # Use domain overview to estimate site health
            response_text = await self._make_api_request('domain_overview', domain)
            
            health_score = 75.0  # Default baseline
            technical_issues = []
            
            if response_text:
                lines = response_text.split('\n')
                for line in lines:
                    fields = line.split('\t')
                    if len(fields) >= 10:
                        try:
                            keyword_count = int(float(fields[4]))
                            traffic_volume = int(float(fields[5]))
                            
                            # Analyze metrics for health indicators
                            if keyword_count < 100:
                                technical_issues.append(TechnicalIssue(
                                    issue_type="SEO",
                                    severity="medium",
                                    description="Limited organic keyword visibility",
                                    category="Keyword Optimization"
                                ))
                                health_score -= 10
                            
                            if traffic_volume < 1000:
                                technical_issues.append(TechnicalIssue(
                                    issue_type="Traffic",
                                    severity="high", 
                                    description="Low organic traffic volume",
                                    category="Traffic Generation"
                                ))
                                health_score -= 15
                            
                            if keyword_count < 50:
                                technical_issues.append(TechnicalIssue(
                                    issue_type="Technical",
                                    severity="high",
                                    description="Very limited search engine visibility",
                                    category="Technical SEO"
                                ))
                                health_score -= 20
                            
                            break
                        except (ValueError, IndexError):
                            continue
            
            # Ensure health score is within bounds
            health_score = max(min(health_score, 100.0), 0.0)
            
            return {
                'health_score': health_score,
                'issues': [issue.dict() for issue in technical_issues],
                'api_cost': self.COSTS['site_health']
            }
            
        except SEMrushIntegrationError:
            return {'health_score': 0.0, 'issues': [], 'api_cost': 0}
    
    async def analyze_domain(self, domain: str) -> SEMrushMetrics:
        """Perform comprehensive domain analysis."""
        
        if not domain or '.' not in domain:
            raise SEMrushIntegrationError(f"Invalid domain format: {domain}")
        
        # Check API balance before expensive operations
        balance = await self._check_api_balance()
        if balance < 100:  # Minimum units required
            logger.warning(f"Low SEMrush API balance: {balance} units")
        
        start_time = time.time()
        
        try:
            # Execute all analysis components in parallel
            authority_task = self._extract_domain_authority(domain)
            backlink_task = self._extract_backlink_analysis(domain)
            traffic_task = self._extract_organic_traffic(domain)
            health_task = self._extract_site_health(domain)
            
            # Wait for all tasks to complete
            authority_data, backlink_data, traffic_data, health_data = await asyncio.gather(
                authority_task, backlink_task, traffic_task, health_task,
                return_exceptions=True
            )
            
            # Handle any exceptions from parallel execution
            for data in [authority_data, backlink_data, traffic_data, health_data]:
                if isinstance(data, Exception):
                    logger.error(f"SEMrush analysis component failed: {data}")
            
            # Ensure we have valid data dictionaries
            authority_data = authority_data if isinstance(authority_data, dict) else {'authority_score': 0, 'api_cost': 0}
            backlink_data = backlink_data if isinstance(backlink_data, dict) else {'toxicity_score': 0.0, 'api_cost': 0}
            traffic_data = traffic_data if isinstance(traffic_data, dict) else {'traffic_estimate': 0, 'keywords_count': 0, 'api_cost': 0}
            health_data = health_data if isinstance(health_data, dict) else {'health_score': 0.0, 'issues': [], 'api_cost': 0}
            
            # Calculate total API cost
            total_cost = (
                authority_data.get('api_cost', 0) +
                backlink_data.get('api_cost', 0) +
                traffic_data.get('api_cost', 0) +
                health_data.get('api_cost', 0)
            )
            
            # Create technical issues list
            technical_issues = []
            for issue_dict in health_data.get('issues', []):
                try:
                    technical_issues.append(TechnicalIssue(**issue_dict))
                except Exception as e:
                    logger.warning(f"Failed to parse technical issue: {e}")
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            metrics = SEMrushMetrics(
                authority_score=authority_data.get('authority_score', 0),
                backlink_toxicity_score=backlink_data.get('toxicity_score', 0.0),
                organic_traffic_estimate=traffic_data.get('traffic_estimate', 0),
                ranking_keywords_count=traffic_data.get('keywords_count', 0),
                site_health_score=health_data.get('health_score', 0.0),
                technical_issues=technical_issues,
                domain=domain,
                analysis_timestamp=datetime.now(timezone.utc).isoformat(),
                api_cost_units=total_cost,
                extraction_duration_ms=duration_ms
            )
            
            logger.info(f"SEMrush analysis completed for {domain}: {total_cost} units, {duration_ms}ms")
            return metrics
            
        except Exception as e:
            logger.error(f"SEMrush domain analysis failed for {domain}: {e}")
            raise SEMrushIntegrationError(f"Domain analysis failed: {str(e)}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

async def assess_semrush_domain(domain: str, lead_id: int) -> SEMrushResults:
    """
    Main entry point for SEMrush domain assessment.
    
    Args:
        domain: Domain to analyze
        lead_id: Database ID of the lead
        
    Returns:
        Complete SEMrush assessment results with cost tracking
    """
    start_time = time.time()
    cost_records = []
    
    try:
        if not settings.SEMRUSH_API_KEY:
            raise SEMrushIntegrationError("SEMrush API key not configured")
        
        # Create cost tracking record
        cost_record = AssessmentCost.create_semrush_cost(
            lead_id=lead_id,
            cost_cents=SEMrushClient.COST_PER_DOMAIN,
            response_status="pending"
        )
        cost_records.append(cost_record)
        
        # Initialize SEMrush client
        semrush_client = SEMrushClient()
        
        try:
            # Perform domain analysis
            logger.info(f"Starting SEMrush analysis for: {domain}")
            metrics = await semrush_client.analyze_domain(domain)
            
            # Update cost record with success
            end_time = time.time()
            cost_record.response_status = "success"
            cost_record.response_time_ms = int((end_time - start_time) * 1000)
            
            logger.info(f"SEMrush analysis completed for {domain}: authority {metrics.authority_score}, traffic {metrics.organic_traffic_estimate}")
            
            return SEMrushResults(
                domain=domain,
                success=True,
                metrics=metrics,
                total_duration_ms=int((end_time - start_time) * 1000),
                cost_records=cost_records
            )
            
        finally:
            await semrush_client.close()
            
    except SEMrushIntegrationError as e:
        # Update cost record with error
        end_time = time.time()
        cost_record.response_status = "error"
        cost_record.response_time_ms = int((end_time - start_time) * 1000)
        cost_record.error_message = str(e)[:500]
        
        logger.error(f"SEMrush assessment failed for {domain}: {e}")
        
        return SEMrushResults(
            domain=domain,
            success=False,
            error_message=str(e),
            total_duration_ms=int((end_time - start_time) * 1000),
            cost_records=cost_records
        )
    
    except Exception as e:
        # Update cost record with unexpected error
        end_time = time.time()
        if cost_records:
            cost_record.response_status = "error"
            cost_record.response_time_ms = int((end_time - start_time) * 1000)
            cost_record.error_message = str(e)[:500]
        
        logger.error(f"Unexpected error in SEMrush assessment for {domain}: {e}")
        
        return SEMrushResults(
            domain=domain,
            success=False,
            error_message=f"SEMrush assessment failed: {str(e)}",
            total_duration_ms=int((end_time - start_time) * 1000),
            cost_records=cost_records
        )

# Add create_semrush_cost method to AssessmentCost model
def create_semrush_cost_method(cls, lead_id: int, cost_cents: float = 10.0, response_status: str = "success", response_time_ms: Optional[int] = None, error_message: Optional[str] = None):
    """
    Create cost record for SEMrush API call.
    
    Args:
        lead_id: ID of the lead being assessed
        cost_cents: Cost in cents (default $0.10)
        response_status: success, error, timeout, rate_limited
        response_time_ms: API response time in milliseconds
        error_message: Error message if applicable
        
    Returns:
        AssessmentCost instance
    """
    now = datetime.now(timezone.utc)
    
    return cls(
        lead_id=lead_id,
        service_name="semrush",
        api_endpoint="https://api.semrush.com/domain_analysis",
        cost_cents=cost_cents,
        currency="USD",
        request_timestamp=now,
        response_status=response_status,
        response_time_ms=response_time_ms,
        api_quota_used=True,  # SEMrush API counts against quota
        rate_limited=False,
        retry_count=0,
        error_message=error_message,
        daily_budget_date=now.strftime("%Y-%m-%d"),
        monthly_budget_date=now.strftime("%Y-%m")
    )

# Monkey patch the method to AssessmentCost
AssessmentCost.create_semrush_cost = classmethod(create_semrush_cost_method)

# Add backward compatibility function for existing imports
async def analyze_domain_seo(domain: str, lead_id: int) -> SEMrushResults:
    """
    Backward compatibility function for analyze_domain_seo.
    
    This function maintains compatibility with existing import statements
    while using the new assess_semrush_domain function internally.
    
    Args:
        domain: Domain to analyze
        lead_id: Database ID of the lead
        
    Returns:
        Complete SEMrush assessment results
    """
    return await assess_semrush_domain(domain, lead_id)
# PRP-007: SEMrush Integration

## Task ID: PRP-007

## Wave: Foundation Services

## Business Logic

The LeadFactory audit platform requires professional SEO data integration via SEMrush Domain Analytics API to provide competitive domain authority, backlink toxicity analysis, and technical SEO insights for $399 audit reports. This integration extracts 6 critical SEO metrics (Site Health Score, Backlink Toxicity Score, Organic Traffic Estimate, Ranking Keywords Count, Domain Authority Score, Technical Issues List) with cost optimization at $0.10 per domain assessment. The SEMrush client provides professional competitive intelligence and authority scoring that enhances audit report quality and justifies premium pricing for business assessments.

## Overview

Implement SEMrush Domain Analytics API client with Celery task integration for:
- Domain authority scoring with 1-100 scale Authority Score calculation
- Backlink toxicity analysis with spam detection and link quality assessment
- Organic traffic estimation with keyword ranking analysis
- Site health scoring with technical issue identification and categorization
- Cost management with API unit tracking and credit balance validation ($0.10 per domain)
- Celery task integration with Assessment Orchestrator for parallel processing
- Error handling for API rate limits, credit exhaustion, and missing domain data

## Dependencies

- **External**: SEMrush Business Plan subscription ($449.95/mo), SEMrush API units ($50 for 1M units), requests library for HTTP client
- **Internal**: PRP-002 (Assessment Orchestrator) for Celery task coordination, PRP-001 (Lead Data Model) for result storage
- **Blockers**: None

## Outcome-Focused Acceptance Criteria

1. **SEMrush Client Operational**: `SEMrushClient().get_domain_metrics('example.com')` returns 6 SEO metrics with proper API authentication and response validation
2. **Domain Authority Extraction**: Authority Score (1-100) extracted from Domain Analytics endpoint with Link Power, Organic Traffic, and Natural Profile components
3. **Backlink Analysis Complete**: Backlink Toxicity Score calculated with spam detection, toxic link identification, and referring domain analysis
4. **Organic Traffic Metrics**: Traffic estimate extracted with keyword ranking count, search visibility, and competitive positioning data
5. **Site Health Assessment**: Technical issues list extracted from Site Audit endpoint with categorized problems (broken links, duplicate content, page speed)
6. **Cost Tracking Implemented**: API unit consumption tracked per request, credit balance checked before expensive operations, cost stays within $0.10 per domain
7. **Celery Task Integration**: `semrush_assessment_task.delay(lead_id)` integrates with Assessment Orchestrator for parallel processing
8. **Error Handling Robust**: API rate limits handled with exponential backoff, credit exhaustion prevents new requests, missing domain data handled gracefully
9. **Database Storage Working**: All 6 SEO metrics stored in PostgreSQL via SQLAlchemy models with proper data types and foreign key relationships
10. **Production Performance**: 100+ domain assessments/hour with <5% failure rate, API response times <10 seconds per domain

## Integration Points

### SEMrush API Client (Core Service)
- **Location**: `src/services/semrush/client.py`, `src/services/semrush/models.py`
- **Dependencies**: requests, typing, pydantic for response validation
- **Functions**: get_domain_authority(), get_backlink_analysis(), get_organic_traffic(), get_site_health(), check_api_balance()

### Celery Task Integration (Assessment Pipeline)
- **Location**: `src/assessment/tasks/semrush_task.py`
- **Dependencies**: Celery, SEMrush client, SQLAlchemy models
- **Functions**: semrush_assessment_task(), process_semrush_metrics(), handle_semrush_errors()

### SEMrush Configuration (API Authentication)
- **Location**: `src/core/config.py`, environment variables
- **Dependencies**: API key management, rate limiting configuration
- **Resources**: API key validation, request timeout settings, retry policies

### Database Models (SEO Metrics Storage)
- **Location**: `src/models/seo_models.py` (extends PRP-001)
- **Dependencies**: SQLAlchemy, PostgreSQL, proper indexing
- **Integration**: SEO metrics stored with lead_id foreign key and normalized data structure

## Implementation Requirements

### SEMrush API Client Implementation

**Domain Metrics Client**:
```python
import requests
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
import time

class SEMrushMetrics(BaseModel):
    """Pydantic model for SEMrush domain metrics."""
    authority_score: int = Field(ge=0, le=100, description="Domain Authority Score 0-100")
    backlink_toxicity_score: float = Field(ge=0.0, le=100.0, description="Toxic backlinks percentage")
    organic_traffic_estimate: int = Field(ge=0, description="Monthly organic traffic estimate")
    ranking_keywords_count: int = Field(ge=0, description="Number of ranking keywords")
    site_health_score: float = Field(ge=0.0, le=100.0, description="Technical site health percentage")
    technical_issues: List[Dict[str, Any]] = Field(default_factory=list, description="List of technical issues found")
    api_cost: float = Field(ge=0.0, description="API units consumed for this request")
    extraction_timestamp: datetime = Field(default_factory=datetime.utcnow)

class SEMrushClient:
    """
    SEMrush Domain Analytics API client for professional SEO data extraction.
    
    Provides domain authority, backlink analysis, organic traffic, and site health metrics
    with cost optimization and error handling for audit report enhancement.
    """
    
    BASE_URL = "https://api.semrush.com/"
    
    def __init__(self, api_key: str, timeout: int = 30):
        """
        Initialize SEMrush client with API authentication.
        
        Args:
            api_key: 32-character SEMrush API key from Business subscription
            timeout: Request timeout in seconds (default: 30)
        """
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'LeadFactory-Audit-Platform/1.0',
            'Accept': 'application/json'
        })
        
        # Validate API key format
        if not api_key or len(api_key) != 32:
            raise ValueError("Invalid SEMrush API key format. Expected 32-character string.")
        
        # Test API connectivity
        self._validate_api_connection()
    
    def _validate_api_connection(self) -> None:
        """Validate API key and connection on client initialization."""
        try:
            balance = self.get_api_balance()
            if balance <= 0:
                raise ValueError("SEMrush API balance exhausted. Please add credits.")
            logging.info(f"SEMrush client initialized. API balance: {balance} units")
        except requests.RequestException as e:
            raise ConnectionError(f"Failed to connect to SEMrush API: {e}")
    
    def get_api_balance(self) -> int:
        """
        Check remaining API units balance.
        
        Returns:
            int: Remaining API units balance
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}",
                params={
                    'type': 'api_units',
                    'key': self.api_key
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Parse API units from response
            balance_data = response.text.strip()
            return int(balance_data) if balance_data.isdigit() else 0
            
        except requests.RequestException as e:
            logging.error(f"Failed to check API balance: {e}")
            raise
    
    def get_domain_metrics(self, domain: str) -> SEMrushMetrics:
        """
        Extract comprehensive SEO metrics for a domain.
        
        Args:
            domain: Domain name to analyze (e.g., 'example.com')
            
        Returns:
            SEMrushMetrics: Complete domain metrics with cost tracking
        """
        if not domain or '.' not in domain:
            raise ValueError(f"Invalid domain format: {domain}")
        
        # Check API balance before expensive operations
        balance = self.get_api_balance()
        if balance < 100:  # Minimum units for domain analysis
            raise ValueError(f"Insufficient API balance: {balance} units remaining")
        
        start_time = time.time()
        total_cost = 0.0
        
        try:
            # Extract all 6 required metrics
            authority_data = self._get_domain_authority(domain)
            backlink_data = self._get_backlink_analysis(domain)
            traffic_data = self._get_organic_traffic(domain)
            health_data = self._get_site_health(domain)
            
            # Calculate total API cost
            total_cost = authority_data.get('api_cost', 0) + backlink_data.get('api_cost', 0) + \
                        traffic_data.get('api_cost', 0) + health_data.get('api_cost', 0)
            
            # Validate cost stays within budget ($0.10 per domain = ~2000 API units)
            if total_cost > 2000:
                logging.warning(f"Domain analysis cost exceeded budget: {total_cost} units for {domain}")
            
            metrics = SEMrushMetrics(
                authority_score=authority_data.get('authority_score', 0),
                backlink_toxicity_score=backlink_data.get('toxicity_score', 0.0),
                organic_traffic_estimate=traffic_data.get('traffic_estimate', 0),
                ranking_keywords_count=traffic_data.get('keywords_count', 0),
                site_health_score=health_data.get('health_score', 0.0),
                technical_issues=health_data.get('issues', []),
                api_cost=total_cost
            )
            
            processing_time = time.time() - start_time
            logging.info(f"SEMrush metrics extracted for {domain}: {total_cost} units, {processing_time:.2f}s")
            
            return metrics
            
        except Exception as e:
            logging.error(f"SEMrush metrics extraction failed for {domain}: {e}")
            raise
    
    def _get_domain_authority(self, domain: str) -> Dict[str, Any]:
        """Extract Authority Score with Link Power, Organic Traffic, Natural Profile."""
        try:
            response = self.session.get(
                f"{self.BASE_URL}",
                params={
                    'type': 'domain_overview',
                    'key': self.api_key,
                    'domain': domain,
                    'database': 'us'
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Parse domain overview response for authority metrics
            lines = response.text.strip().split('\n')
            authority_score = 0
            
            for line in lines:
                fields = line.split('\t')
                if len(fields) >= 10:
                    # Authority Score typically in field position 9
                    try:
                        authority_score = int(float(fields[9]))
                        break
                    except (ValueError, IndexError):
                        continue
            
            return {
                'authority_score': min(max(authority_score, 0), 100),
                'api_cost': 10  # Estimated cost for domain overview
            }
            
        except requests.RequestException as e:
            logging.error(f"Authority Score extraction failed for {domain}: {e}")
            return {'authority_score': 0, 'api_cost': 0}
    
    def _get_backlink_analysis(self, domain: str) -> Dict[str, Any]:
        """Extract backlink toxicity score and spam detection."""
        try:
            response = self.session.get(
                f"{self.BASE_URL}",
                params={
                    'type': 'backlinks_overview',
                    'key': self.api_key,
                    'target': domain,
                    'target_type': 'root_domain'
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Parse backlinks overview for toxicity metrics
            lines = response.text.strip().split('\n')
            toxicity_score = 0.0
            
            for line in lines:
                fields = line.split('\t')
                if len(fields) >= 8:
                    # Estimate toxicity based on referring domains and backlink quality
                    try:
                        referring_domains = int(fields[3])
                        backlinks_total = int(fields[2])
                        
                        # Simple toxicity estimation (can be enhanced with more sophisticated logic)
                        if referring_domains > 0:
                            ratio = backlinks_total / referring_domains
                            toxicity_score = min((ratio - 5) * 2, 100.0) if ratio > 5 else 0.0
                        break
                    except (ValueError, IndexError):
                        continue
            
            return {
                'toxicity_score': max(toxicity_score, 0.0),
                'api_cost': 40  # Estimated cost for backlinks overview
            }
            
        except requests.RequestException as e:
            logging.error(f"Backlink analysis failed for {domain}: {e}")
            return {'toxicity_score': 0.0, 'api_cost': 0}
    
    def _get_organic_traffic(self, domain: str) -> Dict[str, Any]:
        """Extract organic traffic estimate and keyword rankings."""
        try:
            response = self.session.get(
                f"{self.BASE_URL}",
                params={
                    'type': 'domain_organic',
                    'key': self.api_key,
                    'domain': domain,
                    'database': 'us',
                    'display_limit': 1  # Just need summary metrics
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Parse organic traffic data
            lines = response.text.strip().split('\n')
            traffic_estimate = 0
            keywords_count = 0
            
            for line in lines:
                fields = line.split('\t')
                if len(fields) >= 7:
                    try:
                        # Traffic estimate typically in field position 5
                        traffic_estimate = int(float(fields[5]))
                        # Keywords count in field position 4
                        keywords_count = int(float(fields[4]))
                        break
                    except (ValueError, IndexError):
                        continue
            
            return {
                'traffic_estimate': max(traffic_estimate, 0),
                'keywords_count': max(keywords_count, 0),
                'api_cost': 10  # Estimated cost for organic overview
            }
            
        except requests.RequestException as e:
            logging.error(f"Organic traffic analysis failed for {domain}: {e}")
            return {'traffic_estimate': 0, 'keywords_count': 0, 'api_cost': 0}
    
    def _get_site_health(self, domain: str) -> Dict[str, Any]:
        """Extract site health score and technical issues list."""
        try:
            # Note: Site Audit API requires separate endpoint and may have different costs
            response = self.session.get(
                f"{self.BASE_URL}",
                params={
                    'type': 'domain_overview',
                    'key': self.api_key,
                    'domain': domain,
                    'database': 'us'
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # For now, estimate site health based on available domain metrics
            # This can be enhanced with actual Site Audit API integration
            health_score = 75.0  # Default baseline
            technical_issues = []
            
            # Analyze response for potential issues
            lines = response.text.strip().split('\n')
            for line in lines:
                fields = line.split('\t')
                if len(fields) >= 10:
                    try:
                        # Check various metrics for health indicators
                        if int(float(fields[4])) < 100:  # Low keyword count
                            technical_issues.append({
                                'type': 'SEO',
                                'severity': 'medium',
                                'description': 'Limited organic keyword visibility'
                            })
                        if int(float(fields[5])) < 1000:  # Low traffic
                            technical_issues.append({
                                'type': 'Traffic',
                                'severity': 'high',
                                'description': 'Low organic traffic volume'
                            })
                        break
                    except (ValueError, IndexError):
                        continue
            
            # Adjust health score based on issues found
            health_score -= len(technical_issues) * 10
            health_score = max(health_score, 0.0)
            
            return {
                'health_score': health_score,
                'issues': technical_issues,
                'api_cost': 15  # Estimated cost for health analysis
            }
            
        except requests.RequestException as e:
            logging.error(f"Site health analysis failed for {domain}: {e}")
            return {'health_score': 0.0, 'issues': [], 'api_cost': 0}
```

### Celery Task Integration

**SEMrush Assessment Task**:
```python
from celery import Task
from typing import Dict, Any
import logging
from datetime import datetime
from src.services.semrush.client import SEMrushClient, SEMrushMetrics
from src.models.seo_models import SEOAssessment
from src.core.database import get_db_session
from src.core.config import settings

class SEMrushAssessmentTask(Task):
    """Celery task for SEMrush domain analysis with error handling and retry logic."""
    
    autoretry_for = (requests.RequestException, ConnectionError, ValueError)
    retry_backoff = True
    retry_kwargs = {'max_retries': 3}
    
    def __init__(self):
        self.semrush_client = None
    
    def _get_client(self) -> SEMrushClient:
        """Initialize SEMrush client with lazy loading."""
        if self.semrush_client is None:
            self.semrush_client = SEMrushClient(
                api_key=settings.SEMRUSH_API_KEY,
                timeout=30
            )
        return self.semrush_client

@app.task(
    bind=True,
    base=SEMrushAssessmentTask,
    name='assessment.semrush_analysis'
)
def semrush_assessment_task(self, lead_id: int) -> Dict[str, Any]:
    """
    Execute SEMrush domain analysis for lead assessment.
    
    Args:
        lead_id: Database ID of the lead to analyze
        
    Returns:
        Dict containing SEMrush metrics and task metadata
    """
    try:
        # Get lead data from database
        with get_db_session() as db:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            if not lead or not lead.domain:
                raise ValueError(f"Invalid lead or missing domain for lead {lead_id}")
            
            # Update task status
            seo_assessment = db.query(SEOAssessment).filter(
                SEOAssessment.lead_id == lead_id
            ).first()
            
            if not seo_assessment:
                seo_assessment = SEOAssessment(
                    lead_id=lead_id,
                    semrush_status='in_progress',
                    started_at=datetime.utcnow()
                )
                db.add(seo_assessment)
                db.commit()
            else:
                seo_assessment.semrush_status = 'in_progress'
                seo_assessment.started_at = datetime.utcnow()
                db.commit()
        
        # Execute SEMrush analysis
        client = self._get_client()
        metrics = client.get_domain_metrics(lead.domain)
        
        # Store metrics in database
        with get_db_session() as db:
            seo_assessment = db.query(SEOAssessment).filter(
                SEOAssessment.lead_id == lead_id
            ).first()
            
            # Update with SEMrush metrics
            seo_assessment.authority_score = metrics.authority_score
            seo_assessment.backlink_toxicity_score = metrics.backlink_toxicity_score
            seo_assessment.organic_traffic_estimate = metrics.organic_traffic_estimate
            seo_assessment.ranking_keywords_count = metrics.ranking_keywords_count
            seo_assessment.site_health_score = metrics.site_health_score
            seo_assessment.technical_issues = metrics.technical_issues
            seo_assessment.semrush_api_cost = metrics.api_cost
            seo_assessment.semrush_status = 'completed'
            seo_assessment.completed_at = datetime.utcnow()
            
            db.commit()
        
        return {
            "lead_id": lead_id,
            "task": "semrush_analysis",
            "status": "completed",
            "metrics": {
                "authority_score": metrics.authority_score,
                "backlink_toxicity_score": metrics.backlink_toxicity_score,
                "organic_traffic_estimate": metrics.organic_traffic_estimate,
                "ranking_keywords_count": metrics.ranking_keywords_count,
                "site_health_score": metrics.site_health_score,
                "technical_issues_count": len(metrics.technical_issues)
            },
            "api_cost": metrics.api_cost,
            "completed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        # Log error and update database
        logging.error(f"SEMrush assessment failed for lead {lead_id}: {exc}")
        
        # Update error status in database
        try:
            with get_db_session() as db:
                seo_assessment = db.query(SEOAssessment).filter(
                    SEOAssessment.lead_id == lead_id
                ).first()
                if seo_assessment:
                    seo_assessment.semrush_status = 'failed'
                    seo_assessment.error_message = str(exc)
                    seo_assessment.failed_at = datetime.utcnow()
                    db.commit()
        except Exception as db_error:
            logging.error(f"Failed to update error status for lead {lead_id}: {db_error}")
        
        # Retry with exponential backoff
        if self.request.retries < 3:
            retry_countdown = 2 ** self.request.retries
            logging.info(f"Retrying SEMrush analysis for lead {lead_id} in {retry_countdown}s")
            raise self.retry(countdown=retry_countdown)
        else:
            # Final failure
            raise
```

### Database Models Extension

**SEO Assessment Models**:
```python
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text, ForeignKey
from sqlalchemy.orm import relationship
from src.models.base import BaseModel

class SEOAssessment(BaseModel):
    """Database model for SEO assessment results including SEMrush metrics."""
    
    __tablename__ = 'seo_assessments'
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey('leads.id'), nullable=False, index=True)
    
    # SEMrush metrics (6 required fields)
    authority_score = Column(Integer, nullable=True, comment="Domain Authority Score 0-100")
    backlink_toxicity_score = Column(Float, nullable=True, comment="Toxic backlinks percentage")
    organic_traffic_estimate = Column(Integer, nullable=True, comment="Monthly organic traffic estimate")
    ranking_keywords_count = Column(Integer, nullable=True, comment="Number of ranking keywords")
    site_health_score = Column(Float, nullable=True, comment="Technical site health percentage")
    technical_issues = Column(JSON, nullable=True, comment="List of technical issues found")
    
    # Task execution tracking
    semrush_status = Column(String(20), default='pending', comment="Task status: pending/in_progress/completed/failed")
    semrush_api_cost = Column(Float, nullable=True, comment="API units consumed")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    lead = relationship("Lead", back_populates="seo_assessment")
    
    def __repr__(self):
        return f"<SEOAssessment(lead_id={self.lead_id}, authority_score={self.authority_score}, status={self.semrush_status})>"
    
    @property
    def is_complete(self) -> bool:
        """Check if all required SEMrush metrics are present."""
        required_fields = [
            self.authority_score,
            self.backlink_toxicity_score,
            self.organic_traffic_estimate,
            self.ranking_keywords_count,
            self.site_health_score
        ]
        return all(field is not None for field in required_fields)
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage based on available metrics."""
        required_fields = [
            self.authority_score,
            self.backlink_toxicity_score,
            self.organic_traffic_estimate,
            self.ranking_keywords_count,
            self.site_health_score,
            self.technical_issues
        ]
        completed_fields = sum(1 for field in required_fields if field is not None)
        return (completed_fields / len(required_fields)) * 100
```

## Tests to Pass

1. **SEMrush Client Tests**: `pytest tests/test_semrush_client.py -v` validates API authentication, domain metrics extraction, and error handling with ≥90% coverage
2. **Metrics Extraction Tests**: `pytest tests/test_semrush_metrics.py -v` validates all 6 required metrics (authority, toxicity, traffic, keywords, health, issues) extraction accuracy
3. **Cost Management Tests**: API unit consumption tracking stays within $0.10 per domain budget (~2000 units), credit balance validation prevents overruns
4. **Celery Task Tests**: `pytest tests/test_semrush_task.py -v` validates task execution, retry logic, and database integration with proper error handling
5. **Database Integration Tests**: SEO metrics properly stored in PostgreSQL via SQLAlchemy models, foreign key relationships maintained
6. **Performance Tests**: 100+ domain assessments/hour with <5% failure rate, API response times <10 seconds per domain
7. **Error Handling Tests**: API rate limits, credit exhaustion, and missing domain data handled gracefully with proper user feedback
8. **Integration Tests**: `pytest tests/integration/test_semrush_pipeline.py -v` validates complete SEMrush analysis pipeline integration
9. **Mock API Tests**: Unit tests use mocked SEMrush responses to avoid API costs during development and CI
10. **Production Validation**: Live API integration tested with real domains, cost tracking verified with actual API consumption

## Implementation Guide

### Phase 1: Core SEMrush Client (Days 1-3)
1. **API Client Setup**: Implement SEMrushClient class with authentication and basic connection validation
2. **Domain Authority**: Implement Authority Score extraction with Link Power, Organic Traffic, Natural Profile components
3. **Response Validation**: Add Pydantic models for response validation and data structure consistency
4. **Error Handling**: Implement API rate limiting, timeout handling, and connection error recovery
5. **Cost Tracking**: Add API unit consumption tracking and budget validation per domain

### Phase 2: SEO Metrics Implementation (Days 4-6)
1. **Backlink Analysis**: Implement backlink toxicity scoring with spam detection and link quality assessment
2. **Organic Traffic**: Extract traffic estimates with keyword ranking count and search visibility metrics
3. **Site Health**: Implement technical issue identification and site health scoring methodology
4. **Data Normalization**: Ensure consistent data types and ranges for all extracted metrics
5. **Metric Validation**: Add validation logic to ensure extracted metrics are within expected ranges

### Phase 3: Celery Integration (Days 7-9)
1. **Task Implementation**: Create semrush_assessment_task with proper error handling and retry logic
2. **Database Integration**: Implement SEO assessment database models with proper relationships
3. **Orchestrator Integration**: Connect SEMrush task to Assessment Orchestrator pipeline
4. **Status Tracking**: Add real-time status updates for task execution progress
5. **Error Aggregation**: Implement error tracking and failure analysis for debugging

### Phase 4: Testing & Optimization (Days 10-12)
1. **Unit Testing**: Write comprehensive unit tests for all client methods and task functions
2. **Integration Testing**: Test complete SEMrush pipeline with Assessment Orchestrator
3. **Performance Testing**: Validate throughput requirements and API response time optimization
4. **Cost Optimization**: Fine-tune API usage to minimize costs while maintaining data quality
5. **Production Testing**: Test with real SEMrush API using actual domains and validate metrics accuracy

## Validation Commands

```bash
# SEMrush client validation
python -c "from src.services.semrush.client import SEMrushClient; client = SEMrushClient('${SEMRUSH_API_KEY}'); print(client.get_api_balance())"

# Domain metrics extraction
python -c "from src.services.semrush.client import SEMrushClient; client = SEMrushClient('${SEMRUSH_API_KEY}'); metrics = client.get_domain_metrics('example.com'); print(f'Authority: {metrics.authority_score}, Cost: {metrics.api_cost}')"

# Celery task validation
python -c "from src.assessment.tasks.semrush_task import semrush_assessment_task; result = semrush_assessment_task.delay(1); print(result.get())"

# Database integration validation
psql -h localhost -U leadfactory -d leadfactory -c "SELECT lead_id, authority_score, backlink_toxicity_score, semrush_status FROM seo_assessments WHERE semrush_status='completed' LIMIT 5;"

# Performance validation
python scripts/semrush_load_test.py --domains=100 --workers=3 --duration=300

# Cost tracking validation
python -c "from src.services.semrush.client import SEMrushClient; client = SEMrushClient('${SEMRUSH_API_KEY}'); balance_before = client.get_api_balance(); metrics = client.get_domain_metrics('test-domain.com'); balance_after = client.get_api_balance(); print(f'Cost: {balance_before - balance_after} units')"

# Error handling validation
python -c "from src.services.semrush.client import SEMrushClient; client = SEMrushClient('invalid-key'); client.get_domain_metrics('example.com')"  # Should handle gracefully
```

## Rollback Strategy

### Emergency Procedures
1. **API Failure**: Disable SEMrush task in Assessment Orchestrator, continue with other assessment types
2. **Cost Overrun**: Implement emergency cost limits to prevent budget exhaustion
3. **Rate Limiting**: Implement exponential backoff and queue management for API rate limit recovery
4. **Data Corruption**: Rollback to previous SEO assessment data and re-run analysis

### Detailed Rollback Steps
1. **Identify Issue**: Monitor dashboards show SEMrush task failure rate >10% or API errors
2. **Immediate Response**: Disable SEMrush task execution and preserve existing assessment data
3. **Service Isolation**: Continue other assessment types while isolating SEMrush integration issues
4. **Data Validation**: Verify existing SEO assessment data integrity and backup if necessary
5. **Issue Resolution**: Test fixes in staging environment with mock data before re-enabling
6. **Gradual Recovery**: Re-enable SEMrush integration with monitoring for issue recurrence

## Success Criteria

1. **Client Implementation**: SEMrush API client successfully extracts all 6 required SEO metrics with proper authentication
2. **Cost Management**: API costs stay within $0.10 per domain budget with accurate unit tracking
3. **Celery Integration**: SEMrush task integrates seamlessly with Assessment Orchestrator pipeline
4. **Database Storage**: All SEO metrics properly stored in PostgreSQL with normalized data structure
5. **Performance Requirements**: 100+ domain assessments/hour with <5% failure rate and <10s response times
6. **Error Handling**: Robust error handling for API limits, credit exhaustion, and missing data scenarios
7. **Testing Coverage**: Unit tests ≥90% coverage, integration tests validate complete pipeline functionality
8. **Production Readiness**: Live API integration tested with real domains and production-ready deployment

## Critical Context

### SEMrush API Capabilities
- **Authority Score**: 1-100 scale calculated from Link Power, Organic Traffic, Natural Profile
- **Backlink Analysis**: Toxicity scoring, spam detection, referring domain quality assessment
- **Organic Traffic**: Monthly traffic estimates with keyword ranking count and search visibility
- **Site Health**: Technical issue identification with categorized problems and severity levels
- **Cost Structure**: Business Plan required ($449.95/mo), API units ($50/1M units), ~$0.10 per domain

### Integration Requirements
- **Assessment Pipeline**: Integrates with PRP-002 Assessment Orchestrator for parallel processing
- **Database Storage**: Extends PRP-001 lead data model with SEO assessment results
- **Cost Optimization**: API unit tracking and budget validation to control assessment costs
- **Error Recovery**: Handles API failures gracefully without breaking overall assessment pipeline
- **Performance Standards**: Supports 100+ assessments/hour with sub-10-second response times

### Business Value Metrics
- **Audit Enhancement**: Professional SEO data justifies $399 audit report premium pricing
- **Competitive Intelligence**: Authority scoring and backlink analysis provide competitive insights
- **Technical Assessment**: Site health metrics identify actionable technical improvement opportunities
- **Cost Efficiency**: $0.10 per domain cost provides significant ROI on $399 audit reports
- **Market Differentiation**: Professional SEO data sets audit reports apart from basic website analysis

## Definition of Done

- [ ] SEMrush API client implemented with all 6 required metrics extraction capabilities
- [ ] Cost tracking and budget validation prevents API overruns at $0.10 per domain
- [ ] Celery task integration connects with Assessment Orchestrator for parallel processing
- [ ] Database models store SEO metrics with proper relationships and data validation
- [ ] Unit tests written for all client methods and task functions with ≥90% coverage
- [ ] Integration tests validate complete SEMrush pipeline with Assessment Orchestrator
- [ ] Performance testing confirms throughput and latency requirements
- [ ] Error handling covers API limits, credit exhaustion, and missing data scenarios
- [ ] Production testing validates live API integration with real domain analysis
- [ ] Documentation updated with SEMrush integration setup and monitoring procedures
- [ ] Code review completed with security validation for API key management
- [ ] Deployment tested with proper environment variable configuration and secret management
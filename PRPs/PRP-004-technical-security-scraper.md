# PRP-004: Technical/Security Scraper

## Task ID: PRP-004

## Wave: Foundation Infrastructure

## Business Logic

The LeadFactory system requires a technical security scraper service to extract critical security headers, SEO signals, and JavaScript errors from business websites to generate comprehensive $399 audit reports. This scraper performs security vulnerability assessment by analyzing HTTPS enforcement, TLS version detection, security headers (HSTS, CSP, X-Frame-Options), robots.txt/sitemap.xml presence, and JavaScript console errors. The scraper integrates with the assessment orchestrator to provide technical security data that directly impacts business value by identifying vulnerabilities, SEO issues, and technical problems that affect website performance and security posture.

## Overview

Implement Playwright-based technical security scraper with BeautifulSoup DOM parsing for:
- Security header extraction (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy) 
- HTTPS enforcement detection with TLS version analysis (1.2+ required)
- SEO signal detection (robots.txt presence, sitemap.xml presence, file sizes)
- JavaScript console error capture with classification (errors vs warnings)
- Memory-efficient browser automation with 15-second timeout limits
- Celery task integration with retry logic for transient network failures
- Assessment result storage in typed schema for audit report generation

## Dependencies

- **External**: Playwright Python library, BeautifulSoup4 for DOM parsing, browser automation dependencies
- **Internal**: PRP-002 (Assessment Orchestrator) for task coordination and retry logic, PRP-001 (Lead Data Model) for result storage
- **Blockers**: None

## Outcome-Focused Acceptance Criteria

1. **Security Headers Extraction**: All 6 security headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy) extracted from HTTP response headers with case-insensitive matching
2. **HTTPS Enforcement Detection**: TLS version detection via response.security_details(), HTTPS scheme validation, HSTS header analysis with max-age parsing
3. **SEO Signals Captured**: robots.txt and sitemap.xml presence detection with HTTP status codes (200=present, 404=missing), file size measurement in bytes
4. **JavaScript Error Collection**: Console message capture with error/warning classification, source file attribution, first 10 errors stored for memory efficiency
5. **Memory Management**: Browser process memory usage <200MB per assessment, proper page.close() and browser.close() cleanup after each task
6. **Timeout Enforcement**: 15-second hard timeout for all operations, graceful failure handling for slow-loading sites
7. **Celery Integration**: Task decorated with retry logic (3 attempts max), exponential backoff for network failures, JSON-serializable results
8. **Result Schema Validation**: Assessment results match typed schema with security_headers, https_enforcement, seo_signals, javascript_errors fields
9. **SSL Failure Handling**: Graceful handling of SSL certificate errors, invalid certificates, and connection failures without task crashes  
10. **Performance Monitoring**: Assessment completion within 15 seconds for 90% of sites, memory cleanup validation, task success rate >95%

## Integration Points

### Technical Security Scraper Core (Playwright Automation)
- **Location**: `src/assessment/services/technical_scraper.py`, `src/assessment/scrapers/security_analyzer.py`
- **Dependencies**: Playwright, BeautifulSoup, asyncio, SSL certificate validation
- **Functions**: scrape_technical_data(), extract_security_headers(), analyze_https_enforcement(), detect_seo_signals(), capture_js_errors()

### Browser Automation Engine (Memory-Optimized Playwright)
- **Location**: `src/assessment/scrapers/browser_manager.py`, `src/assessment/scrapers/page_analyzer.py`
- **Dependencies**: Playwright browser instances, resource monitoring, timeout management
- **Functions**: create_optimized_browser(), analyze_page_technical(), cleanup_browser_resources()

### Security Analysis Components (OWASP-Compliant)
- **Location**: `src/assessment/analyzers/security_headers.py`, `src/assessment/analyzers/tls_analyzer.py`
- **Dependencies**: HTTP header parsing, SSL/TLS validation, OWASP security standards
- **Functions**: parse_security_headers(), validate_tls_version(), assess_https_enforcement()

### Assessment Result Schema (Typed Data Models)  
- **Location**: `src/models/technical_assessment_models.py` (extends PRP-001)
- **Dependencies**: Pydantic models, SQLAlchemy integration, JSON serialization
- **Integration**: Typed schemas for security headers, HTTPS data, SEO signals, JS errors

## Implementation Requirements

### Playwright Technical Scraper Implementation

**Core Scraper Task**:
```python
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from celery import Celery
from typing import Dict, Any, Optional, List
import asyncio
import time
import logging
from datetime import datetime

app = Celery('technical_scraper')

@app.task(
    bind=True,
    autoretry_for=(PlaywrightTimeout, asyncio.TimeoutError, Exception),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={'max_retries': 3}
)
def scrape_technical_security(self, lead_id: int, url: str) -> Dict[str, Any]:
    """
    Extract technical security data from business website.
    
    Args:
        lead_id: Database ID of the lead being assessed
        url: Target website URL for analysis
        
    Returns:
        Dict containing security headers, HTTPS data, SEO signals, JS errors
    """
    try:
        # Run async scraper in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            scrape_technical_data_async(url, timeout=15000)
        )
        
        # Update assessment in database
        update_technical_assessment(lead_id, result)
        
        return {
            "lead_id": lead_id,
            "url": url,
            "status": "completed",
            "data": result,
            "completed_at": datetime.utcnow().isoformat(),
            "memory_usage_mb": result.get("performance_metrics", {}).get("memory_usage_mb", 0)
        }
        
    except Exception as exc:
        logger.error(f"Technical scraping failed for lead {lead_id}, URL {url}: {exc}")
        
        if self.request.retries < 3:
            raise self.retry(countdown=2**self.request.retries)
        else:
            update_assessment_error(lead_id, f"Technical scraper: {str(exc)}")
            return {
                "lead_id": lead_id,
                "url": url, 
                "status": "failed",
                "error": str(exc),
                "completed_at": datetime.utcnow().isoformat()
            }
    finally:
        loop.close()

async def scrape_technical_data_async(url: str, timeout: int = 15000) -> Dict[str, Any]:
    """
    Asynchronous technical data extraction with memory optimization.
    
    Args:
        url: Target website URL
        timeout: Maximum time in milliseconds for operations
        
    Returns:
        Complete technical assessment data
    """
    # Memory-optimized browser configuration
    browser_args = [
        '--no-sandbox',
        '--disable-dev-shm-usage', 
        '--disable-gpu',
        '--memory-pressure-off',
        '--max_old_space_size=200'  # Limit to 200MB
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=browser_args
        )
        
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='LeadFactory-Security-Scanner/1.0'
        )
        
        try:
            page = await context.new_page()
            
            # Set navigation timeout
            page.set_default_timeout(timeout)
            
            # Resource optimization - block non-essential resources
            await page.route('**/*.{png,jpg,jpeg,gif,webp,svg,mp4,mp3,pdf,woff,woff2}', 
                            lambda route: route.abort())
            
            # JavaScript error collection
            js_errors = []
            def handle_console_message(msg):
                if msg.type in ['error', 'warning']:
                    js_errors.append({
                        'type': msg.type,
                        'text': msg.text,
                        'location': getattr(msg, 'location', None),
                        'timestamp': time.time()
                    })
            
            page.on('console', handle_console_message)
            
            # Navigate to target URL
            response = await page.goto(url, wait_until='domcontentloaded')
            
            # Extract comprehensive technical data
            technical_data = {
                'security_headers': await extract_security_headers(response),
                'https_enforcement': await analyze_https_enforcement(response, page.url),
                'seo_signals': await detect_seo_signals(page, url),
                'javascript_errors': {
                    'error_count': len([e for e in js_errors if e['type'] == 'error']),
                    'warning_count': len([e for e in js_errors if e['type'] == 'warning']),
                    'details': js_errors[:10]  # Limit for memory efficiency
                },
                'performance_metrics': {
                    'load_time_ms': int((time.time() * 1000) % 1000000),
                    'memory_usage_mb': 0  # Would need process monitoring
                }
            }
            
            return technical_data
            
        finally:
            await context.close()
            await browser.close()
```

### Security Headers Analysis Implementation

**OWASP-Compliant Security Header Extraction**:
```python
async def extract_security_headers(response) -> Dict[str, Optional[str]]:
    """
    Extract all OWASP-recommended security headers from HTTP response.
    
    Args:
        response: Playwright response object
        
    Returns:
        Dict mapping security header types to values
    """
    # OWASP 2024 critical security headers
    SECURITY_HEADERS = {
        'Strict-Transport-Security': 'hsts',
        'Content-Security-Policy': 'csp', 
        'X-Frame-Options': 'x_frame_options',
        'X-Content-Type-Options': 'x_content_type_options',
        'Referrer-Policy': 'referrer_policy',
        'Permissions-Policy': 'permissions_policy'
    }
    
    security_data = {}
    
    # Extract each security header with case-insensitive matching
    for header_name, key in SECURITY_HEADERS.items():
        header_value = response.header_value(header_name)
        security_data[key] = header_value if header_value else None
    
    return security_data

async def analyze_https_enforcement(response, current_url: str) -> Dict[str, Any]:
    """
    Analyze HTTPS enforcement and TLS configuration.
    
    Args:
        response: Playwright response object
        current_url: Final URL after redirects
        
    Returns:
        HTTPS enforcement analysis data
    """
    https_data = {
        'scheme': current_url.split('://')[0],
        'enforced': False,
        'tls_version': None,
        'hsts_enabled': False,
        'certificate_valid': False
    }
    
    # Check if final URL uses HTTPS
    https_data['enforced'] = current_url.startswith('https://')
    
    # Extract TLS version from security details
    security_details = response.security_details()
    if security_details:
        https_data['tls_version'] = security_details.get('protocol')
        https_data['certificate_valid'] = True
        
        # Validate TLS version (1.2+ required)
        if https_data['tls_version']:
            version_num = float(https_data['tls_version'].split()[-1]) if 'TLS' in https_data['tls_version'] else 0
            https_data['tls_version_secure'] = version_num >= 1.2
    
    # Check HSTS header
    hsts_header = response.header_value('Strict-Transport-Security')
    if hsts_header:
        https_data['hsts_enabled'] = True
        https_data['hsts_config'] = hsts_header
        
        # Parse max-age value
        if 'max-age=' in hsts_header:
            max_age_match = hsts_header.split('max-age=')[1].split(';')[0]
            try:
                https_data['hsts_max_age'] = int(max_age_match)
            except ValueError:
                https_data['hsts_max_age'] = 0
    
    return https_data
```

### SEO Signals Detection Implementation

**Robots.txt and Sitemap.xml Analysis**:
```python
async def detect_seo_signals(page, base_url: str) -> Dict[str, Any]:
    """
    Detect presence and analyze robots.txt and sitemap.xml files.
    
    Args:
        page: Playwright page object
        base_url: Base URL of the website
        
    Returns:
        SEO signals analysis data
    """
    seo_signals = {}
    
    # Extract base URL (remove path, query, fragment)
    from urllib.parse import urlparse
    parsed_url = urlparse(base_url)
    clean_base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    # Check robots.txt
    try:
        robots_response = await page.goto(f"{clean_base_url}/robots.txt")
        if robots_response.status == 200:
            robots_content = await robots_response.text()
            seo_signals['robots_txt'] = {
                'present': True,
                'status_code': robots_response.status,
                'size_bytes': len(robots_content),
                'has_sitemap_directive': 'sitemap:' in robots_content.lower()
            }
        else:
            seo_signals['robots_txt'] = {
                'present': False,
                'status_code': robots_response.status,
                'size_bytes': 0,
                'has_sitemap_directive': False
            }
    except Exception as e:
        seo_signals['robots_txt'] = {
            'present': False,
            'error': str(e),
            'status_code': None,
            'size_bytes': 0
        }
    
    # Check sitemap.xml
    try:
        sitemap_response = await page.goto(f"{clean_base_url}/sitemap.xml")
        if sitemap_response.status == 200:
            sitemap_content = await sitemap_response.text()
            seo_signals['sitemap_xml'] = {
                'present': True,
                'status_code': sitemap_response.status,
                'size_bytes': len(sitemap_content),
                'is_valid_xml': sitemap_content.strip().startswith('<?xml')
            }
        else:
            seo_signals['sitemap_xml'] = {
                'present': False,
                'status_code': sitemap_response.status,
                'size_bytes': 0,
                'is_valid_xml': False
            }
    except Exception as e:
        seo_signals['sitemap_xml'] = {
            'present': False,
            'error': str(e),
            'status_code': None,
            'size_bytes': 0
        }
    
    return seo_signals
```

### Technical Assessment Data Models

**Typed Result Schema**:
```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class SecurityHeadersData(BaseModel):
    """OWASP security headers analysis results."""
    hsts: Optional[str] = Field(None, description="HTTP Strict Transport Security header")
    csp: Optional[str] = Field(None, description="Content Security Policy header") 
    x_frame_options: Optional[str] = Field(None, description="X-Frame-Options header")
    x_content_type_options: Optional[str] = Field(None, description="X-Content-Type-Options header")
    referrer_policy: Optional[str] = Field(None, description="Referrer-Policy header")
    permissions_policy: Optional[str] = Field(None, description="Permissions-Policy header")

class HttpsEnforcementData(BaseModel):
    """HTTPS enforcement and TLS analysis results."""
    scheme: str = Field(..., description="URL scheme (http/https)")
    enforced: bool = Field(..., description="Whether HTTPS is enforced")
    tls_version: Optional[str] = Field(None, description="TLS protocol version")
    tls_version_secure: Optional[bool] = Field(None, description="Whether TLS version is 1.2+")
    certificate_valid: bool = Field(False, description="SSL certificate validity")
    hsts_enabled: bool = Field(False, description="HSTS header present")
    hsts_config: Optional[str] = Field(None, description="Full HSTS header value")
    hsts_max_age: Optional[int] = Field(None, description="HSTS max-age in seconds")

class SeoSignalsData(BaseModel):
    """SEO signals analysis results."""
    robots_txt: Dict[str, Any] = Field(..., description="Robots.txt analysis")
    sitemap_xml: Dict[str, Any] = Field(..., description="Sitemap.xml analysis")

class JavaScriptErrorsData(BaseModel):
    """JavaScript console errors analysis."""
    error_count: int = Field(0, description="Total JavaScript errors")
    warning_count: int = Field(0, description="Total JavaScript warnings")
    details: List[Dict[str, Any]] = Field(default_factory=list, description="Error details (limited to 10)")

class TechnicalAssessmentResult(BaseModel):
    """Complete technical security assessment result."""
    lead_id: int = Field(..., description="Associated lead ID")
    url: str = Field(..., description="Assessed website URL")
    status: str = Field(..., description="Assessment status")
    security_headers: SecurityHeadersData = Field(..., description="Security headers analysis")
    https_enforcement: HttpsEnforcementData = Field(..., description="HTTPS enforcement analysis")
    seo_signals: SeoSignalsData = Field(..., description="SEO signals analysis")
    javascript_errors: JavaScriptErrorsData = Field(..., description="JavaScript errors analysis")
    performance_metrics: Dict[str, Any] = Field(default_factory=dict, description="Performance metrics")
    completed_at: datetime = Field(..., description="Assessment completion timestamp")
```

## Tests to Pass

1. **Security Headers Tests**: `pytest tests/test_security_headers.py -v` validates extraction of all 6 OWASP security headers with case-insensitive matching
2. **HTTPS Analysis Tests**: `pytest tests/test_https_enforcement.py -v` validates TLS version detection, HSTS parsing, certificate validation
3. **SEO Signals Tests**: `pytest tests/test_seo_signals.py -v` validates robots.txt and sitemap.xml detection with status code analysis
4. **JavaScript Errors Tests**: `pytest tests/test_js_errors.py -v` validates console message capture and error classification
5. **Memory Management Tests**: Browser process memory usage stays <200MB, proper cleanup validation after each assessment
6. **Timeout Tests**: Assessment completes within 15 seconds or fails gracefully with proper error handling
7. **Celery Integration Tests**: `pytest tests/test_technical_scraper_tasks.py -v` validates task retry logic and result serialization
8. **Schema Validation Tests**: All assessment results conform to TechnicalAssessmentResult Pydantic model
9. **SSL Failure Tests**: Graceful handling of SSL errors, invalid certificates, connection timeouts
10. **Performance Tests**: 95%+ task success rate, memory cleanup validation, assessment completion metrics

## Implementation Guide

### Phase 1: Core Playwright Infrastructure (Days 1-3)
1. **Playwright Setup**: Install Playwright Python, configure browser automation with memory optimization
2. **Browser Management**: Implement optimized browser instance creation with resource limits
3. **Basic Scraper**: Create async scraper function with timeout handling and error management
4. **Security Headers**: Implement OWASP security header extraction with case-insensitive matching
5. **Response Analysis**: Add HTTP response parsing and security details extraction

### Phase 2: Security Analysis Implementation (Days 4-6)
1. **HTTPS Detection**: Implement TLS version analysis and certificate validation
2. **HSTS Analysis**: Parse HSTS headers for max-age, subdomain inclusion, preload directives
3. **SEO Signals**: Add robots.txt and sitemap.xml detection with content analysis
4. **JavaScript Errors**: Implement console message capture with error classification
5. **Result Schema**: Create Pydantic models for typed assessment results

### Phase 3: Integration & Optimization (Days 7-9)
1. **Celery Integration**: Wrap scraper in Celery task with retry logic and error handling
2. **Memory Optimization**: Add memory monitoring, cleanup mechanisms, resource limits
3. **Database Storage**: Integrate with PRP-001 lead models for assessment result storage
4. **Performance Tuning**: Optimize browser configuration, resource blocking, timeout handling
5. **Error Handling**: Add comprehensive error handling for network failures, SSL issues

### Phase 4: Testing & Validation (Days 10-12)
1. **Unit Tests**: Write comprehensive tests for all scraper components with ≥90% coverage
2. **Integration Tests**: Test complete scraper pipeline with real websites and error scenarios
3. **Performance Tests**: Validate memory usage, timeout handling, and success rate requirements
4. **Load Testing**: Test scraper with high volume of concurrent assessments
5. **Documentation**: Complete API documentation and deployment instructions

## Validation Commands

```bash
# Playwright installation validation
playwright install chromium
python -c "from playwright.async_api import async_playwright; print('Playwright ready')"

# Security headers validation
python -c "from src.assessment.services.technical_scraper import extract_security_headers; print('Headers extractor ready')"

# Scraper task validation  
python -c "from src.assessment.services.technical_scraper import scrape_technical_security; print(scrape_technical_security.delay(1, 'https://example.com').get())"

# Memory usage validation
python scripts/memory_test.py --url="https://example.com" --iterations=10 --max-memory=200

# Performance validation
python scripts/performance_test.py --sites=100 --timeout=15 --success-rate=95

# Schema validation
python -c "from src.models.technical_assessment_models import TechnicalAssessmentResult; print('Schema validation ready')"

# Celery task validation
celery -A technical_scraper inspect active
celery -A technical_scraper inspect stats

# Database integration validation
python -c "from src.models.assessment_models import TechnicalAssessment; print('Database models ready')"
```

## Rollback Strategy

### Emergency Procedures
1. **Scraper Failure**: Disable technical scraper tasks and continue with other assessment types
2. **Memory Issues**: Reduce browser concurrency and increase cleanup frequency
3. **Timeout Problems**: Increase timeout limits or skip problematic URLs
4. **SSL Failures**: Add SSL error bypass for assessment continuation

### Detailed Rollback Steps
1. **Identify Issue**: Monitor dashboards show scraper failure rate >5% or memory exhaustion
2. **Immediate Response**: Stop new technical scraper tasks and allow running tasks to complete
3. **Service Degradation**: Continue assessments without technical security data
4. **Data Preservation**: Ensure partial results are saved before task failures
5. **System Analysis**: Analyze memory usage, timeout patterns, and error frequencies
6. **Gradual Recovery**: Test fixes with limited URL set before full deployment

## Success Criteria

1. **Technical Extraction Complete**: All 6 security headers, HTTPS data, SEO signals, and JS errors extracted successfully
2. **Memory Optimized**: Browser processes maintain <200MB memory usage with proper cleanup
3. **Performance Target**: 95%+ task success rate with 15-second timeout enforcement
4. **Integration Working**: Celery task integration with retry logic and database storage
5. **Schema Compliance**: All results conform to typed Pydantic models with proper validation
6. **Error Handling**: Graceful handling of SSL failures, timeouts, and network issues
7. **Testing Complete**: Unit tests ≥90% coverage, integration tests validate real-world scenarios
8. **Production Ready**: Memory monitoring, performance metrics, and operational dashboards

## Critical Context

### Security Assessment Components
- **OWASP Headers**: HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy
- **TLS Analysis**: Version detection (1.2+ required), certificate validation, HTTPS enforcement
- **SEO Signals**: robots.txt presence/size, sitemap.xml presence/size, directive analysis
- **JavaScript Monitoring**: Console error capture, warning classification, performance impact

### Performance Requirements  
- **Memory**: <200MB per browser instance with automatic cleanup
- **Timeout**: 15-second hard limit for all operations
- **Success Rate**: >95% task completion rate in production
- **Throughput**: Support for 100+ concurrent assessments

### Integration Dependencies
- **Assessment Orchestrator**: Integration via PRP-002 for task coordination
- **Lead Data Model**: Result storage via PRP-001 database models
- **Celery Framework**: Async task execution with Redis broker
- **Browser Automation**: Playwright with Chromium for reliable scraping

### Business Impact Metrics
- **Security Score**: Technical security rating contributing to overall audit score
- **SEO Health**: Technical SEO signals affecting search engine optimization rating
- **Risk Assessment**: Vulnerability identification for business risk evaluation
- **Compliance**: Security header compliance for regulatory assessment

## Definition of Done

- [ ] Playwright scraper implemented with memory-optimized browser configuration
- [ ] Security headers extraction for all 6 OWASP-recommended headers
- [ ] HTTPS enforcement analysis with TLS version and certificate validation
- [ ] SEO signals detection for robots.txt and sitemap.xml files
- [ ] JavaScript console error capture with error/warning classification
- [ ] Celery task integration with retry logic and exponential backoff
- [ ] Pydantic result schemas with comprehensive data validation
- [ ] Memory management with <200MB usage and proper cleanup
- [ ] Unit tests written for all components with ≥90% coverage
- [ ] Integration tests validate real-world website assessment
- [ ] Performance tests confirm timeout handling and success rates
- [ ] Database integration stores results via PRP-001 models
- [ ] Error handling for SSL failures, timeouts, and network issues
- [ ] Production deployment with monitoring and alerting
- [ ] Code review completed with security and performance validation
- [ ] Documentation updated with API reference and operational procedures
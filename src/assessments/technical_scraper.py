"""
PRP-004: Technical/Security Scraper Implementation
Playwright-based security analysis with OWASP headers, HTTPS enforcement, SEO signals, and JS errors
"""

import asyncio
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from celery import current_app
from pydantic import BaseModel, Field

from src.core.config import settings
from src.models.assessment_cost import AssessmentCost

logger = logging.getLogger(__name__)

# Pydantic Models for Typed Results
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
    analysis_timestamp: str = Field(..., description="Assessment completion timestamp")
    cost_records: List[Any] = Field(default_factory=list, description="Cost tracking records")
    
    class Config:
        arbitrary_types_allowed = True


class TechnicalScraperError(Exception):
    """Custom exception for technical scraper errors"""
    pass


async def scrape_technical_data_async(url: str, timeout: int = 15000) -> Dict[str, Any]:
    """
    Asynchronous technical data extraction with memory optimization.
    
    Args:
        url: Target website URL
        timeout: Maximum time in milliseconds for operations
        
    Returns:
        Complete technical assessment data
    """
    start_time = time.time()
    
    # Memory-optimized browser configuration
    browser_args = [
        '--no-sandbox',
        '--disable-dev-shm-usage', 
        '--disable-gpu',
        '--memory-pressure-off',
        '--max_old_space_size=200',  # Limit to 200MB
        '--disable-web-security',
        '--disable-features=TranslateUI',
        '--disable-extensions',
        '--disable-plugins'
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=browser_args
        )
        
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='LeadFactory-Security-Scanner/1.0',
            ignore_https_errors=True  # Allow SSL analysis even with invalid certs
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
                if msg.type in ['error', 'warning'] and len(js_errors) < 10:  # Limit for memory
                    js_errors.append({
                        'type': msg.type,
                        'text': msg.text[:500],  # Limit message length
                        'location': str(getattr(msg, 'location', 'unknown'))[:200],
                        'timestamp': time.time()
                    })
            
            page.on('console', handle_console_message)
            
            # Navigate to target URL
            try:
                response = await page.goto(url, wait_until='domcontentloaded')
                if not response:
                    raise TechnicalScraperError(f"Failed to navigate to {url}")
            except Exception as e:
                # Try without wait condition for problematic sites
                response = await page.goto(url, wait_until='networkidle')
                if not response:
                    raise TechnicalScraperError(f"Failed to navigate to {url}: {str(e)}")
            
            # Extract comprehensive technical data
            technical_data = {
                'security_headers': await extract_security_headers(response),
                'https_enforcement': await analyze_https_enforcement(response, page.url),
                'seo_signals': await detect_seo_signals(page, url),
                'javascript_errors': {
                    'error_count': len([e for e in js_errors if e['type'] == 'error']),
                    'warning_count': len([e for e in js_errors if e['type'] == 'warning']),
                    'details': js_errors
                },
                'performance_metrics': {
                    'load_time_ms': int((time.time() - start_time) * 1000),
                    'response_status': response.status if response else 0,
                    'final_url': page.url
                }
            }
            
            return technical_data
            
        finally:
            await context.close()
            await browser.close()


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
        try:
            # Get all headers and search case-insensitively
            all_headers = response.headers
            header_value = None
            
            for header_key, header_val in all_headers.items():
                if header_key.lower() == header_name.lower():
                    header_value = header_val
                    break
            
            security_data[key] = header_value if header_value else None
        except Exception as e:
            logger.warning(f"Error extracting header {header_name}: {e}")
            security_data[key] = None
    
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
        'scheme': current_url.split('://')[0] if '://' in current_url else 'unknown',
        'enforced': False,
        'tls_version': None,
        'tls_version_secure': False,
        'certificate_valid': False,
        'hsts_enabled': False,
        'hsts_config': None,
        'hsts_max_age': None
    }
    
    # Check if final URL uses HTTPS
    https_data['enforced'] = current_url.startswith('https://')
    
    try:
        # Extract TLS version from security details
        try:
            security_details = await response.security_details()
            if security_details:
                https_data['tls_version'] = security_details.get('protocol', 'Unknown')
                https_data['certificate_valid'] = True
                
                # Validate TLS version (1.2+ required)
                if https_data['tls_version'] and 'TLS' in https_data['tls_version']:
                    try:
                        # Extract version number (e.g., "TLS 1.3" -> 1.3)
                        version_parts = https_data['tls_version'].split()
                        if len(version_parts) >= 2:
                            version_num = float(version_parts[-1])
                            https_data['tls_version_secure'] = version_num >= 1.2
                    except (ValueError, IndexError):
                        https_data['tls_version_secure'] = False
        except (AttributeError, TypeError):
            # Some responses don't have security_details method or it's not available
            pass
    except Exception as e:
        logger.warning(f"Error analyzing security details: {e}")
    
    # Check HSTS header
    try:
        all_headers = response.headers
        hsts_header = None
        
        for header_key, header_val in all_headers.items():
            if header_key.lower() == 'strict-transport-security':
                hsts_header = header_val
                break
        
        if hsts_header:
            https_data['hsts_enabled'] = True
            https_data['hsts_config'] = hsts_header
            
            # Parse max-age value
            if 'max-age=' in hsts_header:
                try:
                    max_age_part = hsts_header.split('max-age=')[1].split(';')[0].strip()
                    https_data['hsts_max_age'] = int(max_age_part)
                except (ValueError, IndexError):
                    https_data['hsts_max_age'] = 0
    except Exception as e:
        logger.warning(f"Error analyzing HSTS header: {e}")
    
    return https_data


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
    try:
        parsed_url = urlparse(base_url)
        clean_base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    except Exception as e:
        logger.error(f"Error parsing base URL {base_url}: {e}")
        return {
            'robots_txt': {'present': False, 'error': f'URL parsing error: {e}'},
            'sitemap_xml': {'present': False, 'error': f'URL parsing error: {e}'}
        }
    
    # Check robots.txt
    try:
        robots_response = await page.goto(f"{clean_base_url}/robots.txt", timeout=10000)
        if robots_response and robots_response.status == 200:
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
                'status_code': robots_response.status if robots_response else 0,
                'size_bytes': 0,
                'has_sitemap_directive': False
            }
    except Exception as e:
        seo_signals['robots_txt'] = {
            'present': False,
            'error': str(e)[:200],  # Limit error message length
            'status_code': None,
            'size_bytes': 0,
            'has_sitemap_directive': False
        }
    
    # Check sitemap.xml
    try:
        sitemap_response = await page.goto(f"{clean_base_url}/sitemap.xml", timeout=10000)
        if sitemap_response and sitemap_response.status == 200:
            sitemap_content = await sitemap_response.text()
            seo_signals['sitemap_xml'] = {
                'present': True,
                'status_code': sitemap_response.status,
                'size_bytes': len(sitemap_content),
                'is_valid_xml': sitemap_content.strip().startswith('<?xml') or sitemap_content.strip().startswith('<urlset')
            }
        else:
            seo_signals['sitemap_xml'] = {
                'present': False,
                'status_code': sitemap_response.status if sitemap_response else 0,
                'size_bytes': 0,
                'is_valid_xml': False
            }
    except Exception as e:
        seo_signals['sitemap_xml'] = {
            'present': False,
            'error': str(e)[:200],  # Limit error message length
            'status_code': None,
            'size_bytes': 0,
            'is_valid_xml': False
        }
    
    return seo_signals


async def assess_technical_security(url: str, company: str, lead_id: int) -> TechnicalAssessmentResult:
    """
    Main entry point for technical security assessment.
    
    Args:
        url: Target website URL
        company: Company name for cost tracking
        lead_id: Database ID of the lead
        
    Returns:
        Complete technical assessment result
    """
    start_time = time.time()
    cost_records = []
    
    try:
        # Create cost tracking record
        cost_record = AssessmentCost.create_technical_scraper_cost(
            lead_id=lead_id,
            cost_cents=0.10,  # $0.001 per assessment - very low cost for internal scraping
            response_status="pending"
        )
        cost_records.append(cost_record)
        
        # Run technical assessment
        technical_data = await scrape_technical_data_async(url, timeout=15000)
        
        # Update cost record with success
        end_time = time.time()
        cost_record.response_status = "success"
        cost_record.response_time_ms = int((end_time - start_time) * 1000)
        
        # Create result object
        result = TechnicalAssessmentResult(
            lead_id=lead_id,
            url=url,
            status="completed",
            security_headers=SecurityHeadersData(**technical_data['security_headers']),
            https_enforcement=HttpsEnforcementData(**technical_data['https_enforcement']),
            seo_signals=SeoSignalsData(**technical_data['seo_signals']),
            javascript_errors=JavaScriptErrorsData(**technical_data['javascript_errors']),
            performance_metrics=technical_data['performance_metrics'],
            analysis_timestamp=datetime.now(timezone.utc).isoformat(),
            cost_records=cost_records
        )
        
        logger.info(f"Technical assessment completed for {url} in {cost_record.response_time_ms}ms")
        return result
        
    except Exception as e:
        # Update cost record with error
        end_time = time.time()
        if cost_records:
            cost_records[0].response_status = "error"
            cost_records[0].response_time_ms = int((end_time - start_time) * 1000)
            cost_records[0].error_message = str(e)[:500]
        
        logger.error(f"Technical assessment failed for {url}: {e}")
        raise TechnicalScraperError(f"Technical assessment failed: {str(e)}")


# Add create_technical_scraper_cost method to AssessmentCost model
def create_technical_scraper_cost_method(cls, lead_id: int, cost_cents: float = 0.10, response_status: str = "success", response_time_ms: Optional[int] = None, error_message: Optional[str] = None):
    """
    Create cost record for Technical Scraper assessment.
    
    Args:
        lead_id: ID of the lead being assessed
        cost_cents: Cost in cents (default $0.001)
        response_status: success, error, or timeout
        response_time_ms: Assessment response time in milliseconds
        error_message: Error message if applicable
        
    Returns:
        AssessmentCost instance
    """
    now = datetime.now(timezone.utc)
    
    return cls(
        lead_id=lead_id,
        service_name="technical_scraper",
        api_endpoint="playwright_scraper",
        cost_cents=cost_cents,
        currency="USD",
        request_timestamp=now,
        response_status=response_status,
        response_time_ms=response_time_ms,
        api_quota_used=False,  # Internal scraping doesn't use external quota
        rate_limited=False,
        retry_count=0,
        error_message=error_message,
        daily_budget_date=now.strftime("%Y-%m-%d"),
        monthly_budget_date=now.strftime("%Y-%m")
    )

# Monkey patch the method to AssessmentCost
AssessmentCost.create_technical_scraper_cost = classmethod(create_technical_scraper_cost_method)
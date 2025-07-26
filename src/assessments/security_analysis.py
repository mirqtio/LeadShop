"""
Security Header Analysis Module
Analyzes website security headers and SSL configuration
"""

import asyncio
import httpx
import ssl
import socket
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SecurityMetrics(BaseModel):
    """Security assessment metrics"""
    has_https: bool = False
    ssl_grade: Optional[str] = None
    security_headers: Dict[str, Any] = {}
    missing_headers: List[str] = []
    security_score: int = 0
    vulnerabilities: List[str] = []
    recommendations: List[str] = []
    analysis_timestamp: Optional[str] = None
    cost_records: List[Any] = []


REQUIRED_SECURITY_HEADERS = {
    "Strict-Transport-Security": "HSTS header protects against protocol downgrade attacks",
    "X-Content-Type-Options": "Prevents MIME type sniffing",
    "X-Frame-Options": "Protects against clickjacking",
    "Content-Security-Policy": "Controls resources the browser is allowed to load",
    "X-XSS-Protection": "Basic XSS protection (deprecated but still checked)",
    "Referrer-Policy": "Controls referrer information sent with requests",
    "Permissions-Policy": "Controls browser feature permissions"
}


async def assess_security_headers(url: str, lead_id: Optional[int] = None, assessment_id: Optional[int] = None) -> SecurityMetrics:
    """
    Assess website security headers and SSL configuration
    
    Args:
        url: Website URL to analyze
        lead_id: Optional lead ID for tracking
        assessment_id: Optional assessment ID for storing detailed results
        
    Returns:
        SecurityMetrics object with assessment results
    """
    logger.info(f"Starting security assessment for {url}")
    
    metrics = SecurityMetrics(analysis_timestamp=datetime.utcnow().isoformat())
    
    try:
        # Check if URL uses HTTPS
        metrics.has_https = url.startswith("https://")
        
        # Make HTTP request to check headers
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            verify=False  # Allow self-signed certs for now
        ) as client:
            response = await client.get(url)
            
            # Analyze security headers
            headers = response.headers
            metrics.security_headers = {}
            
            for header, description in REQUIRED_SECURITY_HEADERS.items():
                header_lower = header.lower()
                value = headers.get(header_lower)
                
                if value:
                    metrics.security_headers[header] = {
                        "present": True,
                        "value": value,
                        "description": description
                    }
                else:
                    metrics.missing_headers.append(header)
                    metrics.security_headers[header] = {
                        "present": False,
                        "value": None,
                        "description": description
                    }
            
            # Check for additional security indicators
            if headers.get("server"):
                server_header = headers.get("server", "").lower()
                if any(version in server_header for version in ["apache/", "nginx/", "iis/"]):
                    metrics.vulnerabilities.append("Server version exposed in headers")
            
            # Calculate security score
            total_headers = len(REQUIRED_SECURITY_HEADERS)
            present_headers = total_headers - len(metrics.missing_headers)
            base_score = int((present_headers / total_headers) * 70)
            
            # Add points for HTTPS
            if metrics.has_https:
                base_score += 20
                metrics.ssl_grade = "A"  # Simplified SSL grade
            else:
                metrics.vulnerabilities.append("Site does not use HTTPS")
                metrics.recommendations.append("Implement HTTPS with a valid SSL certificate")
            
            # Additional points for strong CSP
            csp = headers.get("content-security-policy")
            if csp and "default-src" in csp:
                base_score += 10
            
            metrics.security_score = min(base_score, 100)
            
            # Generate recommendations
            for header in metrics.missing_headers:
                metrics.recommendations.append(f"Implement {header} header")
            
            # Check for cookies without secure flag
            cookies = response.cookies
            for cookie_name, cookie_value in cookies.items():
                # Note: httpx doesn't expose all cookie attributes easily
                metrics.recommendations.append(f"Ensure cookie '{cookie_name}' has Secure and HttpOnly flags")
            
            logger.info(f"Security assessment completed for {url}: score {metrics.security_score}")
            
    except httpx.ConnectError:
        logger.error(f"Failed to connect to {url}")
        metrics.vulnerabilities.append("Failed to connect to website")
        metrics.security_score = 0
    except httpx.TimeoutException:
        logger.error(f"Timeout while analyzing {url}")
        metrics.vulnerabilities.append("Website response timeout")
        metrics.security_score = 0
    except Exception as e:
        logger.error(f"Security analysis failed for {url}: {e}")
        metrics.vulnerabilities.append(f"Analysis error: {str(e)}")
        metrics.security_score = 0
    
    # Save detailed security data to new tables if assessment_id provided
    if assessment_id:
        from src.core.database import AsyncSessionLocal
        from urllib.parse import urlparse
        
        async with AsyncSessionLocal() as db:
            try:
                # Get SSL certificate data if HTTPS
                ssl_cert_data = None
                if metrics.has_https:
                    try:
                        hostname = urlparse(url).hostname
                        ssl_cert_data = await analyze_ssl_certificate(hostname)
                    except Exception as ssl_e:
                        logger.warning(f"Failed to get SSL certificate data: {ssl_e}")
                
                await save_security_analysis_to_db(
                    db, assessment_id, metrics, ssl_cert_data
                )
                await db.commit()
                logger.info(f"Saved detailed security data for assessment {assessment_id}")
            except Exception as db_exc:
                await db.rollback()
                logger.error(f"Failed to save security data to database: {db_exc}")
    
    return metrics


async def save_security_analysis_to_db(
    db,
    assessment_id: int,
    security_metrics: SecurityMetrics,
    ssl_cert_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Save security analysis results to the new database schema
    
    Args:
        db: Database session
        assessment_id: Assessment ID to link results to
        security_metrics: SecurityMetrics object with assessment results
        ssl_cert_data: Optional SSL certificate data from analyze_ssl_certificate
    """
    from src.models.security import (
        SecurityAnalysis, SecurityHeader, SecurityVulnerability,
        SecurityCookie, SecurityRecommendation
    )
    from datetime import datetime
    
    # Create main security analysis record
    analysis = SecurityAnalysis(
        assessment_id=assessment_id,
        has_https=security_metrics.has_https,
        ssl_grade=security_metrics.ssl_grade,
        security_score=security_metrics.security_score,
        analysis_timestamp=datetime.fromisoformat(security_metrics.analysis_timestamp) if security_metrics.analysis_timestamp else datetime.utcnow(),
        raw_headers={k: v for k, v in security_metrics.security_headers.items()}
    )
    
    # Add SSL certificate data if available
    if ssl_cert_data and ssl_cert_data.get("is_valid"):
        analysis.ssl_issuer = ssl_cert_data.get("issuer", {}).get("organizationName", "Unknown")
        analysis.ssl_protocol = ssl_cert_data.get("version")
        analysis.ssl_certificate_data = ssl_cert_data
        
        # Parse SSL expiration date if available
        if ssl_cert_data.get("not_after"):
            try:
                # SSL date format: 'Oct 15 23:59:59 2024 GMT'
                from datetime import datetime
                expires_str = ssl_cert_data["not_after"]
                analysis.ssl_expires = datetime.strptime(expires_str, "%b %d %H:%M:%S %Y %Z")
            except Exception as e:
                logger.warning(f"Failed to parse SSL expiration date: {e}")
    
    db.add(analysis)
    await db.flush()  # Get the ID
    
    # Save security headers
    for header_name, header_info in security_metrics.security_headers.items():
        if isinstance(header_info, dict):
            header = SecurityHeader(
                security_analysis_id=analysis.id,
                header_name=header_name,
                header_value=header_info.get("value"),
                is_present=header_info.get("present", False),
                is_secure=header_info.get("present", False),  # Simple logic: present = secure
                severity="high" if not header_info.get("present") else "info",
                recommendation=header_info.get("description", "")
            )
            db.add(header)
    
    # Save vulnerabilities
    for vuln_text in security_metrics.vulnerabilities:
        # Determine vulnerability type and severity based on text
        vuln_type = "general"
        severity = "medium"
        
        if "HTTPS" in vuln_text or "SSL" in vuln_text:
            vuln_type = "ssl/tls"
            severity = "high"
        elif "Server version exposed" in vuln_text:
            vuln_type = "information_disclosure"
            severity = "low"
        elif "Failed to connect" in vuln_text or "timeout" in vuln_text.lower():
            vuln_type = "connectivity"
            severity = "critical"
        
        vulnerability = SecurityVulnerability(
            security_analysis_id=analysis.id,
            vulnerability_type=vuln_type,
            severity=severity,
            description=vuln_text,
            recommendation="Address this vulnerability to improve security posture"
        )
        db.add(vulnerability)
    
    # Save recommendations
    priority = 1
    for rec_text in security_metrics.recommendations:
        # Determine category based on recommendation text
        category = "general"
        impact = "medium"
        effort = "medium"
        
        if "HTTPS" in rec_text or "SSL" in rec_text:
            category = "ssl"
            impact = "high"
            effort = "medium"
        elif "header" in rec_text.lower():
            category = "headers"
            impact = "medium"
            effort = "low"
        elif "cookie" in rec_text.lower():
            category = "cookies"
            impact = "medium"
            effort = "low"
        
        recommendation = SecurityRecommendation(
            security_analysis_id=analysis.id,
            category=category,
            priority=priority,
            title=rec_text[:255],  # Truncate if too long
            description=rec_text,
            impact=impact,
            estimated_effort=effort
        )
        db.add(recommendation)
        priority += 1
    
    # Note: Cookie analysis would need to be enhanced in assess_security_headers
    # to properly extract cookie details from the response
    # For now, we'll add basic cookie recommendations if mentioned
    for rec_text in security_metrics.recommendations:
        if "cookie" in rec_text.lower() and "Ensure cookie" in rec_text:
            # Extract cookie name from recommendation text
            import re
            match = re.search(r"cookie '([^']+)'", rec_text)
            if match:
                cookie_name = match.group(1)
                cookie = SecurityCookie(
                    security_analysis_id=analysis.id,
                    cookie_name=cookie_name,
                    has_secure_flag=False,  # Assumed from recommendation
                    has_httponly_flag=False,  # Assumed from recommendation
                    has_samesite=False,
                    recommendation="Set Secure and HttpOnly flags for this cookie"
                )
                db.add(cookie)


async def analyze_ssl_certificate(hostname: str, port: int = 443) -> Dict[str, Any]:
    """
    Analyze SSL certificate details
    
    Args:
        hostname: Domain to check
        port: Port number (default 443)
        
    Returns:
        Dict with certificate details
    """
    try:
        # Create SSL context
        context = ssl.create_default_context()
        
        # Connect and get certificate
        with socket.create_connection((hostname, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                
                return {
                    "issuer": dict(x[0] for x in cert.get("issuer", [])),
                    "subject": dict(x[0] for x in cert.get("subject", [])),
                    "version": cert.get("version"),
                    "serial_number": cert.get("serialNumber"),
                    "not_before": cert.get("notBefore"),
                    "not_after": cert.get("notAfter"),
                    "signature_algorithm": cert.get("signatureAlgorithm"),
                    "is_valid": True
                }
    except Exception as e:
        logger.error(f"SSL certificate analysis failed: {e}")
        return {"is_valid": False, "error": str(e)}


# Test function
if __name__ == "__main__":
    async def test():
        result = await assess_security_headers("https://example.com")
        print(f"Security Score: {result.security_score}")
        print(f"Missing Headers: {result.missing_headers}")
        print(f"Vulnerabilities: {result.vulnerabilities}")
        
    asyncio.run(test())
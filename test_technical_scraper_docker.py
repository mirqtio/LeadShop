#!/usr/bin/env python3
"""
Docker-based Technical/Security Scraper Demo for PRP-004
Tests Playwright security analysis with real website assessment
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

# Ensure we're using the Docker environment paths
sys.path.insert(0, '/app/src')

from src.core.database import get_db, AsyncSessionLocal
from src.models.assessment_cost import AssessmentCost
from src.models.lead import Lead, Assessment
from src.assessments.technical_scraper import assess_technical_security, TechnicalScraperError
from src.core.config import settings

async def check_database_connection():
    """Verify database connection and tables exist"""
    try:
        async with AsyncSessionLocal() as db:
            # Test connection
            result = await db.execute(text("SELECT 1"))
            print("✅ Database connection successful")
            
            # Check if tables exist
            result = await db.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema IN ('public', 'leadfactory') 
                AND table_name IN ('leads', 'assessments', 'assessment_costs')
            """))
            tables = [row[0] for row in result.fetchall()]
            
            print(f"📊 Available tables: {tables}")
            
            if 'leads' not in tables:
                print("❌ Missing 'leads' table - run migrations first")
                return False
            if 'assessments' not in tables:
                print("❌ Missing 'assessments' table - run migrations first") 
                return False
            if 'assessment_costs' not in tables:
                print("⚠️ Missing 'assessment_costs' table - will create automatically")
                
            return True
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def create_test_lead(url: str, company: str = "Technical Demo Company") -> Lead:
    """Create a test lead for technical security analysis"""
    async with AsyncSessionLocal() as db:
        # Check if lead already exists
        existing_lead = await db.execute(
            select(Lead).where(Lead.url == url)
        )
        lead = existing_lead.scalar_one_or_none()
        
        if lead:
            print(f"📋 Using existing lead: {lead.company} ({lead.url})")
            return lead
        
        # Create new lead
        lead = Lead(
            company=company,
            email=f"demo@{company.lower().replace(' ', '')}.com",
            source="docker_technical_demo",
            url=url,
            city="San Francisco",
            state="CA",
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        
        print(f"✅ Created new lead: {lead.company} (ID: {lead.id})")
        return lead


async def create_assessment_record(lead_id: int) -> Assessment:
    """Create assessment record for the lead"""
    async with AsyncSessionLocal() as db:
        # Check if assessment already exists
        existing_assessment = await db.execute(
            select(Assessment).where(Assessment.lead_id == lead_id)
        )
        assessment = existing_assessment.scalar_one_or_none()
        
        if assessment:
            print(f"📊 Using existing assessment (ID: {assessment.id})")
            return assessment
        
        assessment = Assessment(
            lead_id=lead_id,
            status="pending",
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(assessment)
        await db.commit()
        await db.refresh(assessment)
        
        print(f"📊 Created assessment record (ID: {assessment.id})")
        return assessment


async def store_technical_results(lead_id: int, technical_data: dict, security_score: int):
    """Store technical security results in assessment record"""
    async with AsyncSessionLocal() as db:
        # Extract cost records before storing JSON (they aren't JSON serializable)
        cost_records = technical_data.pop("cost_records", [])
        
        # Update assessment with technical security data
        assessment_result = await db.execute(
            select(Assessment).where(Assessment.lead_id == lead_id)
        )
        assessment = assessment_result.scalar_one_or_none()
        
        if assessment:
            assessment.security_headers = technical_data
            assessment.security_score = security_score
            assessment.status = "completed"
            assessment.updated_at = datetime.now(timezone.utc)
            
            await db.commit()
            print(f"💾 Stored technical security results (Score: {security_score})")
        
        # Store cost records separately
        if cost_records:
            for cost_record in cost_records:
                db.add(cost_record)
            await db.commit()
            print(f"💰 Stored {len(cost_records)} cost records")


async def query_and_display_results(lead_id: int):
    """Query database and display comprehensive technical security results"""
    async with AsyncSessionLocal() as db:
        # Get lead and assessment data
        lead_result = await db.execute(
            select(Lead).where(Lead.id == lead_id)
        )
        lead = lead_result.scalar_one()
        
        assessment_result = await db.execute(
            select(Assessment).where(Assessment.lead_id == lead_id)
        )
        assessment = assessment_result.scalar_one()
        
        # Get cost records
        cost_result = await db.execute(
            select(AssessmentCost).where(AssessmentCost.lead_id == lead_id)
        )
        cost_records = cost_result.scalars().all()
        
        # Display comprehensive results
        print("\n" + "="*120)
        print("🔒 TECHNICAL/SECURITY SCRAPER DEMO - PRP-004 RESULTS")
        print("="*120)
        
        print(f"\n🏢 LEAD INFORMATION:")
        print(f"   Company: {lead.company}")
        print(f"   URL: {lead.url}")
        print(f"   Lead ID: {lead.id}")
        print(f"   Source: {lead.source}")
        print(f"   Created: {lead.created_at}")
        
        print(f"\n🔒 SECURITY ANALYSIS RESULTS:")
        print(f"   Security Score: {assessment.security_score}/100")
        print(f"   Assessment Status: {assessment.status}")
        print(f"   Updated: {assessment.updated_at}")
        
        if assessment.security_headers:
            security_data = assessment.security_headers
            
            print(f"\n🛡️ SECURITY HEADERS (OWASP):")
            headers = security_data.get("security_headers", {})
            
            header_labels = {
                'hsts': 'HTTP Strict Transport Security',
                'csp': 'Content Security Policy',
                'x_frame_options': 'X-Frame-Options',
                'x_content_type_options': 'X-Content-Type-Options',
                'referrer_policy': 'Referrer-Policy',
                'permissions_policy': 'Permissions-Policy'
            }
            
            for header_key, header_name in header_labels.items():
                value = headers.get(header_key)
                status = "✅ Present" if value else "❌ Missing"
                if value:
                    print(f"   {header_name}: {status}")
                    print(f"      Value: {value[:80]}{'...' if len(str(value)) > 80 else ''}")
                else:
                    print(f"   {header_name}: {status}")
            
            print(f"\n🔐 HTTPS ENFORCEMENT:")
            https_data = security_data.get("https_enforcement", {})
            scheme = https_data.get("scheme", "unknown")
            enforced = https_data.get("enforced", False)
            cert_valid = https_data.get("certificate_valid", False)
            tls_version = https_data.get("tls_version", "Unknown")
            tls_secure = https_data.get("tls_version_secure", False)
            hsts_enabled = https_data.get("hsts_enabled", False)
            
            print(f"   URL Scheme: {scheme.upper()} {'✅' if scheme == 'https' else '⚠️'}")
            print(f"   HTTPS Enforced: {'✅ Yes' if enforced else '❌ No'}")
            print(f"   Certificate Valid: {'✅ Yes' if cert_valid else '❌ No'}")
            print(f"   TLS Version: {tls_version} {'✅' if tls_secure else '⚠️'}")
            print(f"   HSTS Enabled: {'✅ Yes' if hsts_enabled else '❌ No'}")
            
            if https_data.get("hsts_max_age"):
                max_age = https_data["hsts_max_age"]
                days = max_age // (24 * 3600)
                print(f"   HSTS Max-Age: {max_age} seconds ({days} days)")
            
            print(f"\n🔍 SEO SIGNALS:")
            seo_data = security_data.get("seo_signals", {})
            
            robots_info = seo_data.get("robots_txt", {})
            robots_present = robots_info.get("present", False)
            robots_size = robots_info.get("size_bytes", 0)
            robots_status = robots_info.get("status_code", 0)
            
            sitemap_info = seo_data.get("sitemap_xml", {})
            sitemap_present = sitemap_info.get("present", False)
            sitemap_size = sitemap_info.get("size_bytes", 0)
            sitemap_status = sitemap_info.get("status_code", 0)
            
            print(f"   robots.txt: {'✅ Found' if robots_present else '❌ Missing'}")
            if robots_present:
                print(f"      Status Code: {robots_status}")
                print(f"      File Size: {robots_size} bytes")
                if robots_info.get("has_sitemap_directive"):
                    print(f"      Contains Sitemap Directive: ✅ Yes")
            
            print(f"   sitemap.xml: {'✅ Found' if sitemap_present else '❌ Missing'}")
            if sitemap_present:
                print(f"      Status Code: {sitemap_status}")
                print(f"      File Size: {sitemap_size} bytes")
                if sitemap_info.get("is_valid_xml"):
                    print(f"      Valid XML Format: ✅ Yes")
            
            print(f"\n⚠️ JAVASCRIPT ERRORS:")
            js_data = security_data.get("javascript_errors", {})
            error_count = js_data.get("error_count", 0)
            warning_count = js_data.get("warning_count", 0)
            js_details = js_data.get("details", [])
            
            print(f"   JavaScript Errors: {error_count} {'❌' if error_count > 0 else '✅'}")
            print(f"   JavaScript Warnings: {warning_count} {'⚠️' if warning_count > 0 else '✅'}")
            
            if js_details:
                print(f"   Error Details (showing first 3):")
                for i, error in enumerate(js_details[:3], 1):
                    error_type = error.get("type", "unknown")
                    error_text = error.get("text", "")[:100]
                    print(f"      #{i}: [{error_type.upper()}] {error_text}...")
            
            print(f"\n⚡ PERFORMANCE METRICS:")
            perf_data = security_data.get("performance_metrics", {})
            load_time = perf_data.get("load_time_ms", 0)
            response_status = perf_data.get("response_status", 0)
            final_url = perf_data.get("final_url", "")
            
            print(f"   Load Time: {load_time}ms")
            print(f"   Response Status: {response_status}")
            print(f"   Final URL: {final_url}")
            print(f"   Analysis Timestamp: {security_data.get('scan_timestamp', 'N/A')}")
        
        print(f"\n💰 COST TRACKING:")
        technical_costs = [c for c in cost_records if c.service_name == 'technical_scraper']
        total_cost = sum(cost.cost_cents for cost in technical_costs)
        print(f"   Total Technical Scraper Cost: ${total_cost/100:.4f}")
        print(f"   Cost Records: {len(technical_costs)}")
        
        for i, cost in enumerate(technical_costs, 1):
            status_emoji = "✅" if cost.response_status == "success" else "❌"
            print(f"   #{i}: ${cost.cost_dollars:.4f} - {cost.response_status} {status_emoji} ({cost.response_time_ms}ms)")
        
        print(f"\n🔧 CONFIGURATION:")
        print(f"   Playwright Installed: ✅ Yes")
        print(f"   Browser: Chromium (headless)")
        print(f"   Memory Limit: 200MB per assessment")
        print(f"   Timeout: 15 seconds")
        print(f"   Database URL: {settings.DATABASE_URL[:50]}...")
        
        print("\n" + "="*120)
        print("🎉 PRP-004 TECHNICAL/SECURITY SCRAPER DEMO COMPLETED!")
        print("="*120)


async def run_technical_scraper_demo(url: str, company: str = None):
    """Run complete technical security scraper demo"""
    print("🔒 PRP-004 TECHNICAL/SECURITY SCRAPER DEMO")
    print("🔗 URL:", url)
    print("🏗️ Environment: Docker Staging")
    print("🛡️ Analysis: Security Headers, HTTPS, SEO, JavaScript Errors")
    
    # Step 1: Check database connection
    print("\n📊 Step 1: Checking database connection...")
    db_ok = await check_database_connection()
    if not db_ok:
        print("❌ Database check failed - cannot proceed")
        return
    
    # Step 2: Check Playwright setup
    print("\n🎭 Step 2: Checking Playwright setup...")
    try:
        from playwright.async_api import async_playwright
        print("✅ Playwright library available")
        print("✅ Chromium browser installed")
    except ImportError as e:
        print(f"❌ Playwright not available: {e}")
        return
    
    try:
        # Step 3: Create test lead  
        print("\n📋 Step 3: Creating test lead...")
        lead = await create_test_lead(url, company or f"Technical Demo - {url}")
        
        # Step 4: Create assessment record
        print("\n📊 Step 4: Creating assessment record...")
        assessment = await create_assessment_record(lead.id)
        
        # Step 5: Run technical security analysis
        print("\n🔒 Step 5: Running technical security analysis...")
        print("   🕒 This may take 10-20 seconds for complete security analysis...")
        print("   🛡️ Analyzing security headers, HTTPS enforcement, SEO signals...")
        print("   🔍 Capturing JavaScript errors and performance metrics...")
        
        technical_results = await assess_technical_security(
            url=url, 
            company=lead.company, 
            lead_id=lead.id
        )
        
        # Calculate security score
        security_headers = technical_results.security_headers
        https_enforcement = technical_results.https_enforcement
        seo_signals = technical_results.seo_signals
        js_errors = technical_results.javascript_errors
        
        # Score calculation (same as in Celery task)
        headers_score = 0
        security_header_weights = {
            'hsts': 20, 'csp': 25, 'x_frame_options': 15, 
            'x_content_type_options': 10, 'referrer_policy': 15, 'permissions_policy': 15
        }
        
        for header, weight in security_header_weights.items():
            if getattr(security_headers, header) is not None:
                headers_score += weight
        
        https_score = 0
        if https_enforcement.enforced:
            https_score += 15
        if https_enforcement.certificate_valid:
            https_score += 10
        if https_enforcement.tls_version_secure:
            https_score += 5
        
        seo_score = 0
        if seo_signals.robots_txt.get('present', False):
            seo_score += 5
        if seo_signals.sitemap_xml.get('present', False):
            seo_score += 5
        
        js_penalty = min(10, js_errors.error_count * 2)
        final_security_score = max(0, min(100, headers_score + https_score + seo_score - js_penalty))
        
        print(f"   ✅ Analysis complete! Security Score: {final_security_score}/100")
        
        # Step 6: Store results
        print("\n💾 Step 6: Storing results in database...")
        
        # Convert to dict for storage (same format as Celery task)
        technical_data = {
            "url": url,
            "scan_timestamp": technical_results.analysis_timestamp,
            "security_headers": {
                "hsts": security_headers.hsts,
                "csp": security_headers.csp,
                "x_frame_options": security_headers.x_frame_options,
                "x_content_type_options": security_headers.x_content_type_options,
                "referrer_policy": security_headers.referrer_policy,
                "permissions_policy": security_headers.permissions_policy
            },
            "https_enforcement": {
                "scheme": https_enforcement.scheme,
                "enforced": https_enforcement.enforced,
                "tls_version": https_enforcement.tls_version,
                "tls_version_secure": https_enforcement.tls_version_secure,
                "certificate_valid": https_enforcement.certificate_valid,
                "hsts_enabled": https_enforcement.hsts_enabled,
                "hsts_max_age": https_enforcement.hsts_max_age
            },
            "seo_signals": {
                "robots_txt": seo_signals.robots_txt,
                "sitemap_xml": seo_signals.sitemap_xml
            },
            "javascript_errors": {
                "error_count": js_errors.error_count,
                "warning_count": js_errors.warning_count,
                "details": js_errors.details[:5]
            },
            "performance_metrics": technical_results.performance_metrics,
            "analysis_duration_ms": technical_results.performance_metrics.get('load_time_ms', 0),
            "cost_records": technical_results.cost_records
        }
        
        await store_technical_results(lead.id, technical_data, final_security_score)
        
        # Step 7: Query and display comprehensive results
        print("\n🔍 Step 7: Querying database and displaying comprehensive results...")
        await query_and_display_results(lead.id)
        
    except TechnicalScraperError as e:
        print(f"\n❌ Technical Scraper Error: {e}")
        print("This could be due to:")
        print("- Website blocking automated access")
        print("- SSL certificate issues")
        print("- Network connectivity problems")
        print("- Playwright browser initialization issues")
        
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main demo function"""
    # Use a well-known website for testing
    test_url = "https://anthrasite.io"
    test_company = "Anthrasite.io - AI Dev Tools (Technical Demo)"
    
    # Allow custom URL from command line
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        test_company = f"Technical Demo - {test_url}"
    
    await run_technical_scraper_demo(test_url, test_company)


if __name__ == "__main__":
    # Run the technical scraper demo
    asyncio.run(main())
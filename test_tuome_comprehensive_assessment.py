#!/usr/bin/env python3
"""
Comprehensive Assessment Test: Tuome NYC
Execute full assessment pipeline (PageSpeed + Technical + GBP) with database persistence
"""

import asyncio
import os
import sys
import json
from datetime import datetime, timezone
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, '/Users/charlieirwin/LeadShop')

# Set environment for database connection
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://leadfactory:secure_password_2024@localhost:5432/leadfactory'
os.environ['GOOGLE_PLACES_API_KEY'] = 'demo_key_placeholder'  # Would be real key in production

async def create_test_lead():
    """Create a test lead for Tuome NYC in the database."""
    
    from src.core.database import get_db
    from src.models.lead import Lead
    from sqlalchemy import select
    
    # Tuome business information
    tuome_data = {
        "company": "Tuome",
        "url": "https://tuome.com",
        "email": "contact@tuome.com", 
        "phone": "+1 (212) 555-0123",
        "address": "123 Broadway",
        "city": "New York",
        "state": "NY",
        "zip_code": "10001",
        "country": "US",
        "industry": "Restaurant",
        "employee_count": 50,
        "annual_revenue": 2000000,
        "lead_source": "comprehensive_test",
        "lead_status": "new",
        "notes": "Test lead for comprehensive assessment demo - Tuome NYC restaurant"
    }
    
    async with get_db() as db:
        # Check if lead already exists
        existing_lead = await db.execute(
            select(Lead).where(Lead.company == "Tuome", Lead.city == "New York")
        )
        existing = existing_lead.scalar_one_or_none()
        
        if existing:
            print(f"📋 Using existing lead: Tuome (ID: {existing.id})")
            return existing.id
        
        # Create new lead
        lead = Lead(**tuome_data)
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        
        print(f"📋 Created new lead: Tuome (ID: {lead.id})")
        return lead.id

async def run_pagespeed_assessment(lead_id: int, url: str):
    """Run PageSpeed assessment for Tuome."""
    
    print("\n🚀 Running PageSpeed Assessment")
    print("-" * 40)
    
    try:
        from src.assessments.pagespeed import assess_pagespeed, PageSpeedError
        
        start_time = datetime.now()
        
        # Execute PageSpeed assessment
        pagespeed_results = await assess_pagespeed(url, "Tuome", lead_id)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Display results
        print(f"✅ PageSpeed assessment completed in {duration:.2f}s")
        print(f"📊 Performance Score: {pagespeed_results.get('performance_score', 0)}/100")
        
        # Core Web Vitals
        core_vitals = pagespeed_results.get('core_web_vitals', {})
        print(f"🎯 Core Web Vitals:")
        print(f"   • FCP: {core_vitals.get('first_contentful_paint', 'N/A')}")
        print(f"   • LCP: {core_vitals.get('largest_contentful_paint', 'N/A')}")
        print(f"   • CLS: {core_vitals.get('cumulative_layout_shift', 'N/A')}")
        print(f"   • TBT: {core_vitals.get('total_blocking_time', 'N/A')}")
        
        # Store cost records in database
        if pagespeed_results.get("cost_records"):
            from src.core.database import get_db
            
            async with get_db() as db:
                for cost_record in pagespeed_results["cost_records"]:
                    db.add(cost_record)
                await db.commit()
            
            print(f"💰 Cost: ${pagespeed_results['cost_records'][0].cost_cents / 100:.4f}")
        
        return pagespeed_results
        
    except Exception as e:
        print(f"❌ PageSpeed assessment failed: {e}")
        return None

async def run_technical_assessment(lead_id: int, url: str):
    """Run Technical/Security assessment for Tuome."""
    
    print("\n🔒 Running Technical/Security Assessment")
    print("-" * 40)
    
    try:
        from src.assessments.technical_scraper import assess_technical_security, TechnicalScraperError
        
        start_time = datetime.now()
        
        # Execute technical assessment
        technical_results = await assess_technical_security(url, "Tuome", lead_id)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Display results
        print(f"✅ Technical assessment completed in {duration:.2f}s")
        
        # Security headers
        headers = technical_results.security_headers
        print(f"🛡️  Security Headers:")
        print(f"   • HSTS: {'✅' if headers.hsts else '❌'}")
        print(f"   • CSP: {'✅' if headers.csp else '❌'}")
        print(f"   • X-Frame-Options: {'✅' if headers.x_frame_options else '❌'}")
        print(f"   • X-Content-Type-Options: {'✅' if headers.x_content_type_options else '❌'}")
        
        # HTTPS enforcement
        https = technical_results.https_enforcement
        print(f"🔐 HTTPS Enforcement:")
        print(f"   • HTTPS Enforced: {'✅' if https.enforced else '❌'}")
        print(f"   • TLS Version: {https.tls_version or 'Unknown'}")
        print(f"   • Certificate Valid: {'✅' if https.certificate_valid else '❌'}")
        
        # SEO signals
        seo = technical_results.seo_signals
        print(f"📈 SEO Signals:")
        print(f"   • robots.txt: {'✅' if seo.robots_txt.get('present') else '❌'}")
        print(f"   • sitemap.xml: {'✅' if seo.sitemap_xml.get('present') else '❌'}")
        
        # JavaScript errors
        js_errors = technical_results.javascript_errors
        print(f"⚠️  JavaScript: {js_errors.error_count} errors, {js_errors.warning_count} warnings")
        
        # Store cost records in database
        if technical_results.cost_records:
            from src.core.database import get_db
            
            async with get_db() as db:
                for cost_record in technical_results.cost_records:
                    db.add(cost_record)
                await db.commit()
            
            print(f"💰 Cost: ${technical_results.cost_records[0].cost_cents / 100:.4f}")
        
        return technical_results
        
    except Exception as e:
        print(f"❌ Technical assessment failed: {e}")
        return None

async def run_gbp_assessment(lead_id: int):
    """Run Google Business Profile assessment for Tuome."""
    
    print("\n📍 Running Google Business Profile Assessment")
    print("-" * 40)
    
    try:
        from src.assessments.gbp_integration import assess_google_business_profile, GBPIntegrationError
        
        start_time = datetime.now()
        
        # Execute GBP assessment
        gbp_results = await assess_google_business_profile(
            business_name="Tuome",
            address="123 Broadway",
            city="New York", 
            state="NY",
            lead_id=lead_id
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Display results
        print(f"✅ GBP assessment completed in {duration:.2f}s")
        print(f"📊 Results:")
        print(f"   • Match found: {gbp_results.get('match_found', False)}")
        print(f"   • Confidence: {gbp_results.get('match_confidence', 0):.2f}")
        print(f"   • Search results: {gbp_results.get('search_results_count', 0)}")
        
        gbp_data = gbp_results.get('gbp_data', {})
        
        if gbp_results.get('match_found'):
            print(f"🏪 Business Details:")
            print(f"   • Name: {gbp_data.get('name', 'N/A')}")
            print(f"   • Address: {gbp_data.get('formatted_address', 'N/A')}")
            print(f"   • Phone: {gbp_data.get('phone_number', 'N/A')}")
            print(f"   • Website: {gbp_data.get('website', 'N/A')}")
            
            reviews = gbp_data.get('reviews', {})
            print(f"⭐ Reviews: {reviews.get('total_reviews', 0)} ({reviews.get('average_rating', 0):.1f}★)")
            
            photos = gbp_data.get('photos', {})
            print(f"📸 Photos: {photos.get('total_photos', 0)}")
            
            hours = gbp_data.get('hours', {})
            regular_hours = hours.get('regular_hours', {})
            if regular_hours:
                print(f"🕒 Hours: {len(regular_hours)} days configured")
            
            status = gbp_data.get('status', {})
            print(f"✅ Status: {'Verified' if status.get('verified') else 'Unverified'}")
        
        # Store cost records in database
        if gbp_results.get("cost_records"):
            from src.core.database import get_db
            
            async with get_db() as db:
                for cost_record in gbp_results["cost_records"]:
                    db.add(cost_record)
                await db.commit()
            
            print(f"💰 Cost: ${gbp_results['cost_records'][0].cost_cents / 100:.4f}")
        
        return gbp_results
        
    except Exception as e:
        print(f"❌ GBP assessment failed: {e}")
        return None

async def store_assessment_results(lead_id: int, pagespeed_results, technical_results, gbp_results):
    """Store all assessment results in the database."""
    
    print("\n💾 Storing Assessment Results in Database")
    print("-" * 40)
    
    try:
        from src.core.database import get_db
        from src.models.lead import Assessment
        from sqlalchemy import select
        
        async with get_db() as db:
            # Check if assessment already exists
            existing_assessment = await db.execute(
                select(Assessment).where(Assessment.lead_id == lead_id)
            )
            assessment = existing_assessment.scalar_one_or_none()
            
            if not assessment:
                # Create new assessment
                assessment = Assessment(
                    lead_id=lead_id,
                    status="completed",
                    total_score=0,  # Will calculate below
                    pagespeed_score=0,
                    security_score=0,
                    mobile_score=0,
                    seo_score=0,
                    created_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc)
                )
                db.add(assessment)
            
            # Store results
            scores = []
            
            if pagespeed_results:
                assessment.pagespeed_data = pagespeed_results
                assessment.pagespeed_score = pagespeed_results.get('performance_score', 0)
                scores.append(assessment.pagespeed_score)
                print(f"✅ PageSpeed data stored (Score: {assessment.pagespeed_score})")
            
            if technical_results:
                # Convert Pydantic models to dict for storage
                technical_data = {
                    "url": technical_results.url,
                    "scan_timestamp": technical_results.analysis_timestamp,
                    "security_headers": {
                        "hsts": technical_results.security_headers.hsts,
                        "csp": technical_results.security_headers.csp,
                        "x_frame_options": technical_results.security_headers.x_frame_options,
                        "x_content_type_options": technical_results.security_headers.x_content_type_options,
                        "referrer_policy": technical_results.security_headers.referrer_policy,
                        "permissions_policy": technical_results.security_headers.permissions_policy
                    },
                    "https_enforcement": {
                        "scheme": technical_results.https_enforcement.scheme,
                        "enforced": technical_results.https_enforcement.enforced,
                        "tls_version": technical_results.https_enforcement.tls_version,
                        "certificate_valid": technical_results.https_enforcement.certificate_valid
                    },
                    "seo_signals": {
                        "robots_txt": technical_results.seo_signals.robots_txt,
                        "sitemap_xml": technical_results.seo_signals.sitemap_xml
                    },
                    "javascript_errors": {
                        "error_count": technical_results.javascript_errors.error_count,
                        "warning_count": technical_results.javascript_errors.warning_count
                    }
                }
                
                assessment.security_headers = technical_data
                
                # Calculate security score (simplified)
                security_score = 0
                if technical_results.https_enforcement.enforced:
                    security_score += 30
                if technical_results.security_headers.hsts:
                    security_score += 20
                if technical_results.security_headers.csp:
                    security_score += 25
                if technical_results.seo_signals.robots_txt.get('present'):
                    security_score += 15
                if technical_results.seo_signals.sitemap_xml.get('present'):
                    security_score += 10
                
                assessment.security_score = min(100, security_score)
                scores.append(assessment.security_score)
                print(f"✅ Technical/Security data stored (Score: {assessment.security_score})")
            
            if gbp_results:
                assessment.gbp_data = gbp_results
                
                # Calculate mobile score based on GBP completeness
                gbp_data = gbp_results.get("gbp_data", {})
                mobile_score = 0
                
                if gbp_results.get("match_found", False):
                    # Score based on data completeness
                    if gbp_data.get('hours', {}).get('regular_hours'):
                        mobile_score += 25
                    if gbp_data.get('reviews', {}).get('total_reviews', 0) > 0:
                        mobile_score += 25
                    if gbp_data.get('photos', {}).get('total_photos', 0) > 0:
                        mobile_score += 20
                    if gbp_data.get('status', {}).get('verified', False):
                        mobile_score += 15
                    if gbp_data.get('formatted_address'):
                        mobile_score += 10
                    if gbp_data.get('phone_number'):
                        mobile_score += 5
                else:
                    mobile_score = 10  # Minimal score for no listing found
                
                assessment.mobile_score = mobile_score
                scores.append(assessment.mobile_score)
                print(f"✅ GBP data stored (Score: {assessment.mobile_score})")
            
            # Calculate total score
            if scores:
                assessment.total_score = int(sum(scores) / len(scores))
                print(f"📊 Total Score: {assessment.total_score}/100")
            
            await db.commit()
            await db.refresh(assessment)
            
            print(f"💾 Assessment stored with ID: {assessment.id}")
            return assessment.id
            
    except Exception as e:
        print(f"❌ Failed to store assessment results: {e}")
        return None

async def verify_database_storage(lead_id: int, assessment_id: int):
    """Verify that data was properly stored in the database."""
    
    print("\n🔍 Verifying Database Storage")
    print("-" * 40)
    
    try:
        from src.core.database import get_db
        from src.models.lead import Lead, Assessment
        from src.models.assessment_cost import AssessmentCost
        from sqlalchemy import select
        
        async with get_db() as db:
            # Fetch lead
            lead_result = await db.execute(select(Lead).where(Lead.id == lead_id))
            lead = lead_result.scalar_one_or_none()
            
            # Fetch assessment
            assessment_result = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
            assessment = assessment_result.scalar_one_or_none()
            
            # Fetch cost records
            cost_result = await db.execute(select(AssessmentCost).where(AssessmentCost.lead_id == lead_id))
            cost_records = cost_result.scalars().all()
            
            if lead and assessment:
                print(f"✅ Lead verified: {lead.company} (ID: {lead.id})")
                print(f"✅ Assessment verified: ID {assessment.id}")
                print(f"   • Status: {assessment.status}")
                print(f"   • Total Score: {assessment.total_score}/100")
                print(f"   • PageSpeed Score: {assessment.pagespeed_score}/100")
                print(f"   • Security Score: {assessment.security_score}/100") 
                print(f"   • Mobile Score: {assessment.mobile_score}/100")
                
                # Check data fields
                data_fields = []
                if assessment.pagespeed_data:
                    data_fields.append("PageSpeed")
                if assessment.security_headers:
                    data_fields.append("Security Headers")
                if assessment.gbp_data:
                    data_fields.append("GBP Data")
                
                print(f"   • Data Fields: {', '.join(data_fields)}")
                
                # Cost records
                if cost_records:
                    total_cost = sum(record.cost_cents for record in cost_records) / 100
                    print(f"💰 Cost Records: {len(cost_records)} records, ${total_cost:.4f} total")
                    
                    for record in cost_records:
                        print(f"   • {record.service_name}: ${record.cost_cents/100:.4f} ({record.response_status})")
                else:
                    print(f"💰 Cost Records: None found")
                
                return True
            else:
                print(f"❌ Verification failed: Lead or Assessment not found")
                return False
                
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return False

async def main():
    """Run comprehensive assessment for Tuome NYC."""
    
    print("🎯 Comprehensive Assessment: Tuome NYC")
    print("=" * 60)
    print("Testing full assessment pipeline with database persistence")
    print()
    
    try:
        # Step 1: Create test lead
        lead_id = await create_test_lead()
        
        # Step 2: Run all assessments
        pagespeed_results = await run_pagespeed_assessment(lead_id, "https://tuome.com")
        technical_results = await run_technical_assessment(lead_id, "https://tuome.com")
        gbp_results = await run_gbp_assessment(lead_id)
        
        # Step 3: Store results in database
        assessment_id = await store_assessment_results(lead_id, pagespeed_results, technical_results, gbp_results)
        
        # Step 4: Verify database storage
        if assessment_id:
            verification_success = await verify_database_storage(lead_id, assessment_id)
        else:
            verification_success = False
        
        # Summary
        print("\n🎯 Assessment Summary")
        print("=" * 60)
        assessments_completed = sum([
            1 if pagespeed_results else 0,
            1 if technical_results else 0, 
            1 if gbp_results else 0
        ])
        
        print(f"✅ Assessments completed: {assessments_completed}/3")
        print(f"💾 Database storage: {'✅ Success' if verification_success else '❌ Failed'}")
        print(f"📊 Lead ID: {lead_id}")
        if assessment_id:
            print(f"📊 Assessment ID: {assessment_id}")
        
        if assessments_completed == 3 and verification_success:
            print("\n🚀 SUCCESS: Full comprehensive assessment completed!")
            print("All data has been stored in the PostgreSQL database.")
        else:
            print(f"\n⚠️  PARTIAL SUCCESS: {assessments_completed}/3 assessments completed")
        
    except Exception as e:
        print(f"\n❌ ASSESSMENT FAILED: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
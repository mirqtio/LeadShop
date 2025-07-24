#!/usr/bin/env python3
"""
Docker-based PageSpeed Integration Demo
Runs inside Docker container to test PRP-003 with proper staging environment
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
from src.assessments.pagespeed import assess_pagespeed, PageSpeedError
from src.core.config import settings

async def get_db_session():
    """Get database session as context manager"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


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
                print("⚠️ Missing 'assessment_costs' table - PRP-003 migration needed")
                
            return True
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def create_test_lead(url: str, company: str = "Docker Demo Company") -> Lead:
    """Create a test lead for PageSpeed analysis"""
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
            source="docker_pagespeed_demo",
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


async def store_assessment_results(lead_id: int, pagespeed_data: dict, score: int):
    """Store PageSpeed results in assessment record"""
    async with AsyncSessionLocal() as db:
        # Extract cost records before storing JSON (they aren't JSON serializable)
        cost_records = pagespeed_data.pop("cost_records", [])
        
        # Update assessment with PageSpeed data
        assessment_result = await db.execute(
            select(Assessment).where(Assessment.lead_id == lead_id)
        )
        assessment = assessment_result.scalar_one_or_none()
        
        if assessment:
            assessment.pagespeed_data = pagespeed_data
            assessment.pagespeed_score = score
            assessment.status = "completed"
            assessment.updated_at = datetime.now(timezone.utc)
            
            await db.commit()
            print(f"💾 Stored PageSpeed results (Score: {score})")
        
        # Store cost records separately
        if cost_records:
            for cost_record in cost_records:
                db.add(cost_record)
            await db.commit()
            print(f"💰 Stored {len(cost_records)} cost records")


async def query_and_display_results(lead_id: int):
    """Query database and display comprehensive PageSpeed results"""
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
        print("\n" + "="*100)
        print("🚀 PAGESPEED INTEGRATION DEMO - DOCKER STAGING RESULTS")
        print("="*100)
        
        print(f"\n🏢 LEAD INFORMATION:")
        print(f"   Company: {lead.company}")
        print(f"   URL: {lead.url}")
        print(f"   Lead ID: {lead.id}")
        print(f"   Source: {lead.source}")
        print(f"   Created: {lead.created_at}")
        
        print(f"\n⚡ PERFORMANCE RESULTS:")
        print(f"   Overall Score: {assessment.pagespeed_score}/100")
        print(f"   Assessment Status: {assessment.status}")
        print(f"   Updated: {assessment.updated_at}")
        
        if assessment.pagespeed_data:
            cwv = assessment.pagespeed_data.get("core_web_vitals", {})
            print(f"\n🎯 CORE WEB VITALS:")
            
            if cwv.get("first_contentful_paint"):
                fcp = cwv["first_contentful_paint"]
                fcp_status = "🟢 Good" if fcp < 1800 else "🟡 Needs Improvement" if fcp < 3000 else "🔴 Poor"
                print(f"   First Contentful Paint: {fcp:.1f}ms {fcp_status}")
                
            if cwv.get("largest_contentful_paint"):
                lcp = cwv["largest_contentful_paint"]
                lcp_status = "🟢 Good" if lcp < 2500 else "🟡 Needs Improvement" if lcp < 4000 else "🔴 Poor"
                print(f"   Largest Contentful Paint: {lcp:.1f}ms {lcp_status}")
                
            if cwv.get("cumulative_layout_shift"):
                cls = cwv["cumulative_layout_shift"]
                cls_status = "🟢 Good" if cls < 0.1 else "🟡 Needs Improvement" if cls < 0.25 else "🔴 Poor"
                print(f"   Cumulative Layout Shift: {cls:.3f} {cls_status}")
                
            if cwv.get("total_blocking_time"):
                tbt = cwv["total_blocking_time"]
                tbt_status = "🟢 Good" if tbt < 200 else "🟡 Needs Improvement" if tbt < 600 else "🔴 Poor"
                print(f"   Total Blocking Time: {tbt:.1f}ms {tbt_status}")
                
            if cwv.get("time_to_interactive"):
                tti = cwv["time_to_interactive"]
                tti_status = "🟢 Good" if tti < 3800 else "🟡 Needs Improvement" if tti < 7300 else "🔴 Poor"
                print(f"   Time to Interactive: {tti:.1f}ms {tti_status}")
            
            print(f"\n📱 ANALYSIS DETAILS:")
            print(f"   Primary Strategy: {assessment.pagespeed_data.get('primary_strategy', 'mobile')}")
            print(f"   API Calls Made: {assessment.pagespeed_data.get('api_calls_made', 0)}")
            
            # Show mobile vs desktop if available
            mobile_data = assessment.pagespeed_data.get("mobile_analysis")
            desktop_data = assessment.pagespeed_data.get("desktop_analysis")
            
            if mobile_data and desktop_data:
                mobile_score = mobile_data.get("core_web_vitals", {}).get("performance_score", 0)
                desktop_score = desktop_data.get("core_web_vitals", {}).get("performance_score", 0)
                print(f"   📱 Mobile Score: {mobile_score}/100")
                print(f"   🖥️ Desktop Score: {desktop_score}/100")
            
            print(f"   Analysis Timestamp: {assessment.pagespeed_data.get('analysis_timestamp', 'N/A')}")
        
        print(f"\n💰 COST TRACKING & BUDGET:")
        total_cost = sum(cost.cost_cents for cost in cost_records)
        print(f"   Total Cost: ${total_cost/100:.4f}")
        print(f"   Cost Records: {len(cost_records)}")
        print(f"   Daily Budget Cap: ${settings.DAILY_BUDGET_CAP}")
        print(f"   Per Lead Cap: ${settings.PER_LEAD_CAP}")
        
        for i, cost in enumerate(cost_records, 1):
            status_emoji = "✅" if cost.response_status == "success" else "❌"
            print(f"   #{i}: ${cost.cost_dollars:.4f} - {cost.response_status} {status_emoji} ({cost.response_time_ms}ms)")
        
        # Calculate budget utilization
        budget_used_pct = (total_cost/100) / settings.DAILY_BUDGET_CAP * 100
        budget_status = "🟢" if budget_used_pct < 50 else "🟡" if budget_used_pct < 80 else "🔴"
        print(f"   Budget Utilization: {budget_used_pct:.2f}% {budget_status}")
        
        print(f"\n🔧 CONFIGURATION:")
        print(f"   API Key Configured: {'✅ Yes' if settings.GOOGLE_PAGESPEED_API_KEY else '❌ No'}")
        print(f"   PageSpeed Enabled: {'✅ Yes' if settings.ENABLE_PAGESPEED else '❌ No'}")
        print(f"   Database URL: {settings.DATABASE_URL[:50]}...")
        
        print("\n" + "="*100)
        print("🎉 DOCKER STAGING DEMO COMPLETED SUCCESSFULLY!")
        print("="*100)


async def run_docker_pagespeed_demo(url: str, company: str = None):
    """Run complete PageSpeed demo in Docker staging environment"""
    print("🐳 DOCKER PAGESPEED INTEGRATION DEMO")
    print("🔗 URL:", url)
    print("🏗️ Environment: Docker Staging")
    
    # Step 1: Check database connection
    print("\n📊 Step 1: Checking database connection...")
    db_ok = await check_database_connection()
    if not db_ok:
        print("❌ Database check failed - cannot proceed")
        return
    
    # Step 2: Check configuration
    print("\n🔧 Step 2: Checking configuration...")
    if not settings.GOOGLE_PAGESPEED_API_KEY:
        print("❌ ERROR: GOOGLE_PAGESPEED_API_KEY not configured")
        print("Please set your Google PageSpeed API key in .env file")
        return
    
    print(f"✅ API Key configured: {settings.GOOGLE_PAGESPEED_API_KEY[:8]}...")
    print(f"✅ PageSpeed enabled: {settings.ENABLE_PAGESPEED}")
    
    try:
        # Step 3: Create test lead
        print("\n📋 Step 3: Creating test lead...")
        lead = await create_test_lead(url, company or f"Docker Demo - {url}")
        
        # Step 4: Create assessment record
        print("\n📊 Step 4: Creating assessment record...")
        assessment = await create_assessment_record(lead.id)
        
        # Step 5: Run PageSpeed analysis
        print("\n⚡ Step 5: Running PageSpeed analysis...")
        print("   🕒 This may take 10-15 seconds for mobile + desktop analysis...")
        print("   📡 Making API calls to Google PageSpeed Insights v5...")
        
        pagespeed_results = await assess_pagespeed(
            url=url, 
            company=lead.company, 
            lead_id=lead.id
        )
        
        performance_score = pagespeed_results.get("performance_score", 0)
        print(f"   ✅ Analysis complete! Performance Score: {performance_score}/100")
        
        # Step 6: Store results
        print("\n💾 Step 6: Storing results in database...")
        await store_assessment_results(lead.id, pagespeed_results, performance_score)
        
        # Step 7: Query and display comprehensive results
        print("\n🔍 Step 7: Querying database and displaying comprehensive results...")
        await query_and_display_results(lead.id)
        
    except PageSpeedError as e:
        print(f"\n❌ PageSpeed API Error: {e}")
        print("This could be due to:")
        print("- Invalid API key")
        print("- Rate limiting (25K daily quota exceeded)")
        print("- Invalid URL")
        print("- Network connectivity issues")
        
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main demo function"""
    # Use the provided URL
    test_url = "https://anthrasite.io"
    test_company = "Anthrasite.io - AI Dev Tools"
    
    # Allow custom URL from command line
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        test_company = f"Docker Demo - {test_url}"
    
    await run_docker_pagespeed_demo(test_url, test_company)


if __name__ == "__main__":
    # Run the Docker demo
    asyncio.run(main())
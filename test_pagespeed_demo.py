#!/usr/bin/env python3
"""
Demo script to test PRP-003 PageSpeed Integration
Runs PageSpeed analysis on an arbitrary URL and stores results in database
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Override database URL for local testing
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://leadfactory:00g2Xyn7HHaEpQ79ldO8oE1sp@localhost:5432/leadfactory_dev'

from src.core.database import get_db
from src.models.lead import Lead, Assessment
from src.models.assessment_cost import AssessmentCost
from src.assessments.pagespeed import assess_pagespeed, PageSpeedError
from src.core.config import settings


async def create_test_lead(url: str, company: str = "Demo Company") -> Lead:
    """Create a test lead for PageSpeed analysis"""
    async with get_db() as db:
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
            source="pagespeed_demo",
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
    async with get_db() as db:
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
    async with get_db() as db:
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
        
        # Store cost records
        if pagespeed_data.get("cost_records"):
            for cost_record in pagespeed_data["cost_records"]:
                db.add(cost_record)
            await db.commit()
            print(f"💰 Stored {len(pagespeed_data['cost_records'])} cost records")


async def query_and_display_results(lead_id: int):
    """Query database and display PageSpeed results"""
    async with get_db() as db:
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
        
        # Display results
        print("\n" + "="*80)
        print("📊 PAGESPEED ANALYSIS RESULTS")
        print("="*80)
        
        print(f"\n🏢 LEAD INFORMATION:")
        print(f"   Company: {lead.company}")
        print(f"   URL: {lead.url}")
        print(f"   Lead ID: {lead.id}")
        print(f"   Created: {lead.created_at}")
        
        print(f"\n⚡ PERFORMANCE RESULTS:")
        print(f"   Overall Score: {assessment.pagespeed_score}/100")
        print(f"   Assessment Status: {assessment.status}")
        print(f"   Updated: {assessment.updated_at}")
        
        if assessment.pagespeed_data:
            cwv = assessment.pagespeed_data.get("core_web_vitals", {})
            print(f"\n🎯 CORE WEB VITALS:")
            
            if cwv.get("first_contentful_paint"):
                print(f"   First Contentful Paint: {cwv['first_contentful_paint']:.1f}ms")
            if cwv.get("largest_contentful_paint"):
                print(f"   Largest Contentful Paint: {cwv['largest_contentful_paint']:.1f}ms")
            if cwv.get("cumulative_layout_shift"):
                print(f"   Cumulative Layout Shift: {cwv['cumulative_layout_shift']:.3f}")
            if cwv.get("total_blocking_time"):
                print(f"   Total Blocking Time: {cwv['total_blocking_time']:.1f}ms")
            if cwv.get("time_to_interactive"):
                print(f"   Time to Interactive: {cwv['time_to_interactive']:.1f}ms")
            
            print(f"\n📱 ANALYSIS DETAILS:")
            print(f"   Primary Strategy: {assessment.pagespeed_data.get('primary_strategy', 'mobile')}")
            print(f"   API Calls Made: {assessment.pagespeed_data.get('api_calls_made', 0)}")
            print(f"   Analysis Timestamp: {assessment.pagespeed_data.get('analysis_timestamp', 'N/A')}")
        
        print(f"\n💰 COST TRACKING:")
        total_cost = sum(cost.cost_cents for cost in cost_records)
        print(f"   Total Cost: ${total_cost/100:.4f}")
        print(f"   Cost Records: {len(cost_records)}")
        
        for i, cost in enumerate(cost_records, 1):
            print(f"   #{i}: ${cost.cost_dollars:.4f} - {cost.response_status} ({cost.response_time_ms}ms)")
        
        print("\n" + "="*80)


async def run_pagespeed_demo(url: str, company: str = None):
    """Run complete PageSpeed demo workflow"""
    print("🚀 Starting PageSpeed Integration Demo")
    print(f"🔗 URL: {url}")
    
    # Check configuration
    if not settings.GOOGLE_PAGESPEED_API_KEY:
        print("❌ ERROR: GOOGLE_PAGESPEED_API_KEY not configured")
        print("Please set your Google PageSpeed API key in environment variables")
        return
    
    print(f"✅ API Key configured: {settings.GOOGLE_PAGESPEED_API_KEY[:8]}...")
    
    try:
        # Step 1: Create test lead
        print("\n📋 Step 1: Creating test lead...")
        lead = await create_test_lead(url, company or "PageSpeed Demo")
        
        # Step 2: Create assessment record
        print("\n📊 Step 2: Creating assessment record...")
        assessment = await create_assessment_record(lead.id)
        
        # Step 3: Run PageSpeed analysis
        print("\n⚡ Step 3: Running PageSpeed analysis...")
        print("   This may take 10-15 seconds for mobile + desktop analysis...")
        
        pagespeed_results = await assess_pagespeed(
            url=url, 
            company=lead.company, 
            lead_id=lead.id
        )
        
        performance_score = pagespeed_results.get("performance_score", 0)
        print(f"   ✅ Analysis complete! Score: {performance_score}/100")
        
        # Step 4: Store results
        print("\n💾 Step 4: Storing results in database...")
        await store_assessment_results(lead.id, pagespeed_results, performance_score)
        
        # Step 5: Query and display results
        print("\n🔍 Step 5: Querying database and displaying results...")
        await query_and_display_results(lead.id)
        
        print("\n🎉 PageSpeed demo completed successfully!")
        
    except PageSpeedError as e:
        print(f"\n❌ PageSpeed API Error: {e}")
        print("This could be due to:")
        print("- Invalid API key")
        print("- Rate limiting")
        print("- Invalid URL")
        print("- Network connectivity issues")
        
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main demo function"""
    # Default to a fast, reliable URL
    test_url = "https://web.dev"
    test_company = "Google Web.dev"
    
    # Allow custom URL from command line
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        test_company = f"Demo for {test_url}"
    
    await run_pagespeed_demo(test_url, test_company)


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())
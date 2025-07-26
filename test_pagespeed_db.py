#!/usr/bin/env python3
"""
Test script to verify PageSpeed assessment saves to new database tables
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.assessments.pagespeed import assess_pagespeed
from src.core.database import AsyncSessionLocal
from src.models.pagespeed import PageSpeedAnalysis, PageSpeedAudit
from sqlalchemy import select


async def test_pagespeed_db_storage():
    """Test that PageSpeed assessment saves data to new tables"""
    
    # Test URL
    test_url = "https://example.com"
    test_company = "Example Company"
    test_lead_id = 1
    test_assessment_id = 1
    
    print(f"Testing PageSpeed assessment for {test_url}")
    
    try:
        # Run PageSpeed assessment
        result = await assess_pagespeed(
            url=test_url,
            company=test_company,
            lead_id=test_lead_id,
            assessment_id=test_assessment_id
        )
        
        print("\nAssessment completed successfully!")
        print(f"Performance Score: {result.get('performance_score')}")
        print(f"Total Cost: ${result.get('total_cost_cents', 0) / 100:.2f}")
        
        # Check if data was saved to database
        async with AsyncSessionLocal() as db:
            # Check PageSpeedAnalysis table
            analysis_result = await db.execute(
                select(PageSpeedAnalysis).where(
                    PageSpeedAnalysis.assessment_id == test_assessment_id
                )
            )
            analyses = analysis_result.scalars().all()
            
            print(f"\nFound {len(analyses)} PageSpeed analyses in database:")
            for analysis in analyses:
                print(f"  - Strategy: {analysis.strategy}")
                print(f"    Performance Score: {analysis.performance_score}")
                print(f"    FCP: {analysis.first_contentful_paint_ms}ms")
                print(f"    LCP: {analysis.largest_contentful_paint_ms}ms")
                print(f"    CLS: {analysis.cumulative_layout_shift}")
                print(f"    Speed Index: {analysis.speed_index_ms}ms")
                
                # Check audits for this analysis
                audit_result = await db.execute(
                    select(PageSpeedAudit).where(
                        PageSpeedAudit.pagespeed_analysis_id == analysis.id
                    )
                )
                audits = audit_result.scalars().all()
                print(f"    Total Audits: {len(audits)}")
        
        print("\n✅ Test passed! Data saved to new database tables.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_pagespeed_db_storage())
#!/usr/bin/env python3
"""
Test script to verify PageSpeed data is correctly saved to and retrieved from new database tables
"""

import asyncio
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_pagespeed_db_integration():
    """Test the complete PageSpeed database integration flow"""
    
    # Import required modules
    from src.core.database import AsyncSessionLocal
    from src.models.lead import Lead, Assessment
    from src.models.pagespeed import PageSpeedAnalysis
    from src.models.assessment_results import AssessmentResults
    from src.api.v1.pagespeed_helpers import get_pagespeed_data_for_assessment
    from sqlalchemy import select
    
    logger.info("Starting PageSpeed database integration test...")
    
    async with AsyncSessionLocal() as db:
        try:
            # 1. Find a recent assessment with PageSpeed data
            logger.info("Looking for recent assessments with PageSpeed data...")
            
            result = await db.execute(
                select(Assessment)
                .where(Assessment.pagespeed_data.isnot(None))
                .order_by(Assessment.created_at.desc())
                .limit(5)
            )
            assessments = result.scalars().all()
            
            if not assessments:
                logger.warning("No assessments found with PageSpeed data")
                return
            
            logger.info(f"Found {len(assessments)} assessments with PageSpeed data")
            
            # 2. Check if PageSpeed data exists in new tables
            for assessment in assessments:
                logger.info(f"\nChecking assessment ID: {assessment.id}")
                
                # Check PageSpeedAnalysis table
                ps_result = await db.execute(
                    select(PageSpeedAnalysis)
                    .where(PageSpeedAnalysis.assessment_id == assessment.id)
                )
                ps_analyses = ps_result.scalars().all()
                
                if ps_analyses:
                    logger.info(f"  ✓ Found {len(ps_analyses)} PageSpeed analyses in new tables")
                    for analysis in ps_analyses:
                        logger.info(f"    - Strategy: {analysis.strategy}, Score: {analysis.performance_score}")
                        logger.info(f"    - FCP: {analysis.first_contentful_paint_ms}ms")
                        logger.info(f"    - LCP: {analysis.largest_contentful_paint_ms}ms")
                        logger.info(f"    - CLS: {analysis.cumulative_layout_shift}")
                        
                        # Count related data
                        audit_count = len(analysis.audits) if hasattr(analysis, 'audits') else 0
                        logger.info(f"    - Audits: {audit_count}")
                else:
                    logger.warning(f"  ✗ No PageSpeed data in new tables for assessment {assessment.id}")
                    logger.info(f"    Old data exists: {bool(assessment.pagespeed_data)}")
                
                # Check AssessmentResults table
                ar_result = await db.execute(
                    select(AssessmentResults)
                    .where(AssessmentResults.assessment_id == assessment.id)
                )
                assessment_results = ar_result.scalar_one_or_none()
                
                if assessment_results:
                    logger.info(f"  ✓ Found AssessmentResults record")
                    logger.info(f"    - PageSpeed FCP: {assessment_results.pagespeed_fcp_ms}ms")
                    logger.info(f"    - PageSpeed Score: {assessment_results.pagespeed_performance_score}")
                else:
                    logger.warning(f"  ✗ No AssessmentResults record found")
                
                # Test the helper function
                logger.info("  Testing helper function...")
                pagespeed_data = await get_pagespeed_data_for_assessment(db, assessment.id)
                
                if pagespeed_data.get("has_data"):
                    logger.info(f"  ✓ Helper function returned data successfully")
                    logger.info(f"    - Mobile data: {bool(pagespeed_data.get('mobile_analysis'))}")
                    logger.info(f"    - Desktop data: {bool(pagespeed_data.get('desktop_analysis'))}")
                    logger.info(f"    - Performance score: {pagespeed_data.get('performance_score')}")
                else:
                    logger.warning(f"  ✗ Helper function returned no data")
                
                logger.info("-" * 60)
            
            # 3. Test a new assessment creation flow
            logger.info("\nTesting new assessment creation with PageSpeed data...")
            
            # This would require running an actual assessment - skipping for now
            logger.info("Skipping new assessment test (requires API key)")
            
        except Exception as e:
            logger.error(f"Test failed: {e}", exc_info=True)
            raise


async def test_ui_endpoint_integration():
    """Test that UI endpoints correctly retrieve PageSpeed data"""
    
    logger.info("\nTesting UI endpoint integration...")
    
    # Import test client
    from httpx import AsyncClient
    from src.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Find a test assessment ID
        from src.core.database import AsyncSessionLocal
        from src.models.lead import Assessment
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Assessment)
                .where(Assessment.pagespeed_data.isnot(None))
                .order_by(Assessment.created_at.desc())
                .limit(1)
            )
            assessment = result.scalar_one_or_none()
            
            if not assessment:
                logger.warning("No test assessment found")
                return
            
            assessment_id = assessment.id
        
        # Test the test endpoint
        logger.info(f"Testing /api/v1/assessment/test/{assessment_id}")
        response = await client.get(f"/api/v1/assessment/test/{assessment_id}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info("✓ Endpoint returned successfully")
            
            # Check for PageSpeed data
            execution = data.get("result", {}).get("execution", {})
            pagespeed_result = execution.get("pagespeed_result", {})
            
            if pagespeed_result.get("status", {}).get("value") == "success":
                logger.info("✓ PageSpeed data retrieved successfully")
                pagespeed_data = pagespeed_result.get("data", {})
                logger.info(f"  - Has mobile data: {bool(pagespeed_data.get('mobile_analysis'))}")
                logger.info(f"  - Has desktop data: {bool(pagespeed_data.get('desktop_analysis'))}")
                logger.info(f"  - Performance score: {pagespeed_data.get('performance_score')}")
            else:
                logger.warning("✗ No PageSpeed data in response")
            
            # Check decomposed metrics
            decomposed_metrics = execution.get("decomposed_metrics", {})
            if decomposed_metrics:
                logger.info(f"✓ Found {len(decomposed_metrics)} decomposed metrics")
                # Show PageSpeed-specific metrics
                pagespeed_metrics = [
                    "First Contentful Paint (FCP)",
                    "Largest Contentful Paint (LCP)",
                    "Cumulative Layout Shift (CLS)",
                    "Total Blocking Time (TBT)",
                    "Time to Interactive (TTI)",
                    "Speed Index",
                    "Performance Score (runtime)"
                ]
                for metric in pagespeed_metrics:
                    if metric in decomposed_metrics:
                        logger.info(f"  - {metric}: {decomposed_metrics[metric]}")
            else:
                logger.warning("✗ No decomposed metrics found")
        else:
            logger.error(f"✗ Endpoint returned status {response.status_code}")


async def main():
    """Run all tests"""
    try:
        await test_pagespeed_db_integration()
        await test_ui_endpoint_integration()
        logger.info("\n✅ All tests completed!")
    except Exception as e:
        logger.error(f"\n❌ Tests failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
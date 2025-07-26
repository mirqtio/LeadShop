#!/usr/bin/env python3
"""Test script for SEMrush integration in orchestrator"""

import asyncio
import logging
from src.assessments.orchestrator_with_security import run_assessments

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_orchestrator_with_semrush():
    """Test the orchestrator with SEMrush assessment included"""
    
    # Test URL
    test_url = "https://www.example.com"
    test_business = "Example Business"
    
    print(f"\n🚀 Testing orchestrator with SEMrush for: {test_url}")
    print("=" * 60)
    
    # Run assessments
    results = await run_assessments(
        url=test_url,
        business_name=test_business,
        assessment_id=1
    )
    
    # Check overall status
    print(f"\nOverall Status: {results.get('status')}")
    
    # Check individual assessments
    assessments = results.get("assessments", {})
    print(f"\nAssessments completed: {list(assessments.keys())}")
    
    # Check SEMrush specifically
    semrush_assessment = assessments.get("semrush", {})
    if semrush_assessment:
        print(f"\nSEMrush Assessment Status: {semrush_assessment.get('status')}")
        if semrush_assessment.get('status') == 'success':
            semrush_data = results.get("semrush_data", {})
            if semrush_data.get("success"):
                print(f"  Domain: {semrush_data.get('domain')}")
                print(f"  Authority Score: {semrush_data.get('authority_score')}")
                print(f"  Organic Traffic: {semrush_data.get('organic_traffic_estimate')}")
                print(f"  Keywords Count: {semrush_data.get('ranking_keywords_count')}")
                print(f"  Site Health: {semrush_data.get('site_health_score')}%")
            
            # Check summary
            semrush_summary = results.get("semrush_summary", {})
            if semrush_summary:
                print(f"\nSEMrush Summary:")
                print(f"  Authority: {semrush_summary.get('authority')}")
                print(f"  Traffic: {semrush_summary.get('traffic')}")
                print(f"  Keywords: {semrush_summary.get('keywords')}")
                print(f"  Health: {semrush_summary.get('health')}%")
                print(f"  Has Issues: {semrush_summary.get('has_issues')}")
        else:
            print(f"  Error: {semrush_assessment.get('error')}")
    else:
        print("\n⚠️  SEMrush assessment not found in results")
    
    # Check other assessments briefly
    print(f"\nOther Assessments:")
    for name, assessment in assessments.items():
        if name != "semrush":
            status = assessment.get('status', 'unknown')
            print(f"  {name}: {status}")
    
    print("\n" + "=" * 60)
    print("✅ Test completed")

if __name__ == "__main__":
    asyncio.run(test_orchestrator_with_semrush())
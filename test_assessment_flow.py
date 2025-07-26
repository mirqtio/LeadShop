#!/usr/bin/env python3
"""
Test the assessment UI flow with mock data
"""

import asyncio
import json
from datetime import datetime

# Import the assessment orchestrator
from src.assessments.assessment_orchestrator import AssessmentOrchestrator

async def test_assessment_flow():
    """Test the assessment flow with a sample URL"""
    
    print("Starting assessment test...")
    
    # Mock lead data
    lead_data = {
        "id": 1,
        "company": "Test Company",
        "website": "https://example.com",
        "address": "123 Main St",
        "city": "San Francisco",
        "state": "CA"
    }
    
    # Create orchestrator
    orchestrator = AssessmentOrchestrator()
    
    # Run assessment
    try:
        print("\n1. Running PageSpeed assessment...")
        pagespeed_result = await orchestrator.run_single_component(
            "pagespeed",
            lead_data["website"],
            lead_data["id"],
            lead_data,
            {}
        )
        print(f"PageSpeed Score: {pagespeed_result.get('performance_score', 'N/A')}")
        
        print("\n2. Running Security assessment...")
        security_result = await orchestrator.run_single_component(
            "security",
            lead_data["website"],
            lead_data["id"],
            lead_data,
            {}
        )
        print(f"Security vulnerabilities: {len(security_result.get('vulnerabilities', []))}")
        
        print("\n3. Running SEO assessment...")
        seo_result = await orchestrator.run_single_component(
            "seo",
            lead_data["website"],
            lead_data["id"],
            lead_data,
            {}
        )
        print(f"SEO Score: {seo_result.get('overall_score', 'N/A')}")
        
        print("\n4. Screenshot capture (will fail without API key)...")
        screenshot_result = await orchestrator.run_single_component(
            "screenshots",
            lead_data["website"],
            lead_data["id"],
            lead_data,
            {}
        )
        print(f"Screenshot success: {screenshot_result.get('success', False)}")
        print(f"Screenshot error: {screenshot_result.get('error_message', 'None')}")
        
        print("\n✅ Assessment test completed successfully!")
        
        # Print summary
        print("\n" + "="*50)
        print("ASSESSMENT SUMMARY")
        print("="*50)
        print(f"Website: {lead_data['website']}")
        print(f"Company: {lead_data['company']}")
        print(f"Components tested: 4")
        print("\nResults:")
        print(f"- PageSpeed: {'✓' if pagespeed_result else '✗'}")
        print(f"- Security: {'✓' if security_result else '✗'}")
        print(f"- SEO: {'✓' if seo_result else '✗'}")
        print(f"- Screenshots: {'✓' if screenshot_result.get('success') else '✗'}")
        
    except Exception as e:
        print(f"\n❌ Error during assessment: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_assessment_flow())
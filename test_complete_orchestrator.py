#!/usr/bin/env python3
"""
Test the complete assessment orchestrator with all components
"""

import asyncio
import json
from src.assessments.orchestrator_with_security import run_assessments


async def test_orchestrator():
    """Test the complete assessment pipeline"""
    # Test data
    test_url = "https://example.com"
    test_business = "Example Business"
    test_assessment_id = 1
    
    print(f"Testing complete assessment pipeline for: {test_url}")
    print(f"Business: {test_business}")
    print(f"Assessment ID: {test_assessment_id}")
    print("-" * 80)
    
    try:
        # Run the assessments
        results = await run_assessments(
            url=test_url,
            business_name=test_business,
            assessment_id=test_assessment_id,
            city="San Francisco",
            state="CA"
        )
        
        # Display results
        print("\n=== ASSESSMENT RESULTS ===\n")
        
        # Overall status
        print(f"Status: {results.get('status')}")
        print(f"URL: {results.get('url')}")
        print(f"Business: {results.get('business_name')}")
        print(f"Assessment ID: {results.get('assessment_id')}")
        
        # Individual assessment statuses
        print("\n=== Assessment Statuses ===")
        for name, data in results.get("assessments", {}).items():
            status = data.get("status", "unknown")
            error = data.get("error", "")
            print(f"- {name}: {status} {f'({error})' if error else ''}")
        
        # PageSpeed data
        if "pagespeed_data" in results:
            print("\n=== PageSpeed Data ===")
            ps_data = results["pagespeed_data"]
            print(f"Mobile Score: {ps_data.get('mobile_score', 'N/A')}")
            print(f"Desktop Score: {ps_data.get('desktop_score', 'N/A')}")
        
        # Security data
        if "security_data" in results:
            print("\n=== Security Data ===")
            sec_data = results["security_data"]
            print(f"Headers Found: {len(sec_data.get('headers_found', {}))}")
            print(f"Missing Headers: {len(sec_data.get('missing_headers', []))}")
            print(f"Security Score: {sec_data.get('security_score', 'N/A')}")
        
        # GBP data
        if "gbp_summary" in results:
            print("\n=== Google Business Profile ===")
            gbp = results["gbp_summary"]
            print(f"Found: {gbp.get('found', False)}")
            print(f"Name: {gbp.get('name', 'N/A')}")
            print(f"Rating: {gbp.get('rating', 'N/A')} ({gbp.get('review_count', 0)} reviews)")
        
        # Screenshot data
        if "screenshot_data" in results:
            print("\n=== Screenshot Capture ===")
            ss_data = results["screenshot_data"]
            print(f"Success: {ss_data.get('success', False)}")
            print(f"Desktop Captured: {ss_data.get('desktop', {}).get('captured', False)}")
            print(f"Mobile Captured: {ss_data.get('mobile', {}).get('captured', False)}")
            if ss_data.get('error_message'):
                print(f"Error: {ss_data['error_message']}")
        
        # Visual Analysis data
        if "visual_analysis_data" in results:
            print("\n=== Visual Analysis ===")
            va_data = results["visual_analysis_data"]
            if va_data.get("success"):
                print(f"Overall UX Score: {va_data.get('overall_ux_score', 'N/A')}/2.0")
                print(f"Critical Issues: {len(va_data.get('critical_issues', []))}")
                print(f"Positive Elements: {len(va_data.get('positive_elements', []))}")
                
                # Show rubric scores
                if "rubric_summary" in va_data:
                    print("\nUX Rubric Scores:")
                    for rubric_name, rubric_data in va_data["rubric_summary"].items():
                        score = rubric_data.get("score", 0)
                        print(f"  - {rubric_name}: {score}/2")
            else:
                print(f"Failed: {va_data.get('error_message', 'Unknown error')}")
        
        # Save full results to file
        with open("test_orchestrator_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        print("\n\nFull results saved to: test_orchestrator_results.json")
        
    except Exception as e:
        print(f"\nError running assessments: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_orchestrator())
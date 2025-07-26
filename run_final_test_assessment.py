#!/usr/bin/env python3
"""
Run final test assessment with all fixes applied
"""

import requests
import json
import time

def run_test_assessment():
    """Run assessment for a reliable URL"""
    
    print("🚀 Starting assessment with all fixes applied...")
    
    # Use stackoverflow.com which should work with PageSpeed
    assessment_data = {
        "url": "https://www.stackoverflow.com",
        "business_name": "Stack Overflow",
        "city": "New York",
        "state": "NY"
    }
    
    print(f"📤 Submitting assessment: {json.dumps(assessment_data, indent=2)}")
    
    response = requests.post(
        "http://localhost:8001/api/v1/simple-assessment/execute",
        json=assessment_data,
        timeout=300  # 5 minute timeout
    )
    
    if response.status_code == 200:
        print("✅ Assessment completed successfully!")
        result = response.json()
        
        # Extract assessment ID from response
        if 'assessment_id' in result:
            assessment_id = result['assessment_id']
        elif 'results' in result and 'assessment_id' in result['results']:
            assessment_id = result['results']['assessment_id']
        else:
            # Try to find it in the response
            import re
            match = re.search(r'assessment_id["\s:]+(\d+)', str(result))
            if match:
                assessment_id = int(match.group(1))
            else:
                print("❌ Could not find assessment_id in response")
                print(f"Response: {json.dumps(result, indent=2)}")
                return None
        
        print(f"📊 Assessment ID: {assessment_id}")
        
        # Show summary
        if 'results' in result:
            results = result['results']
            print("\n📊 Assessment Summary:")
            
            if 'pagespeed_data' in results and results['pagespeed_data']:
                ps_data = results['pagespeed_data']
                print(f"  ✅ PageSpeed Mobile Score: {ps_data.get('mobile_score', 'N/A')}")
                print(f"  ✅ PageSpeed Desktop Score: {ps_data.get('desktop_score', 'N/A')}")
            
            if 'security_data' in results and results['security_data']:
                sec_data = results['security_data']
                print(f"  ✅ Security Score: {sec_data.get('security_score', 'N/A')}")
            
            if 'gbp_summary' in results and results['gbp_summary']:
                gbp = results['gbp_summary']
                if gbp.get('found'):
                    print(f"  ✅ GBP Found: Yes (confidence: {gbp.get('confidence', 0):.0%})")
                else:
                    print(f"  ❌ GBP: Not found")
            
            if 'screenshot_data' in results:
                print(f"  ✅ Screenshots: Captured")
            
            if 'semrush_data' in results and results['semrush_data']:
                sem = results['semrush_data']
                if sem.get('success'):
                    print(f"  ✅ SEMrush: Authority Score {sem.get('authority_score', 'N/A')}")
                else:
                    print(f"  ⚠️ SEMrush: {sem.get('error', 'Failed')}")
        
        return assessment_id
    else:
        print(f"❌ Assessment failed: {response.status_code}")
        print(f"Response: {response.text[:500]}")
    
    return None

if __name__ == "__main__":
    assessment_id = run_test_assessment()
    
    if assessment_id:
        print(f"\n✅ Assessment {assessment_id} completed!")
        print(f"Next: Run capture script with assessment ID {assessment_id}")
#!/usr/bin/env python3
"""
Run a real assessment and capture results
"""

import requests
import json
import time

# Test with a simple site
url = "https://www.w3.org"
business_name = "W3C"

print(f"Running assessment for: {url}")
print(f"Business name: {business_name}")
print("-" * 50)

# Submit assessment
print("\nSubmitting assessment...")
response = requests.post(
    "http://localhost:8000/api/v1/simple-assessment/execute",
    json={
        "url": url,
        "business_name": business_name
    }
)

if response.status_code == 200:
    result = response.json()
    print("\n✅ Assessment completed successfully!")
    print(f"\nAssessment ID: {result.get('assessment_id')}")
    print(f"Status: {result.get('status')}")
    
    # Save results
    with open('real_assessment_results.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    # Display results
    if 'results' in result:
        results = result['results']
        print("\n" + "="*50)
        print("ASSESSMENT RESULTS")
        print("="*50)
        
        # PageSpeed
        if results.get('pagespeed_data'):
            ps = results['pagespeed_data']
            print(f"\n⚡ PageSpeed:")
            print(f"   Mobile Score: {ps.get('mobile_score')}/100")
            print(f"   Desktop Score: {ps.get('desktop_score')}/100")
        
        # Security
        if results.get('security_data'):
            sec = results['security_data']
            print(f"\n🛡️ Security:")
            print(f"   Score: {sec.get('score')}/100")
            print(f"   HTTPS: {'Yes' if sec.get('https_enabled') else 'No'}")
            print(f"   Headers: {sec.get('headers_present')}/{sec.get('headers_total')}")
        
        # SEMrush
        if results.get('semrush_data'):
            sem = results['semrush_data']
            print(f"\n🔍 SEMrush:")
            print(f"   Authority: {sem.get('domain_authority')}/100")
            print(f"   Traffic: {sem.get('organic_traffic'):,}")
            print(f"   Keywords: {sem.get('organic_keywords'):,}")
        
        # GBP
        if results.get('gbp_data'):
            gbp = results['gbp_data']
            print(f"\n🏢 Google Business Profile:")
            print(f"   Found: {'Yes' if gbp else 'No'}")
            if gbp and gbp.get('rating'):
                print(f"   Rating: {gbp.get('rating')}/5.0")
                print(f"   Reviews: {gbp.get('review_count')}")
        
        # Screenshots
        if results.get('screenshot_data'):
            screenshots = results['screenshot_data']
            print(f"\n📸 Screenshots:")
            print(f"   Captured: {len(screenshots)} screenshots")
        
        print("\n" + "="*50)
        print("✅ Assessment tool is working correctly!")
        print("="*50)
else:
    print(f"\n❌ Error: {response.status_code}")
    print(response.text)
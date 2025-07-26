#!/usr/bin/env python3
"""
Test simple assessment API
"""

import requests
import time
import json

# Test data
url = "https://www.spotify.com"
business_name = "Spotify"

print(f"Testing assessment for: {url}")
print(f"Business name: {business_name}")

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
    
    if 'results' in result:
        results = result['results']
        
        # PageSpeed data
        if 'pagespeed_data' in results and results['pagespeed_data']:
            ps = results['pagespeed_data']
            print("\n📊 PageSpeed Results:")
            print(f"  Mobile Score: {ps.get('mobile_score')}/100")
            print(f"  Desktop Score: {ps.get('desktop_score')}/100")
        
        # Security data  
        if 'security_data' in results and results['security_data']:
            sec = results['security_data']
            print("\n🛡️ Security Results:")
            print(f"  Security Score: {sec.get('score')}/100")
            print(f"  HTTPS Enabled: {'✅' if sec.get('https_enabled') else '❌'}")
        
        # SEMrush data
        if 'semrush_data' in results and results['semrush_data']:
            sem = results['semrush_data']
            print("\n🔍 SEMrush Results:")
            print(f"  Domain Authority: {sem.get('domain_authority')}")
            print(f"  Organic Traffic: {sem.get('organic_traffic'):,}")
            print(f"  Keywords: {sem.get('organic_keywords'):,}")
        
        # GBP data
        if 'gbp_data' in results and results['gbp_data']:
            gbp = results['gbp_data']
            if gbp.get('rating'):
                print("\n🏢 Google Business Profile:")
                print(f"  Rating: {gbp.get('rating')}/5.0")
                print(f"  Reviews: {gbp.get('review_count')}")
        
        # Screenshots
        if 'screenshot_data' in results and results['screenshot_data']:
            screenshots = results['screenshot_data']
            print(f"\n📸 Screenshots: {len(screenshots)} captured")
    
    # Save full results
    with open('assessment_results.json', 'w') as f:
        json.dump(result, f, indent=2)
    print("\n💾 Full results saved to: assessment_results.json")
    
else:
    print(f"\n❌ Error: {response.status_code}")
    print(response.text)
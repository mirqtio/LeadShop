#!/usr/bin/env python3
"""
Test assessment with google.com - a reliable URL that should work for all assessments
"""

import requests
import json
import time

def run_google_assessment():
    """Run assessment for google.com and track the results"""
    
    print("🚀 Starting assessment for google.com...")
    
    # Submit assessment
    assessment_data = {
        "url": "https://www.google.com",
        "business_name": "Google",
        "city": "Mountain View",
        "state": "CA"
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
        
        # Check what we got
        if 'results' in result and 'assessment_id' in result['results']:
            assessment_id = result['results']['assessment_id']
            print(f"📊 Assessment ID: {assessment_id}")
            
            # Now fetch the results with decomposed scores
            print(f"\n🔍 Fetching decomposed scores for assessment {assessment_id}...")
            
            db_response = requests.get(
                f"http://localhost:8001/api/v1/simple-assessment/results/{assessment_id}"
            )
            
            if db_response.status_code == 200:
                db_data = db_response.json()
                
                # Check decomposed scores
                if 'decomposed_scores' in db_data and db_data['decomposed_scores']:
                    scores = db_data['decomposed_scores']
                    non_null = {k: v for k, v in scores.items() if v is not None}
                    print(f"\n✅ Decomposed metrics extracted: {len(non_null)} / 53")
                    
                    # Show metrics by category
                    categories = {
                        'PageSpeed': [k for k in non_null.keys() if 'pagespeed' in k.lower()],
                        'Security': [k for k in non_null.keys() if 'security' in k.lower() or 'tech_' in k or 'HTTPS' in k or 'TLS' in k or 'HSTS' in k],
                        'GBP': [k for k in non_null.keys() if 'gbp_' in k or k in ['hours', 'review_count', 'rating', 'photos_count']],
                        'SEMrush': [k for k in non_null.keys() if 'semrush' in k.lower() or 'Site Health' in k or 'Domain Authority' in k],
                        'Visual': [k for k in non_null.keys() if 'visual' in k.lower() or 'Screenshot' in k],
                        'Content': [k for k in non_null.keys() if 'content' in k.lower()]
                    }
                    
                    for category, keys in categories.items():
                        if keys:
                            print(f"\n📋 {category} Metrics ({len(keys)}):")
                            for key in keys:
                                print(f"  - {key}: {non_null[key]}")
                    
                    return assessment_id
                else:
                    print("❌ No decomposed scores found in database response")
            else:
                print(f"❌ Failed to fetch results from database: {db_response.status_code}")
        
        # Show raw results summary
        if 'results' in result:
            results = result['results']
            print("\n📊 Assessment Summary:")
            
            if 'pagespeed_data' in results and results['pagespeed_data']:
                ps_data = results['pagespeed_data']
                if 'mobile_score' in ps_data:
                    print(f"  - PageSpeed Mobile Score: {ps_data.get('mobile_score', 'N/A')}")
                if 'desktop_score' in ps_data:
                    print(f"  - PageSpeed Desktop Score: {ps_data.get('desktop_score', 'N/A')}")
            
            if 'security_data' in results and results['security_data']:
                sec_data = results['security_data']
                print(f"  - Security Score: {sec_data.get('security_score', 'N/A')}")
                print(f"  - HTTPS: {sec_data.get('has_https', 'N/A')}")
            
            if 'gbp_summary' in results and results['gbp_summary']:
                gbp = results['gbp_summary']
                if gbp.get('found'):
                    print(f"  - GBP Found: Yes (confidence: {gbp.get('confidence', 0):.0%})")
                    print(f"  - GBP Rating: {gbp.get('rating', 'N/A')}")
                else:
                    print(f"  - GBP Found: No")
            
            if 'semrush_data' in results and results['semrush_data']:
                sem = results['semrush_data']
                if sem.get('success'):
                    print(f"  - Domain Authority: {sem.get('authority_score', 'N/A')}")
                    print(f"  - Organic Traffic: {sem.get('organic_traffic_estimate', 'N/A')}")
    else:
        print(f"❌ Assessment failed: {response.status_code}")
        print(f"Response: {response.text[:500]}")

if __name__ == "__main__":
    assessment_id = run_google_assessment()
    
    if assessment_id:
        print(f"\n✅ Assessment {assessment_id} completed!")
        print(f"View results at: http://localhost:8001/api/v1/simple-assessment/results/{assessment_id}")
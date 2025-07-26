#!/usr/bin/env python3
"""
Test SEMrush with Google to verify parsing fixes
"""

import requests
import json
import time

def test_semrush_parsing():
    """Test SEMrush with Google"""
    
    print("🚀 Testing SEMrush parsing fixes with Google...")
    
    assessment_data = {
        "url": "https://www.google.com",
        "business_name": "Google",
        "city": "Mountain View",
        "state": "CA"
    }
    
    print(f"📤 Submitting assessment for {assessment_data['business_name']}...")
    
    response = requests.post(
        "http://localhost:8001/api/v1/simple-assessment/execute",
        json=assessment_data,
        timeout=120
    )
    
    if response.status_code == 200:
        print("✅ Assessment completed!")
        result = response.json()
        
        # Check for SEMrush data
        if 'results' in result:
            results = result['results']
            print("\n📊 SEMrush Data Extraction:")
            
            # Check raw SEMrush data
            if 'semrush_data' in results and results['semrush_data']:
                sem = results['semrush_data']
                if sem.get('success'):
                    print(f"  ✅ Success: {sem.get('success')}")
                    print(f"  📈 Authority Score: {sem.get('authority_score', 'N/A')}")
                    print(f"  🌐 Domain Rank: {sem.get('domain_rank', 'N/A')}")
                    print(f"  🚗 Organic Traffic: {sem.get('organic_traffic', 'N/A'):,}" if sem.get('organic_traffic') else "  🚗 Organic Traffic: N/A")
                    print(f"  🔑 Keywords Count: {sem.get('keywords_count', 'N/A'):,}" if sem.get('keywords_count') else "  🔑 Keywords Count: N/A")
                    print(f"  ❤️ Site Health: {sem.get('site_health', 'N/A')}%")
                else:
                    print(f"  ❌ Failed: {sem.get('error', 'Unknown error')}")
            
            # Get assessment ID for detailed check
            assessment_id = results.get('assessment_id')
            if assessment_id:
                print(f"\n📋 Assessment ID: {assessment_id}")
                return assessment_id
        
        return None
    else:
        print(f"❌ Assessment failed: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return None


def check_decomposed_scores(assessment_id):
    """Check decomposed scores after processing"""
    
    print(f"\n🔍 Checking decomposed scores for assessment {assessment_id}...")
    
    response = requests.get(
        f"http://localhost:8001/api/v1/simple-assessment/results/{assessment_id}"
    )
    
    if response.status_code == 200:
        data = response.json()
        if 'decomposed_scores' in data:
            scores = data['decomposed_scores']
            
            print("\n📊 SEMrush Decomposed Scores:")
            semrush_found = False
            
            for key, value in scores.items():
                if 'semrush' in key.lower() or 'authority' in key.lower() or 'domain' in key.lower():
                    print(f"  {key}: {value}")
                    semrush_found = True
            
            if not semrush_found:
                print("  ⚠️ No SEMrush metrics found in decomposed scores")
            
            return semrush_found
    
    return False


if __name__ == "__main__":
    # Wait for app to be ready
    time.sleep(10)
    
    assessment_id = test_semrush_parsing()
    
    if assessment_id:
        # Wait for decomposition
        print("\n⏳ Waiting for score decomposition...")
        time.sleep(5)
        
        if check_decomposed_scores(assessment_id):
            print("\n✅ SEMrush parsing is now working correctly!")
        else:
            print("\n⚠️ SEMrush data may not be fully integrated yet")
    
    print("\n📝 Summary:")
    print("1. Fixed semicolon separator parsing (was looking for tabs)")
    print("2. Fixed field positions for domain_ranks response")
    print("3. Updated authority score calculation from domain rank")
    print("4. Fixed organic traffic and keywords extraction")
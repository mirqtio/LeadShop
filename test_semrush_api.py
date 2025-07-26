"""Test SEMrush API integration directly."""

import asyncio
import httpx
import json
import time

async def test_semrush_api():
    """Test SEMrush integration through the API endpoint"""
    
    # Use a test domain for quick testing
    test_url = f"https://testsite{int(time.time())}.com"
    
    async with httpx.AsyncClient() as client:
        try:
            print(f"Testing SEMrush with URL: {test_url}")
            
            # Submit assessment request
            response = await client.post(
                "http://localhost:8001/api/v1/simple-assessment/execute",
                json={
                    "url": test_url,
                    "business_name": "SEMrush API Test"
                },
                timeout=60.0
            )
            
            if response.status_code != 200:
                print(f"❌ API returned status {response.status_code}")
                print(f"Response: {response.text}")
                return
            
            data = response.json()
            print(f"✓ Assessment completed successfully")
            print(f"  Status: {data.get('status')}")
            
            # Get assessment_id from results
            results = data.get('results', {})
            assessment_id = results.get('assessment_id')
            print(f"  Assessment ID: {assessment_id}")
            print(f"  Full response keys: {list(data.keys())}")
            print(f"  Results keys: {list(results.keys())}")
            
            # Check if SEMrush data is in the response
            semrush_data = results.get('semrush_data')
            
            if not semrush_data:
                print("❌ No SEMrush data in response")
                print(f"Available keys: {list(results.keys())}")
                return
            
            if semrush_data.get('success'):
                print("✅ SEMrush data retrieved successfully!")
                print(f"  Domain: {semrush_data.get('domain')}")
                print(f"  Authority Score: {semrush_data.get('authority_score')}/100")
                print(f"  Organic Traffic: {semrush_data.get('organic_traffic_estimate')} visitors/month")
                print(f"  Keywords: {semrush_data.get('ranking_keywords_count')}")
                print(f"  Site Health: {semrush_data.get('site_health_score')}%")
                print(f"  Backlink Toxicity: {semrush_data.get('backlink_toxicity_score')}%")
                
                if semrush_data.get('technical_issues'):
                    print(f"  Technical Issues: {len(semrush_data['technical_issues'])}")
                    for issue in semrush_data['technical_issues'][:3]:  # Show first 3
                        print(f"    - {issue['severity']}: {issue['description']}")
                
                # Now verify data was saved to DB by fetching from DB endpoint
                if assessment_id:
                    print("\nVerifying data was saved to database...")
                    await asyncio.sleep(2)  # Give DB time to commit
                    
                    db_response = await client.get(
                        f"http://localhost:8001/api/v1/simple-assessment/results/{assessment_id}",
                        timeout=30.0
                    )
                    
                    if db_response.status_code == 200:
                        db_data = db_response.json()
                        db_semrush = db_data.get('semrush_data')
                        
                        if db_semrush and db_semrush.get('authority_score') == semrush_data.get('authority_score'):
                            print("✅ SEMrush data successfully saved to and retrieved from database!")
                        else:
                            print("❌ SEMrush data mismatch between API and database")
                    else:
                        print(f"❌ Failed to fetch from DB: {db_response.status_code}")
                
            else:
                print(f"❌ SEMrush analysis failed: {semrush_data.get('error_message')}")
                
        except Exception as e:
            print(f"❌ Test failed with error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_semrush_api())
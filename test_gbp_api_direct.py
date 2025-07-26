#!/usr/bin/env python3
"""
Direct API test for GBP assessment functionality
Tests the assessment API directly without going through the UI
"""

import asyncio
import httpx
import json
import psycopg2
from datetime import datetime
import time

# API configuration
API_BASE_URL = "http://localhost:8001"
API_ENDPOINT = "/api/v1/assessment/execute"

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "leadfactory",
    "user": "leadfactory",
    "password": "00g2Xyn7HHaEpQ79ldO8oE1sp"
}

async def test_gbp_assessment_api():
    """Test GBP assessment through direct API call"""
    
    # Test data
    test_url = "https://www.starbucks.com"
    test_business_name = "Starbucks Coffee Company"
    
    print(f"[{datetime.now()}] Starting GBP API test...")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Submit assessment request
        print(f"[{datetime.now()}] Submitting assessment request...")
        print(f"  URL: {test_url}")
        print(f"  Business: {test_business_name}")
        
        try:
            # Try without authentication first (testing mode)
            response = await client.post(
                f"{API_BASE_URL}{API_ENDPOINT}",
                json={
                    "url": test_url,
                    "business_name": test_business_name
                },
                headers={
                    "Content-Type": "application/json",
                    # Skip auth header for testing
                }
            )
            
            if response.status_code == 401:
                # Try with test token
                print(f"[{datetime.now()}] Authentication required, using test token...")
                response = await client.post(
                    f"{API_BASE_URL}{API_ENDPOINT}",
                    json={
                        "url": test_url,
                        "business_name": test_business_name
                    },
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer test-token"
                    }
                )
            
            print(f"[{datetime.now()}] Response status: {response.status_code}")
            print(f"[{datetime.now()}] Response body: {response.text[:500]}")
            
            if response.status_code != 200:
                print(f"[{datetime.now()}] ✗ Assessment submission failed")
                return
            
            result = response.json()
            task_id = result.get('task_id')
            
            if not task_id:
                print(f"[{datetime.now()}] ✗ No task ID returned")
                return
            
            print(f"[{datetime.now()}] ✓ Assessment started - Task ID: {task_id}")
            
            # Poll for status
            print(f"[{datetime.now()}] Polling for assessment completion...")
            
            start_time = time.time()
            timeout = 120  # 2 minutes timeout
            
            while time.time() - start_time < timeout:
                status_response = await client.get(
                    f"{API_BASE_URL}/api/v1/assessment/status/{task_id}",
                    headers={
                        "Authorization": "Bearer test-token"
                    }
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    status = status_data.get('status')
                    
                    print(f"[{datetime.now()}] Status: {status}")
                    
                    if status == 'completed':
                        print(f"[{datetime.now()}] ✓ Assessment completed!")
                        
                        # Get the results
                        assessment_result = status_data.get('result')
                        if assessment_result:
                            print_assessment_results(assessment_result)
                            
                            # Check database
                            verify_database_gbp_data(test_business_name)
                        break
                        
                    elif status == 'failed':
                        print(f"[{datetime.now()}] ✗ Assessment failed: {status_data.get('error')}")
                        break
                    
                    elif status == 'in_progress' and status_data.get('progress'):
                        progress = status_data['progress']
                        if progress.get('components'):
                            print(f"[{datetime.now()}] Progress:")
                            for comp, comp_status in progress['components'].items():
                                status_val = comp_status.get('status', {}).get('value', 'unknown')
                                print(f"  - {comp}: {status_val}")
                
                await asyncio.sleep(5)  # Poll every 5 seconds
            
            if time.time() - start_time >= timeout:
                print(f"[{datetime.now()}] ✗ Assessment timed out after {timeout} seconds")
                
        except Exception as e:
            print(f"[{datetime.now()}] ✗ Error during assessment: {e}")
            import traceback
            traceback.print_exc()

def print_assessment_results(result):
    """Print assessment results focusing on GBP data"""
    print(f"\n[{datetime.now()}] Assessment Results:")
    
    execution = result.get('execution', result)
    
    # Check GBP results
    if 'gbp_result' in execution:
        gbp = execution['gbp_result']
        print(f"\n  Google Business Profile:")
        print(f"    Status: {gbp.get('status', {}).get('value', 'unknown')}")
        
        if gbp.get('data'):
            data = gbp['data']
            print(f"    Business Found: {data.get('place_found', False)}")
            print(f"    Business Name: {data.get('name', 'N/A')}")
            print(f"    Rating: {data.get('rating', 'N/A')}")
            print(f"    Total Reviews: {data.get('user_ratings_total', 0)}")
            print(f"    Business Status: {data.get('business_status', 'N/A')}")
            print(f"    Address: {data.get('formatted_address', 'N/A')}")
            
    # Check decomposed metrics
    if 'decomposed_metrics' in execution:
        metrics = execution['decomposed_metrics']
        print(f"\n  GBP Decomposed Metrics:")
        gbp_metrics = {
            'hours': 'Business Hours',
            'review_count': 'Review Count',
            'rating': 'Rating',
            'photos_count': 'Photos Count',
            'total_reviews': 'Total Reviews',
            'avg_rating': 'Average Rating',
            'recent_90d': 'Recent 90d Reviews',
            'rating_trend': 'Rating Trend',
            'is_closed': 'Is Closed'
        }
        
        for key, label in gbp_metrics.items():
            if key in metrics:
                print(f"    {label}: {metrics[key]}")

def verify_database_gbp_data(business_name):
    """Verify GBP data was saved to database"""
    
    print(f"\n[{datetime.now()}] Checking database for GBP data...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Query for recent GBP analysis
        cur.execute("""
            SELECT 
                ga.id,
                ga.assessment_id,
                ga.business_name,
                ga.place_id,
                ga.formatted_address,
                ga.total_reviews,
                ga.average_rating,
                ga.is_verified,
                ga.primary_category,
                ga.created_at
            FROM gbp_analysis ga
            WHERE ga.created_at >= NOW() - INTERVAL '5 minutes'
            ORDER BY ga.created_at DESC
            LIMIT 1
        """)
        
        result = cur.fetchone()
        
        if result:
            print(f"✓ Found GBP analysis in database:")
            print(f"  - ID: {result[0]}")
            print(f"  - Assessment ID: {result[1]}")
            print(f"  - Business Name: {result[2]}")
            print(f"  - Place ID: {result[3]}")
            print(f"  - Address: {result[4]}")
            print(f"  - Total Reviews: {result[5]}")
            print(f"  - Average Rating: {result[6]}")
            print(f"  - Verified: {result[7]}")
            print(f"  - Category: {result[8]}")
            print(f"  - Created At: {result[9]}")
            
            # Check assessment_results table
            cur.execute("""
                SELECT 
                    gbp_total_reviews,
                    gbp_avg_rating,
                    gbp_recent_90d,
                    gbp_rating_trend,
                    gbp_is_closed
                FROM assessment_results
                WHERE assessment_id = %s
            """, (result[1],))
            
            ar_result = cur.fetchone()
            if ar_result:
                print(f"\n✓ Found GBP data in assessment_results:")
                print(f"  - Total Reviews: {ar_result[0]}")
                print(f"  - Average Rating: {ar_result[1]}")
                print(f"  - Recent 90d Reviews: {ar_result[2]}")
                print(f"  - Rating Trend: {ar_result[3]}")
                print(f"  - Is Closed: {ar_result[4]}")
        else:
            print(f"✗ No recent GBP analysis found in database")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Database error: {e}")

if __name__ == "__main__":
    asyncio.run(test_gbp_assessment_api())
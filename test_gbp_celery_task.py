#!/usr/bin/env python3
"""
Test GBP assessment by calling Celery task directly
"""

import asyncio
import json
import psycopg2
from datetime import datetime
from src.assessment.tasks import full_assessment_orchestrator_task
from celery.result import AsyncResult
import time

# Database connection
DB_CONFIG = {
    "host": "localhost", 
    "port": 5432,
    "database": "leadfactory",
    "user": "leadfactory",
    "password": "00g2Xyn7HHaEpQ79ldO8oE1sp"
}

def test_gbp_celery_task():
    """Test GBP assessment through direct Celery task call"""
    
    # Test data
    test_url = "https://www.starbucks.com"
    test_business_name = "Starbucks Coffee Company"
    
    print(f"[{datetime.now()}] Starting GBP Celery task test...")
    print(f"  URL: {test_url}")
    print(f"  Business: {test_business_name}")
    
    try:
        # Call the Celery task
        result = full_assessment_orchestrator_task.delay(
            url=test_url,
            business_name=test_business_name
        )
        
        task_id = result.id
        print(f"[{datetime.now()}] Task submitted - ID: {task_id}")
        
        # Poll for completion
        start_time = time.time()
        timeout = 120  # 2 minutes
        
        while time.time() - start_time < timeout:
            task_result = AsyncResult(task_id)
            
            if task_result.ready():
                if task_result.successful():
                    print(f"[{datetime.now()}] ✓ Task completed successfully!")
                    
                    # Get the results
                    assessment_result = task_result.result
                    print_assessment_results(assessment_result)
                    
                    # Verify database
                    verify_database_gbp_data(test_business_name)
                    
                    return True
                else:
                    print(f"[{datetime.now()}] ✗ Task failed: {task_result.info}")
                    return False
                    
            print(f"[{datetime.now()}] Task state: {task_result.state}")
            time.sleep(5)
            
        print(f"[{datetime.now()}] ✗ Task timed out after {timeout} seconds")
        return False
        
    except Exception as e:
        print(f"[{datetime.now()}] ✗ Error during task execution: {e}")
        import traceback
        traceback.print_exc()
        return False

def print_assessment_results(result):
    """Print assessment results focusing on GBP data"""
    print(f"\n[{datetime.now()}] Assessment Results:")
    
    if isinstance(result, dict):
        # Check if we have execution data
        execution = result.get('execution', result)
        
        # Look for GBP results
        if 'gbp_result' in execution:
            gbp = execution['gbp_result']
            print(f"\n  Google Business Profile:")
            print(f"    Status: {gbp.get('status', 'unknown')}")
            
            if gbp.get('data'):
                data = gbp['data']
                print(f"    Business Found: {data.get('place_found', False)}")
                if data.get('place_found'):
                    print(f"    Business Name: {data.get('name', 'N/A')}")
                    print(f"    Rating: {data.get('rating', 'N/A')}")
                    print(f"    Total Reviews: {data.get('user_ratings_total', 0)}")
                    print(f"    Business Status: {data.get('business_status', 'N/A')}")
                    print(f"    Address: {data.get('formatted_address', 'N/A')}")
                    
        # Check for GBP metrics
        if 'metrics' in execution:
            metrics = execution['metrics']
            print(f"\n  GBP Metrics in assessment_results:")
            gbp_fields = [
                'gbp_hours', 'gbp_review_count', 'gbp_rating', 
                'gbp_photos_count', 'gbp_total_reviews', 'gbp_avg_rating',
                'gbp_recent_90d', 'gbp_rating_trend', 'gbp_is_closed'
            ]
            for field in gbp_fields:
                if field in metrics:
                    print(f"    {field}: {metrics[field]}")

def verify_database_gbp_data(business_name):
    """Verify GBP data was saved to database"""
    
    print(f"\n[{datetime.now()}] Checking database for GBP data...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Check gbp_analysis table
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
            WHERE ga.created_at >= NOW() - INTERVAL '10 minutes'
            ORDER BY ga.created_at DESC
            LIMIT 1
        """)
        
        result = cur.fetchone()
        
        if result:
            print(f"\n✓ Found GBP analysis in database:")
            print(f"  - ID: {result[0]}")
            print(f"  - Assessment ID: {result[1]}")
            print(f"  - Business Name: {result[2]}")
            print(f"  - Place ID: {result[3]}")
            print(f"  - Address: {result[4]}")
            print(f"  - Total Reviews: {result[5]}")
            print(f"  - Average Rating: {result[6]}")
            print(f"  - Verified: {result[7]}")
            print(f"  - Category: {result[8]}")
            
            # Check assessment_results for GBP fields
            cur.execute("""
                SELECT 
                    gbp_total_reviews,
                    gbp_avg_rating,
                    gbp_recent_90d,
                    gbp_rating_trend,
                    gbp_is_closed,
                    gbp_hours
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
                if ar_result[5]:
                    print(f"  - Business Hours: {json.dumps(ar_result[5], indent=4)}")
        else:
            print(f"\n✗ No recent GBP analysis found in database")
            
            # Check if there are any assessments at all
            cur.execute("""
                SELECT COUNT(*) FROM assessments 
                WHERE created_at >= NOW() - INTERVAL '10 minutes'
            """)
            count = cur.fetchone()[0]
            print(f"  Recent assessments count: {count}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"\n✗ Database error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    success = test_gbp_celery_task()
    print(f"\n[{datetime.now()}] Test {'✓ PASSED' if success else '✗ FAILED'}")
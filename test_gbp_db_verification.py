#!/usr/bin/env python3
"""
Simple test to verify GBP data in the database
Checks if GBP data exists and is properly stored
"""

import psycopg2
import json
from datetime import datetime

# Database connection - use localhost since we're running locally
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "leadfactory",
    "user": "leadfactory",
    "password": "00g2Xyn7HHaEpQ79ldO8oE1sp"
}

def check_gbp_data():
    """Check GBP data in all relevant tables"""
    
    print(f"[{datetime.now()}] Checking GBP data in database...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # 1. Check gbp_analysis table
        print("\n1. Checking gbp_analysis table:")
        cur.execute("""
            SELECT 
                id,
                assessment_id,
                business_name,
                place_id,
                formatted_address,
                total_reviews,
                average_rating,
                is_verified,
                primary_category,
                created_at
            FROM gbp_analysis
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        results = cur.fetchall()
        print(f"   Found {len(results)} GBP analysis records")
        
        for row in results:
            print(f"\n   Record ID: {row[0]}")
            print(f"   - Assessment ID: {row[1]}")
            print(f"   - Business Name: {row[2]}")
            print(f"   - Place ID: {row[3]}")
            print(f"   - Address: {row[4]}")
            print(f"   - Total Reviews: {row[5]}")
            print(f"   - Average Rating: {row[6]}")
            print(f"   - Verified: {row[7]}")
            print(f"   - Category: {row[8]}")
            print(f"   - Created: {row[9]}")
            
            # Check business hours for this record
            cur.execute("""
                SELECT day_of_week, open_time, close_time, is_closed
                FROM gbp_business_hours
                WHERE gbp_analysis_id = %s
                ORDER BY 
                    CASE day_of_week 
                        WHEN 'monday' THEN 1
                        WHEN 'tuesday' THEN 2
                        WHEN 'wednesday' THEN 3
                        WHEN 'thursday' THEN 4
                        WHEN 'friday' THEN 5
                        WHEN 'saturday' THEN 6
                        WHEN 'sunday' THEN 7
                    END
            """, (row[0],))
            
            hours = cur.fetchall()
            if hours:
                print("   - Business Hours:")
                for day, open_time, close_time, is_closed in hours:
                    if is_closed:
                        print(f"     {day.capitalize()}: Closed")
                    else:
                        print(f"     {day.capitalize()}: {open_time} - {close_time}")
        
        # 2. Check assessment_results table for GBP fields
        print("\n2. Checking assessment_results table for GBP fields:")
        cur.execute("""
            SELECT 
                assessment_id,
                gbp_total_reviews,
                gbp_avg_rating,
                gbp_recent_90d,
                gbp_rating_trend,
                gbp_is_closed,
                gbp_hours,
                gbp_found,
                gbp_verified,
                created_at
            FROM assessment_results
            WHERE gbp_total_reviews IS NOT NULL
               OR gbp_avg_rating IS NOT NULL
               OR gbp_found = true
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        results = cur.fetchall()
        print(f"   Found {len(results)} assessment results with GBP data")
        
        for row in results:
            print(f"\n   Assessment ID: {row[0]}")
            print(f"   - Total Reviews: {row[1]}")
            print(f"   - Average Rating: {row[2]}")
            print(f"   - Recent 90d Reviews: {row[3]}")
            print(f"   - Rating Trend: {row[4]}")
            print(f"   - Is Closed: {row[5]}")
            if row[6]:
                print(f"   - Business Hours: {json.dumps(row[6], indent=6)}")
            print(f"   - GBP Found: {row[7]}")
            print(f"   - GBP Verified: {row[8]}")
            print(f"   - Created: {row[9]}")
        
        # 3. Check for recent assessments
        print("\n3. Recent assessments (last 24 hours):")
        cur.execute("""
            SELECT 
                id,
                url,
                business_name,
                created_at,
                status
            FROM assessments
            WHERE created_at >= NOW() - INTERVAL '24 hours'
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        results = cur.fetchall()
        print(f"   Found {len(results)} recent assessments")
        
        for row in results:
            print(f"\n   Assessment ID: {row[0]}")
            print(f"   - URL: {row[1]}")
            print(f"   - Business Name: {row[2]}")
            print(f"   - Created: {row[3]}")
            print(f"   - Status: {row[4]}")
        
        cur.close()
        conn.close()
        
        print(f"\n[{datetime.now()}] ✓ Database check completed")
        
    except Exception as e:
        print(f"\n[{datetime.now()}] ✗ Database error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_gbp_data()
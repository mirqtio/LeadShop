#!/usr/bin/env python3
"""
Direct test of GBP integration module
Tests the GBP functionality without going through the full assessment pipeline
"""

import asyncio
import json
import psycopg2
from datetime import datetime
import os
import sys

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import the GBP integration module
from assessments.gbp_integration import assess_google_business_profile

# Database connection
# Use 'db' as host when running inside Docker, 'localhost' when running locally
import os
DB_HOST = "db" if os.path.exists("/.dockerenv") else "localhost"

DB_CONFIG = {
    "host": DB_HOST,
    "port": 5432,
    "database": "leadfactory", 
    "user": "leadfactory",
    "password": "00g2Xyn7HHaEpQ79ldO8oE1sp"
}

async def test_gbp_module():
    """Test GBP integration module directly"""
    
    # Test data
    test_url = "https://www.starbucks.com"
    test_business_name = "Starbucks Coffee Company"
    
    print(f"[{datetime.now()}] Starting direct GBP module test...")
    print(f"  URL: {test_url}")
    print(f"  Business: {test_business_name}")
    
    try:
        # Call the GBP assessment function directly
        # The function expects: business_name, address, city, state, lead_id, assessment_id
        result = await assess_google_business_profile(
            business_name=test_business_name,
            address=None,  # Let it find based on business name
            city=None,
            state=None,
            lead_id=1,  # Dummy lead ID for testing
            assessment_id=1  # Dummy assessment ID for testing
        )
        
        print(f"\n[{datetime.now()}] GBP Assessment Result:")
        
        # Result is a dict, not an object
        if isinstance(result, dict):
            data = result.data
            print(f"\n  Business Profile Data:")
            print(f"    Place Found: {data.get('place_found', False)}")
            
            if data.get('place_found'):
                print(f"    Business Name: {data.get('name', 'N/A')}")
                print(f"    Place ID: {data.get('place_id', 'N/A')}")
                print(f"    Rating: {data.get('rating', 'N/A')}")
                print(f"    Total Reviews: {data.get('user_ratings_total', 0)}")
                print(f"    Business Status: {data.get('business_status', 'N/A')}")
                print(f"    Address: {data.get('formatted_address', 'N/A')}")
                print(f"    Phone: {data.get('formatted_phone_number', 'N/A')}")
                print(f"    Website: {data.get('website', 'N/A')}")
                
                # Business hours
                if data.get('opening_hours'):
                    print(f"\n    Business Hours:")
                    weekday_text = data['opening_hours'].get('weekday_text', [])
                    for day_hours in weekday_text:
                        print(f"      {day_hours}")
                
                # Location
                if data.get('geometry'):
                    location = data['geometry'].get('location', {})
                    print(f"\n    Location:")
                    print(f"      Latitude: {location.get('lat', 'N/A')}")
                    print(f"      Longitude: {location.get('lng', 'N/A')}")
                
                # Types/Categories
                if data.get('types'):
                    print(f"\n    Categories: {', '.join(data['types'][:5])}")
                
                # Metrics
                if result.metrics:
                    print(f"\n  Decomposed Metrics:")
                    for key, value in result.metrics.items():
                        if key.startswith('gbp_') or key in ['hours', 'review_count', 'rating', 'photos_count', 
                                                             'total_reviews', 'avg_rating', 'recent_90d', 
                                                             'rating_trend', 'is_closed']:
                            print(f"    {key}: {value}")
                
                return True
            else:
                print(f"    Error: Business not found")
                print(f"    Search Query: {data.get('search_query', 'N/A')}")
                print(f"    Match Confidence: {data.get('match_confidence', 0)}")
                return False
                
        else:
            print(f"  Error: {result.error}")
            if result.error_details:
                print(f"  Details: {result.error_details}")
            return False
            
    except Exception as e:
        print(f"\n[{datetime.now()}] ✗ Error during GBP assessment: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_database_for_test_data():
    """Check if there's any test GBP data in the database"""
    
    print(f"\n[{datetime.now()}] Checking database for existing GBP data...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Check gbp_analysis table
        cur.execute("""
            SELECT COUNT(*) FROM gbp_analysis
        """)
        count = cur.fetchone()[0]
        print(f"  Total GBP analysis records: {count}")
        
        if count > 0:
            cur.execute("""
                SELECT 
                    business_name,
                    total_reviews,
                    average_rating,
                    created_at
                FROM gbp_analysis
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            print(f"\n  Recent GBP records:")
            for row in cur.fetchall():
                print(f"    - {row[0]}: {row[1]} reviews, {row[2]} rating (created: {row[3]})")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"  Database error: {e}")

if __name__ == "__main__":
    # First check what's in the database
    check_database_for_test_data()
    
    # Then run the test
    success = asyncio.run(test_gbp_module())
    print(f"\n[{datetime.now()}] Test {'✓ PASSED' if success else '✗ FAILED'}")
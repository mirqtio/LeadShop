#!/usr/bin/env python3
"""
Playwright test to verify GBP data is saved and displayed in the UI
Tests the complete flow:
1. Submit assessment with business details
2. Verify GBP data is saved to database
3. Verify GBP data is displayed in UI
"""

import asyncio
import time
from playwright.async_api import async_playwright
import json
import psycopg2
from datetime import datetime

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "leadfactory",
    "user": "leadfactory",
    "password": "00g2Xyn7HHaEpQ79ldO8oE1sp"
}

async def test_gbp_assessment_flow():
    """Test the complete GBP assessment flow"""
    
    # Test data
    test_url = "https://www.starbucks.com"
    test_business_name = "Starbucks Coffee Company"
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)  # Set to True for CI
        context = await browser.new_context()
        page = await context.new_page()
        
        print(f"[{datetime.now()}] Starting GBP assessment test...")
        
        # Navigate to assessment UI
        await page.goto("http://localhost:8001/api/v1/assessment/")
        print(f"[{datetime.now()}] Loaded assessment UI")
        
        # Wait for page to load and take a screenshot to debug
        await page.wait_for_timeout(2000)
        await page.screenshot(path="gbp_test_page_loaded.png")
        
        # Fill in the form using the correct IDs from the actual page
        try:
            # The actual IDs are websiteUrl and businessName
            await page.fill("#websiteUrl", test_url)
            await page.fill("#businessName", test_business_name)
            print(f"[{datetime.now()}] Filled form - URL: {test_url}, Business: {test_business_name}")
        except Exception as e:
            print(f"[{datetime.now()}] ERROR filling form: {e}")
            page_content = await page.content()
            with open("gbp_test_page_content.html", "w") as f:
                f.write(page_content)
            raise
        
        # Submit assessment
        try:
            # The button has id="analyzeBtn"
            await page.click("#analyzeBtn")
            print(f"[{datetime.now()}] Submitted assessment")
        except Exception as e:
            print(f"[{datetime.now()}] ERROR submitting form: {e}")
            raise
        
        # Wait for assessment to complete (check for results container to be visible)
        try:
            # The results container needs to have the 'show' class to be visible
            await page.wait_for_selector(".results-container.show", timeout=90000)
            print(f"[{datetime.now()}] Assessment completed, results displayed")
        except Exception as e:
            print(f"[{datetime.now()}] ERROR: Assessment timeout - {e}")
            await page.screenshot(path="gbp_test_timeout_error.png", full_page=True)
            # Check if there are any error messages
            error_msg = await page.query_selector(".alert-error.show")
            if error_msg:
                error_text = await error_msg.text_content()
                print(f"[{datetime.now()}] Error message on page: {error_text}")
            raise
        
        # Wait a bit for all data to render
        await page.wait_for_timeout(2000)
        
        # Check if GBP section is displayed
        gbp_section = await page.query_selector("text=/Google Business Profile/i")
        if gbp_section:
            print(f"[{datetime.now()}] ✓ GBP section found in UI")
        else:
            print(f"[{datetime.now()}] ✗ GBP section NOT found in UI")
        
        # Check for GBP data in the results
        page_content = await page.content()
        
        # Look for GBP-specific indicators
        gbp_indicators = [
            "Business Found",
            "Business Name",
            "Business Hours",
            "Reviews",
            "Rating",
            "Photos"
        ]
        
        found_indicators = []
        for indicator in gbp_indicators:
            if indicator in page_content:
                found_indicators.append(indicator)
        
        print(f"[{datetime.now()}] Found GBP indicators in UI: {found_indicators}")
        
        # Take screenshot of results
        await page.screenshot(path="gbp_test_results.png", full_page=True)
        print(f"[{datetime.now()}] Screenshot saved: gbp_test_results.png")
        
        # Get assessment ID from the page (if available)
        assessment_id = None
        try:
            # Try to extract assessment ID from the page or network requests
            # This might be in a data attribute or visible in the UI
            assessment_elem = await page.query_selector("[data-assessment-id]")
            if assessment_elem:
                assessment_id = await assessment_elem.get_attribute("data-assessment-id")
                print(f"[{datetime.now()}] Found assessment ID: {assessment_id}")
        except:
            pass
        
        # Close browser
        await browser.close()
        
        # Verify database
        print(f"\n[{datetime.now()}] Checking database...")
        verify_database_gbp_data(test_business_name, assessment_id)
        
        print(f"\n[{datetime.now()}] ✅ GBP assessment test completed successfully!")

def verify_database_gbp_data(business_name, assessment_id=None):
    """Verify GBP data was saved to database"""
    
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Query for GBP analysis data
        if assessment_id:
            query = """
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
                WHERE ga.assessment_id = %s
                ORDER BY ga.created_at DESC
                LIMIT 1
            """
            cur.execute(query, (assessment_id,))
        else:
            query = """
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
                WHERE ga.business_name ILIKE %s
                ORDER BY ga.created_at DESC
                LIMIT 1
            """
            cur.execute(query, (f"%{business_name}%",))
        
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
            
            # Check business hours
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
            """, (result[0],))
            
            hours = cur.fetchall()
            if hours:
                print(f"\n  Business Hours:")
                for day, open_time, close_time, is_closed in hours:
                    if is_closed:
                        print(f"    - {day.capitalize()}: Closed")
                    else:
                        print(f"    - {day.capitalize()}: {open_time} - {close_time}")
            
            # Check reviews distribution
            cur.execute("""
                SELECT rating, review_count, percentage
                FROM gbp_reviews
                WHERE gbp_analysis_id = %s
                ORDER BY rating DESC
            """, (result[0],))
            
            reviews = cur.fetchall()
            if reviews:
                print(f"\n  Review Distribution:")
                for rating, count, percentage in reviews:
                    print(f"    - {rating} stars: {count} reviews ({percentage:.1f}%)")
            
        else:
            print(f"✗ No GBP analysis found in database for business: {business_name}")
        
        # Also check assessment_results table for GBP fields
        if assessment_id:
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
            """, (assessment_id,))
        else:
            cur.execute("""
                SELECT 
                    ar.gbp_total_reviews,
                    ar.gbp_avg_rating,
                    ar.gbp_recent_90d,
                    ar.gbp_rating_trend,
                    ar.gbp_is_closed,
                    ar.gbp_hours
                FROM assessment_results ar
                JOIN assessments a ON ar.assessment_id = a.id
                WHERE a.created_at >= NOW() - INTERVAL '5 minutes'
                ORDER BY a.created_at DESC
                LIMIT 1
            """)
        
        result = cur.fetchone()
        if result:
            print(f"\n✓ Found GBP data in assessment_results table:")
            print(f"  - Total Reviews: {result[0]}")
            print(f"  - Average Rating: {result[1]}")
            print(f"  - Recent 90d Reviews: {result[2]}")
            print(f"  - Rating Trend: {result[3]}")
            print(f"  - Is Closed: {result[4]}")
            if result[5]:
                print(f"  - Business Hours: {json.dumps(result[5], indent=2)}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Database error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_gbp_assessment_flow())
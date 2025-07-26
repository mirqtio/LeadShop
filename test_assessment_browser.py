#!/usr/bin/env python3
"""
Browser-based test for synchronous assessment tool
Captures screenshots of the complete workflow
"""

import asyncio
import json
import time
from playwright.async_api import async_playwright
import os

async def test_simple_assessment():
    """Test the synchronous assessment tool end-to-end"""
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False, args=['--window-size=1400,900'])
        context = await browser.new_context(
            viewport={'width': 1400, 'height': 900},
            record_video_dir='test_videos'
        )
        page = await context.new_page()
        
        try:
            # Navigate to the assessment UI
            await page.goto('http://localhost:8001/api/v1/simple-assessment/')
            await page.wait_for_load_state('networkidle')
            
            # Take screenshot of initial UI
            await page.screenshot(path='assessment_ui_initial.png', full_page=True)
            print("✓ Initial UI screenshot captured")
            
            # Fill the form
            await page.fill('input[name="url"]', 'https://www.google.com')
            await page.fill('input[name="business_name"]', 'Google')
            await page.fill('input[name="email"]', 'test@example.com')
            await page.fill('input[name="notes"]', 'Browser automation test')
            
            # Take screenshot of filled form
            await page.screenshot(path='assessment_ui_filled.png', full_page=True)
            print("✓ Filled form screenshot captured")
            
            # Submit the form
            await page.click('button[type="submit"]')
            
            # Wait for assessment to complete (synchronous execution)
            print("⏳ Running synchronous assessment...")
            await page.wait_for_selector('#results', timeout=120000)  # 2 minute timeout
            
            # Take screenshot of results
            await page.screenshot(path='assessment_ui_results.png', full_page=True)
            print("✓ Results screenshot captured")
            
            # Wait a bit more for any final updates
            await asyncio.sleep(5)
            
            # Take final screenshot with all data loaded
            await page.screenshot(path='assessment_ui_complete.png', full_page=True)
            print("✓ Complete assessment screenshot captured")
            
            # Extract results from the page
            results_text = await page.text_content('#results')
            print("✓ Assessment completed successfully")
            print("Results preview:", results_text[:200] + "...")
            
            return True
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            # Take error screenshot
            await page.screenshot(path='assessment_error.png', full_page=True)
            return False
            
        finally:
            await browser.close()

async def verify_database_results():
    """Verify assessment results were saved to database"""
    from sqlalchemy import create_engine, text
    
    # Connect to database
    DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/leadfactory"
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Check latest assessment
        result = conn.execute(text("""
            SELECT a.id, a.url, a.business_name, a.status, a.created_at,
                   COUNT(s.id) as screenshot_count
            FROM assessments a
            LEFT JOIN screenshots s ON a.id = s.assessment_id
            WHERE a.url = 'https://www.google.com'
            ORDER BY a.created_at DESC
            LIMIT 1
        """))
        
        assessment = result.fetchone()
        if assessment:
            print("✓ Database verification:")
            print(f"  Assessment ID: {assessment.id}")
            print(f"  URL: {assessment.url}")
            print(f"  Business: {assessment.business_name}")
            print(f"  Status: {assessment.status}")
            print(f"  Screenshots: {assessment.screenshot_count}")
            return True
        else:
            print("❌ No assessment found in database")
            return False

if __name__ == "__main__":
    print("🚀 Starting synchronous assessment browser test...")
    
    # Run browser test
    success = asyncio.run(test_simple_assessment())
    
    if success:
        print("\n✅ Browser test completed successfully")
        
        # Verify database
        print("\n🔍 Verifying database results...")
        asyncio.run(verify_database_results())
        
        print("\n📸 Screenshots captured:")
        print("  - assessment_ui_initial.png")
        print("  - assessment_ui_filled.png") 
        print("  - assessment_ui_results.png")
        print("  - assessment_ui_complete.png")
    else:
        print("\n❌ Browser test failed - check error screenshot")

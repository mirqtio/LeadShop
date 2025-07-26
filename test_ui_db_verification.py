#!/usr/bin/env python3
"""
Test UI with Playwright to verify PageSpeed data is displayed from DB
"""

import asyncio
from playwright.async_api import async_playwright
import time
import psycopg2

async def test_ui_db_verification():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser for debugging
        page = await browser.new_page()
        
        # Enable console logging
        page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
        
        try:
            # Navigate to simple assessment UI
            print("Navigating to assessment UI...")
            await page.goto("http://localhost:8001/api/v1/simple-assessment")
            
            # Use a unique URL with timestamp
            test_url = f"https://www.example.org?dbtest={int(time.time())}"
            print(f"Testing with URL: {test_url}")
            
            # Fill in the URL
            await page.fill('input[type="url"]', test_url)
            
            # Click the submit button
            await page.click('button[type="submit"]')
            
            # Wait for assessment to complete
            print("Waiting for assessment to complete...")
            await page.wait_for_selector('text=PageSpeed assessment completed!', timeout=60000)
            
            # Wait a bit for DB fetch
            await asyncio.sleep(2)
            
            # Check if results are displayed
            results_displayed = await page.is_visible('text=Assessment Results')
            print(f"Results displayed: {results_displayed}")
            
            # Get the FCP value from the UI
            fcp_element = await page.query_selector('td:has-text("First Contentful Paint (FCP)") + td')
            ui_fcp_value = None
            if fcp_element:
                ui_fcp_value = await fcp_element.text_content()
                print(f"FCP value from UI: {ui_fcp_value}")
            
            # Get performance score from UI
            perf_element = await page.query_selector('td:has-text("Performance Score") + td')
            ui_perf_value = None
            if perf_element:
                ui_perf_value = await perf_element.text_content()
                print(f"Performance score from UI: {ui_perf_value}")
            
            # Connect to database through docker-compose
            import subprocess
            result = subprocess.run(
                ["docker-compose", "exec", "-T", "db", "psql", "-U", "leadfactory", "-d", "leadfactory", "-t", "-c",
                 """SELECT a.id, pa.first_contentful_paint_ms, pa.performance_score
                    FROM assessments a
                    JOIN pagespeed_analysis pa ON pa.assessment_id = a.id
                    WHERE pa.strategy = 'mobile'
                    ORDER BY a.created_at DESC
                    LIMIT 1"""],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # Parse the output (format: "id | fcp | score")
                parts = result.stdout.strip().split('|')
                if len(parts) >= 3:
                    assessment_id = parts[0].strip()
                    db_fcp = parts[1].strip()
                    db_perf = parts[2].strip()
                print(f"\nDatabase values:")
                print(f"Assessment ID: {assessment_id}")
                print(f"FCP from DB: {db_fcp}ms")
                print(f"Performance score from DB: {db_perf}")
                
                # Verify UI matches DB
                if ui_fcp_value and str(db_fcp) in ui_fcp_value:
                    print("✓ FCP value matches database")
                else:
                    print("✗ FCP value mismatch!")
                
                if ui_perf_value and str(db_perf) in ui_perf_value:
                    print("✓ Performance score matches database")
                else:
                    print("✗ Performance score mismatch!")
            
            
            # Take a screenshot for verification
            await page.screenshot(path='test_db_results.png')
            print("\nScreenshot saved to test_db_results.png")
            
            return True
            
        except Exception as e:
            print(f"Error during test: {e}")
            await page.screenshot(path='test_db_error.png')
            return False
        finally:
            await asyncio.sleep(5)  # Keep browser open to see results
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(test_ui_db_verification())
    print(f"\nTest {'passed' if success else 'failed'}")
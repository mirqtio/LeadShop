#!/usr/bin/env python3
"""
Test UI with Playwright to verify Security assessment works
"""

import asyncio
from playwright.async_api import async_playwright
import time
import subprocess

async def test_security_assessment():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Enable console logging
        page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
        
        try:
            # Navigate to simple assessment UI
            print("Navigating to assessment UI...")
            await page.goto("http://localhost:8001/api/v1/simple-assessment")
            
            # Use a unique URL with timestamp - using HTTPS for better security score
            test_url = f"https://www.example.org?security={int(time.time())}"
            print(f"Testing with URL: {test_url}")
            
            # Fill in the URL
            await page.fill('input[type="url"]', test_url)
            
            # Click the submit button
            await page.click('button[type="submit"]')
            
            # Wait for assessment to complete
            print("Waiting for assessments to complete...")
            await page.wait_for_selector('text=Assessments completed!', timeout=60000)
            
            # Wait a bit for all results to load
            await asyncio.sleep(2)
            
            # Check if security results are displayed
            security_section = await page.query_selector('text=Security Analysis')
            if security_section:
                print("✓ Security Analysis section found")
            else:
                print("✗ Security Analysis section NOT found")
            
            # Get security score from UI
            security_score_element = await page.query_selector('td:has-text("Security Score") + td')
            if security_score_element:
                security_score = await security_score_element.text_content()
                print(f"Security Score from UI: {security_score}")
            
            # Get HTTPS status
            https_element = await page.query_selector('td:has-text("HTTPS") + td')
            if https_element:
                https_status = await https_element.text_content()
                print(f"HTTPS status: {https_status}")
            
            # Check database for security data
            result = subprocess.run(
                ["docker-compose", "exec", "-T", "db", "psql", "-U", "leadfactory", "-d", "leadfactory", "-t", "-c",
                 """SELECT a.id, a.security_score, a.security_headers IS NOT NULL as has_headers
                    FROM assessments a
                    ORDER BY a.created_at DESC
                    LIMIT 1"""],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split('|')
                if len(parts) >= 3:
                    assessment_id = parts[0].strip()
                    db_security_score = parts[1].strip()
                    has_headers = parts[2].strip()
                    
                    print(f"\nDatabase values:")
                    print(f"Assessment ID: {assessment_id}")
                    print(f"Security score from DB: {db_security_score}")
                    print(f"Has security headers data: {has_headers}")
                    
                    # Verify scores match
                    if security_score and db_security_score in security_score:
                        print("✓ Security score matches database")
                    else:
                        print("✗ Security score mismatch!")
            
            # Take a screenshot
            await page.screenshot(path='test_security_results.png')
            print("\nScreenshot saved to test_security_results.png")
            
            return True
            
        except Exception as e:
            print(f"Error during test: {e}")
            await page.screenshot(path='test_security_error.png')
            return False
        finally:
            await asyncio.sleep(5)  # Keep browser open to see results
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(test_security_assessment())
    print(f"\nTest {'passed' if success else 'failed'}")
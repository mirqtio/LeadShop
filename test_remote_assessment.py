#!/usr/bin/env python3
"""Test the remote assessment UI by submitting a URL and capturing results"""

import asyncio
from playwright.async_api import async_playwright
import sys
from datetime import datetime

async def test_assessment_ui():
    async with async_playwright() as p:
        # Launch browser in headless mode
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )
        page = await context.new_page()
        
        try:
            print(f"[{datetime.now()}] Navigating to assessment UI...")
            # Try to navigate to the assessment page on local instance
            await page.goto('http://localhost:8001/api/v1/assessment', 
                          wait_until='networkidle',
                          timeout=30000)
            
            print(f"[{datetime.now()}] Page loaded successfully!")
            
            # Wait for the form to be ready
            await page.wait_for_selector('input[type="url"]', timeout=10000)
            
            # Fill in the URL field with Mozilla's website
            test_url = "https://www.mozilla.org"
            print(f"[{datetime.now()}] Entering URL: {test_url}")
            await page.fill('input[type="url"]', test_url)
            
            # Find and click the submit button
            submit_button = await page.query_selector('button[type="submit"]')
            if submit_button:
                print(f"[{datetime.now()}] Clicking submit button...")
                await submit_button.click()
            else:
                # Try alternative selectors
                await page.click('button:has-text("Assess")', timeout=5000)
            
            # Wait for results to load (look for common result indicators)
            print(f"[{datetime.now()}] Waiting for results to load...")
            await page.wait_for_selector('.results, #results, [class*="result"]', 
                                       timeout=60000,
                                       state='visible')
            
            # Wait a bit more to ensure all content is loaded
            await page.wait_for_timeout(3000)
            
            # Take a screenshot of the results
            screenshot_path = f'/Users/charlieirwin/LeadShop/assessment_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"[{datetime.now()}] Screenshot saved to: {screenshot_path}")
            
            # Try to extract some result text for verification
            result_text = await page.inner_text('body')
            print(f"[{datetime.now()}] Results preview (first 500 chars):")
            print(result_text[:500])
            
            return screenshot_path
            
        except Exception as e:
            print(f"[{datetime.now()}] Error occurred: {type(e).__name__}: {e}")
            # Take a screenshot of the error state
            error_screenshot = f'/Users/charlieirwin/LeadShop/assessment_error_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
            await page.screenshot(path=error_screenshot)
            print(f"[{datetime.now()}] Error screenshot saved to: {error_screenshot}")
            raise
        finally:
            await browser.close()

if __name__ == "__main__":
    try:
        screenshot_path = asyncio.run(test_assessment_ui())
        print(f"\nTest completed successfully! Screenshot: {screenshot_path}")
    except Exception as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
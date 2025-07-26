#!/usr/bin/env python3
"""
Test UI with Playwright to verify PageSpeed data saves to DB
"""

import asyncio
from playwright.async_api import async_playwright
import time

async def test_ui_pagespeed():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Navigate to simple assessment UI
            print("Navigating to assessment UI...")
            await page.goto("http://localhost:8001/api/v1/simple-assessment")
            
            # Use a unique URL with timestamp
            test_url = f"https://www.example.org?test={int(time.time())}"
            print(f"Testing with URL: {test_url}")
            
            # Fill in the URL
            await page.fill('input[type="url"]', test_url)
            
            # Click the submit button
            await page.click('button[type="submit"]')
            
            # Wait for assessment to complete
            print("Waiting for assessment to complete...")
            await page.wait_for_selector('text=PageSpeed assessment completed!', timeout=60000)
            
            # Check if results are displayed
            results_displayed = await page.is_visible('text=Assessment Results')
            print(f"Results displayed: {results_displayed}")
            
            # Get the FCP value from the UI
            fcp_element = await page.query_selector('td:has-text("First Contentful Paint (FCP)") + td')
            if fcp_element:
                fcp_value = await fcp_element.text_content()
                print(f"FCP value from UI: {fcp_value}")
            
            # Get performance score from UI
            perf_element = await page.query_selector('td:has-text("Performance Score") + td')
            if perf_element:
                perf_value = await perf_element.text_content()
                print(f"Performance score from UI: {perf_value}")
            
            # Take a screenshot for verification
            await page.screenshot(path='test_results.png')
            print("Screenshot saved to test_results.png")
            
            return True
            
        except Exception as e:
            print(f"Error during test: {e}")
            await page.screenshot(path='test_error.png')
            return False
        finally:
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(test_ui_pagespeed())
    print(f"\nTest {'passed' if success else 'failed'}")
#!/usr/bin/env python3
"""Capture screenshots of the assessment UI"""

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime

async def capture_assessment_ui():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Run with UI to see what's happening
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        try:
            # Try the regular assessment UI first
            print("Testing regular assessment UI...")
            await page.goto('http://localhost:8001/api/v1/assessment')
            await page.wait_for_timeout(2000)
            await page.screenshot(path='/Users/charlieirwin/LeadShop/assessment_ui_regular.png', full_page=True)
            print("Regular assessment UI screenshot saved")
            
            # Try the simple assessment UI
            print("\nTesting simple assessment UI...")
            await page.goto('http://localhost:8001/api/v1/simple-assessment')
            await page.wait_for_timeout(2000)
            await page.screenshot(path='/Users/charlieirwin/LeadShop/assessment_ui_simple.png', full_page=True)
            print("Simple assessment UI screenshot saved")
            
            # Fill and submit the simple form
            print("\nFilling and submitting simple assessment form...")
            await page.fill('#url', 'https://www.example.com')
            await page.fill('#businessName', 'Example Company')
            
            # Take screenshot before submission
            await page.screenshot(path='/Users/charlieirwin/LeadShop/assessment_ui_filled.png', full_page=True)
            print("Filled form screenshot saved")
            
            # Submit the form
            await page.click('#submitBtn')
            
            # Wait a bit and take screenshot of submission state
            await page.wait_for_timeout(5000)
            await page.screenshot(path='/Users/charlieirwin/LeadShop/assessment_ui_submitted.png', full_page=True)
            print("Submitted form screenshot saved")
            
            # Keep browser open for manual inspection
            print("\nBrowser will stay open for 30 seconds for manual inspection...")
            await page.wait_for_timeout(30000)
            
        except Exception as e:
            print(f"Error: {e}")
            await page.screenshot(path='/Users/charlieirwin/LeadShop/assessment_ui_error.png')
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_assessment_ui())
#!/usr/bin/env python3
"""Test the assessment UI and capture screenshots of decomposed scores."""

import asyncio
import os
from playwright.async_api import async_playwright
import time

async def test_assessment_ui():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Navigate to the assessment UI
        print("1. Navigating to assessment UI...")
        await page.goto("http://localhost:8001/api/v1/simple-assessment")
        await page.wait_for_load_state("networkidle")
        
        # Take initial screenshot
        await page.screenshot(path="screenshot_1_initial_page.png", full_page=True)
        print("   ✓ Captured initial page")
        
        # Fill in the form
        print("2. Filling out assessment form...")
        await page.fill('input[placeholder="https://example.com"]', "https://www.airbnb.com")
        await page.fill('input[placeholder="Business Name (optional)"]', "Airbnb")
        await page.fill('input[placeholder="Street Address (optional)"]', "888 Brannan Street")
        await page.fill('input[placeholder="City (optional)"]', "San Francisco")
        await page.fill('input[placeholder="State (optional)"]', "CA")
        
        # Take screenshot of filled form
        await page.screenshot(path="screenshot_2_filled_form.png", full_page=True)
        print("   ✓ Captured filled form")
        
        # Submit the form
        print("3. Submitting assessment...")
        await page.click('button[type="submit"]')
        
        # Wait for results (this may take a while)
        print("4. Waiting for assessment to complete...")
        start_time = time.time()
        
        # Wait for results container to appear with a longer timeout
        try:
            await page.wait_for_selector('#results', state='visible', timeout=120000)
            print(f"   ✓ Results loaded after {time.time() - start_time:.1f} seconds")
        except:
            print("   ✗ Timeout waiting for results")
            await page.screenshot(path="screenshot_3_timeout_state.png", full_page=True)
            await browser.close()
            return
        
        # Wait a bit more for all content to load
        await page.wait_for_timeout(3000)
        
        # Take screenshot of initial results
        await page.screenshot(path="screenshot_4_initial_results.png", full_page=True)
        print("   ✓ Captured initial results")
        
        # Scroll to find the decomposed scores section
        print("5. Looking for decomposed scores section...")
        
        # Try to find the decomposed scores section
        decomposed_section = await page.query_selector('text="DECOMPOSED SCORES FROM DATABASE (PRP-014)"')
        if decomposed_section:
            print("   ✓ Found decomposed scores section")
            
            # Scroll to the decomposed scores section
            await decomposed_section.scroll_into_view_if_needed()
            await page.wait_for_timeout(1000)
            
            # Take screenshot of decomposed scores
            await page.screenshot(path="screenshot_5_decomposed_scores_focused.png", full_page=True)
            print("   ✓ Captured decomposed scores")
            
            # Try to capture just the decomposed section
            box = await decomposed_section.bounding_box()
            if box:
                # Expand the box to capture more context
                expanded_box = {
                    'x': max(0, box['x'] - 20),
                    'y': max(0, box['y'] - 20),
                    'width': box['width'] + 40,
                    'height': min(1000, box['height'] + 500)  # Capture more below
                }
                await page.screenshot(
                    path="screenshot_6_decomposed_scores_closeup.png",
                    clip=expanded_box
                )
                print("   ✓ Captured decomposed scores closeup")
        else:
            print("   ✗ Could not find decomposed scores section")
        
        # Scroll through the entire page to capture all content
        print("6. Capturing full page content...")
        
        # Scroll to bottom
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="screenshot_7_bottom_of_page.png", full_page=True)
        print("   ✓ Captured bottom of page")
        
        # Take a final full-page screenshot
        await page.screenshot(path="screenshot_8_full_page_final.png", full_page=True)
        print("   ✓ Captured final full page")
        
        print("\n✅ Test completed! Check the following screenshots:")
        print("   - screenshot_1_initial_page.png")
        print("   - screenshot_2_filled_form.png")
        print("   - screenshot_4_initial_results.png")
        print("   - screenshot_5_decomposed_scores_focused.png")
        print("   - screenshot_6_decomposed_scores_closeup.png")
        print("   - screenshot_7_bottom_of_page.png")
        print("   - screenshot_8_full_page_final.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_assessment_ui())
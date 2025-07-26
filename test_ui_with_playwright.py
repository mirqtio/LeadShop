#!/usr/bin/env python3
"""Test assessment UI using Playwright with proper waiting."""

import asyncio
from playwright.async_api import async_playwright
import time

async def test_ui():
    async with async_playwright() as p:
        # Launch browser in non-headless mode so we can see what's happening
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("1. Opening assessment UI...")
        await page.goto("http://localhost:8001/api/v1/simple-assessment")
        await page.wait_for_load_state("networkidle")
        
        print("2. Filling form...")
        # Fill the form using the actual input fields
        await page.fill('input[placeholder="https://example.com"]', "https://www.airbnb.com")
        await page.fill('input[placeholder="Business Name (optional)"]', "Airbnb")
        await page.fill('input[placeholder="Street Address (optional)"]', "888 Brannan Street")
        await page.fill('input[placeholder="City (optional)"]', "San Francisco")
        await page.fill('input[placeholder="State (optional)"]', "CA")
        
        # Take screenshot before submission
        await page.screenshot(path="test_1_form_filled.png")
        print("   ✓ Form filled and screenshot saved")
        
        print("3. Submitting assessment...")
        # Click the submit button
        await page.click('button:has-text("Run Assessment")')
        
        print("4. Waiting for results (this may take 30-60 seconds)...")
        # Wait for the results div to appear
        try:
            await page.wait_for_selector('#results', state='visible', timeout=120000)
            print("   ✓ Results appeared!")
            
            # Wait a bit more for all content to load
            await page.wait_for_timeout(5000)
            
            # Take initial results screenshot
            await page.screenshot(path="test_2_initial_results.png", full_page=True)
            print("   ✓ Initial results captured")
            
            # Look for decomposed scores section
            print("5. Looking for decomposed scores section...")
            decomposed_heading = await page.query_selector('text="DECOMPOSED SCORES FROM DATABASE (PRP-014)"')
            
            if decomposed_heading:
                print("   ✓ Found decomposed scores section!")
                
                # Scroll to it
                await decomposed_heading.scroll_into_view_if_needed()
                await page.wait_for_timeout(1000)
                
                # Take focused screenshot
                await page.screenshot(path="test_3_decomposed_scores_visible.png", full_page=True)
                
                # Try to capture just the decomposed section
                box = await decomposed_heading.bounding_box()
                if box:
                    # Capture a larger area around the heading
                    clip_area = {
                        'x': max(0, box['x'] - 50),
                        'y': max(0, box['y'] - 50),
                        'width': min(page.viewport_size['width'] - box['x'] + 50, box['width'] + 100),
                        'height': 800  # Capture more content below
                    }
                    await page.screenshot(
                        path="test_4_decomposed_scores_closeup.png",
                        clip=clip_area
                    )
                    print("   ✓ Captured decomposed scores closeup")
                
                # Scroll to bottom to see if there's more
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)
                await page.screenshot(path="test_5_bottom_of_page.png", full_page=True)
                
            else:
                print("   ✗ Could not find decomposed scores section")
                # Take a full page screenshot anyway
                await page.screenshot(path="test_no_decomposed_full_page.png", full_page=True)
            
            print("\n✅ Test completed successfully!")
            print("   Check the following screenshots:")
            print("   - test_1_form_filled.png")
            print("   - test_2_initial_results.png")
            print("   - test_3_decomposed_scores_visible.png")
            print("   - test_4_decomposed_scores_closeup.png")
            print("   - test_5_bottom_of_page.png")
            
        except Exception as e:
            print(f"   ✗ Error waiting for results: {e}")
            await page.screenshot(path="test_error_state.png", full_page=True)
        
        # Keep browser open for manual inspection
        print("\nKeeping browser open for manual inspection...")
        print("Press Ctrl+C to close")
        await asyncio.sleep(300)  # Keep open for 5 minutes
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_ui())
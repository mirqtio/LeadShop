#!/usr/bin/env python3
"""
Capture a real assessment through the UI using Playwright
Shows the complete flow: entering URL, submitting, and displaying results
"""

import asyncio
from playwright.async_api import async_playwright
import time

async def run_assessment():
    print("🚀 Starting real UI assessment demonstration...")
    
    async with async_playwright() as p:
        # Launch browser in non-headless mode so we can see it
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Navigate to the assessment UI
        print("📍 Navigating to assessment UI...")
        await page.goto("http://localhost:8001/api/v1/simple-assessment")
        await page.wait_for_load_state("networkidle")
        
        # Take screenshot of empty form
        await page.screenshot(path="1_initial_empty_form.png")
        print("📸 Captured: Empty form")
        
        # Fill in the form with a well-known URL
        print("✍️ Filling form with Amazon.com...")
        await page.fill("#businessUrl", "https://www.amazon.com")
        await page.fill("#businessName", "Amazon.com, Inc.")
        await page.fill("#city", "Seattle")
        await page.fill("#state", "WA")
        
        # Take screenshot of filled form
        await page.screenshot(path="2_filled_form.png")
        print("📸 Captured: Filled form")
        
        # Click submit button
        print("🖱️ Clicking submit button...")
        await page.click("#submitBtn")
        
        # Wait for assessment to complete (show progress)
        print("⏳ Waiting for assessment to complete...")
        for i in range(60):
            try:
                # Check if results are visible
                results_visible = await page.is_visible("#assessmentResults")
                if results_visible:
                    print(f"✅ Results appeared after {i} seconds")
                    break
            except:
                pass
            
            # Take periodic screenshots of progress
            if i % 10 == 0:
                await page.screenshot(path=f"3_progress_{i}s.png")
                print(f"📸 Captured: Progress at {i}s")
            
            await asyncio.sleep(1)
        
        # Wait a bit more for all data to load
        await asyncio.sleep(5)
        
        # Scroll to show decomposed scores
        print("📜 Scrolling to show all results...")
        await page.evaluate("window.scrollTo(0, document.getElementById('decomposed-scores')?.offsetTop || 0)")
        await asyncio.sleep(1)
        
        # Take screenshot of decomposed scores
        await page.screenshot(path="4_decomposed_scores_view.png", full_page=False)
        print("📸 Captured: Decomposed scores view")
        
        # Scroll to bottom to show screenshots
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1)
        
        # Take final full page screenshot
        await page.screenshot(path="5_complete_results_fullpage.png", full_page=True)
        print("📸 Captured: Complete results (full page)")
        
        # Also capture just the viewport
        await page.screenshot(path="6_results_viewport.png", full_page=False)
        print("📸 Captured: Results viewport")
        
        # Extract and print some key metrics to verify
        print("\n🔍 Verifying data from UI...")
        
        # Check PageSpeed scores
        try:
            mobile_score = await page.text_content("td:has-text('Performance Score (mobile)') + td")
            desktop_score = await page.text_content("td:has-text('Performance Score (desktop)') + td")
            print(f"PageSpeed Mobile: {mobile_score}")
            print(f"PageSpeed Desktop: {desktop_score}")
        except:
            print("⚠️ Could not extract PageSpeed scores")
        
        # Check SEMrush data
        try:
            authority = await page.text_content("td:has-text('Authority Score') + td")
            traffic = await page.text_content("td:has-text('Organic Traffic') + td")
            keywords = await page.text_content("td:has-text('Keywords Count') + td")
            print(f"SEMrush Authority: {authority}")
            print(f"SEMrush Traffic: {traffic}")
            print(f"SEMrush Keywords: {keywords}")
        except:
            print("⚠️ Could not extract SEMrush data")
        
        # Check if screenshots are displayed
        try:
            screenshot_count = await page.locator("img[alt*='Screenshot']").count()
            print(f"Screenshots displayed: {screenshot_count}")
        except:
            print("⚠️ Could not count screenshots")
        
        print("\n✅ Assessment demonstration complete!")
        print("📁 Screenshots saved:")
        print("   1_initial_empty_form.png - Empty assessment form")
        print("   2_filled_form.png - Form filled with Amazon.com")
        print("   3_progress_*.png - Progress during assessment")
        print("   4_decomposed_scores_view.png - Decomposed scores section")
        print("   5_complete_results_fullpage.png - Full page with all results")
        print("   6_results_viewport.png - Current viewport of results")
        
        # Keep browser open for manual inspection
        print("\n👀 Browser will remain open for 30 seconds for manual inspection...")
        await asyncio.sleep(30)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_assessment())
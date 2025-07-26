"""
Final Playwright Test for Visual Analysis
Uses the simple assessment UI to submit and verify visual analysis
"""

import asyncio
import os
from playwright.async_api import async_playwright, expect
from datetime import datetime
import time

# Test configuration
TEST_URL = "http://localhost:8001"
TEST_WEBSITE_URL = f"https://www.cloudflare.com?visual=test_{int(datetime.now().timestamp())}"
TEST_BUSINESS_NAME = "Cloudflare Visual Test"


async def test_visual_analysis_final():
    """Final test for visual analysis using Playwright"""
    
    async with async_playwright() as p:
        # Launch browser in non-headless mode to see what's happening
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # 1. Navigate to simple assessment UI
            print(f"1. Navigating to {TEST_URL}/api/v1/simple-assessment")
            await page.goto(f"{TEST_URL}/api/v1/simple-assessment", wait_until="networkidle")
            print("✓ Page loaded")
            
            # 2. Fill in the form
            print(f"\n2. Filling form with URL: {TEST_WEBSITE_URL}")
            await page.fill("#url", TEST_WEBSITE_URL)
            await page.fill("#businessName", TEST_BUSINESS_NAME)
            print("✓ Form filled")
            
            # 3. Submit the assessment
            print("\n3. Submitting assessment...")
            await page.click("#submitBtn")
            print("✓ Assessment submitted")
            
            # 4. Wait for results with longer timeout
            print("\n4. Waiting for assessment to complete (this may take 2-3 minutes)...")
            max_wait_time = 300  # 5 minutes
            start_time = time.time()
            results_found = False
            visual_analysis_found = False
            
            while time.time() - start_time < max_wait_time:
                # Check status
                try:
                    status_text = await page.locator("#status").text_content()
                    print(f"   Status: {status_text}")
                except:
                    pass
                
                # Check if results are visible
                results_visible = await page.locator("#results").is_visible()
                
                if results_visible:
                    # Check for any results
                    rows = await page.locator("#resultsBody tr").count()
                    if rows > 0:
                        print(f"   ✓ Found {rows} result rows")
                        results_found = True
                        
                        # Look specifically for visual analysis metrics
                        all_metrics = await page.locator("#resultsBody tr td:first-child").all_text_contents()
                        
                        visual_keywords = [
                            "visual", "design", "usability", "accessibility", 
                            "professionalism", "trust", "ux", "ui", "screenshot",
                            "layout", "typography", "color", "mobile", "desktop"
                        ]
                        
                        visual_metrics_found = []
                        for metric in all_metrics:
                            metric_lower = metric.lower()
                            for keyword in visual_keywords:
                                if keyword in metric_lower:
                                    visual_metrics_found.append(metric)
                                    visual_analysis_found = True
                                    break
                        
                        if visual_analysis_found:
                            print(f"\n✅ Visual analysis completed!")
                            print(f"Found {len(visual_metrics_found)} visual analysis metrics:")
                            for vm in visual_metrics_found[:10]:
                                print(f"  - {vm}")
                            if len(visual_metrics_found) > 10:
                                print(f"  ... and {len(visual_metrics_found) - 10} more")
                            break
                
                # Check for errors
                try:
                    status_text = await page.locator("#status").text_content()
                    if "error" in status_text.lower() or "failed" in status_text.lower():
                        print(f"\n❌ Assessment failed: {status_text}")
                        break
                except:
                    pass
                
                # Wait before checking again
                await page.wait_for_timeout(5000)
            
            # 5. Take screenshot of results
            if results_found:
                print("\n5. Taking screenshot of results...")
                
                # Scroll to results section
                await page.locator("#results").scroll_into_view_if_needed()
                
                # Take full page screenshot
                screenshot_path = f"visual_analysis_results_{int(datetime.now().timestamp())}.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"✓ Screenshot saved as {screenshot_path}")
                
                # Also take a focused screenshot of just the results table
                results_screenshot = f"visual_analysis_table_{int(datetime.now().timestamp())}.png"
                await page.locator("#resultsTable").screenshot(path=results_screenshot)
                print(f"✓ Results table screenshot saved as {results_screenshot}")
                
                # Print summary
                print("\n" + "="*60)
                print("TEST SUMMARY:")
                print(f"- Assessment completed: {'Yes' if results_found else 'No'}")
                print(f"- Visual analysis found: {'Yes' if visual_analysis_found else 'No'}")
                print(f"- Total metrics displayed: {rows if results_found else 0}")
                print(f"- Visual metrics found: {len(visual_metrics_found) if visual_analysis_found else 0}")
                print(f"- Time taken: {int(time.time() - start_time)} seconds")
                print("="*60)
                
                # If we didn't find visual analysis, check what happened
                if results_found and not visual_analysis_found:
                    print("\n⚠️  Assessment completed but no visual analysis metrics found")
                    print("This could mean:")
                    print("1. Screenshot capture failed (check if ScreenshotOne API key is configured)")
                    print("2. Visual analysis was skipped due to missing screenshots")
                    print("3. Visual analysis module encountered an error")
                    
                    # Look for screenshot-related messages
                    for metric in all_metrics:
                        if "screenshot" in metric.lower():
                            value_index = all_metrics.index(metric)
                            if value_index < len(all_metrics):
                                try:
                                    value = await page.locator(f"#resultsBody tr:nth-child({value_index + 1}) td:last-child").text_content()
                                    print(f"\nScreenshot info: {metric} = {value}")
                                except:
                                    pass
            else:
                print(f"\n❌ Assessment did not complete within {max_wait_time} seconds")
                await page.screenshot(path="visual_analysis_timeout.png")
                print("Timeout screenshot saved as visual_analysis_timeout.png")
            
        except Exception as e:
            print(f"\n❌ Test failed with error: {str(e)}")
            await page.screenshot(path="visual_analysis_error.png")
            print("Error screenshot saved as visual_analysis_error.png")
            raise
            
        finally:
            # Keep browser open for 10 seconds to review results
            print("\nKeeping browser open for 10 seconds...")
            await page.wait_for_timeout(10000)
            await browser.close()


if __name__ == "__main__":
    print("Visual Analysis Final Test")
    print("="*80)
    print("This test will:")
    print("1. Submit an assessment using the simple UI")
    print("2. Wait for completion (may take 2-3 minutes)")
    print("3. Verify visual analysis results are displayed")
    print("4. Take screenshots of the results")
    print("="*80 + "\n")
    
    asyncio.run(test_visual_analysis_final())
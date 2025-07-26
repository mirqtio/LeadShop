#!/usr/bin/env python3
"""
Capture screenshot of assessment results using Playwright
"""

import asyncio
from playwright.async_api import async_playwright
import os
from datetime import datetime

async def capture_assessment_results():
    async with async_playwright() as p:
        # Launch browser in non-headless mode to see what's happening
        browser = await p.chromium.launch(headless=False)
        
        try:
            # Create a new page
            page = await browser.new_page()
            
            # Set a reasonable viewport size
            await page.set_viewport_size({"width": 1400, "height": 900})
            
            print("Navigating to assessment UI...")
            # Navigate to the assessment page
            await page.goto('http://localhost:8001/api/v1/simple-assessment', wait_until='networkidle')
            
            # Wait for the form to be visible
            await page.wait_for_selector('input[placeholder="https://example.com"]', timeout=10000)
            
            print("Filling in the form...")
            # Fill in the form - using the actual field names from the UI
            await page.fill('input[placeholder="https://example.com"]', 'https://www.github.com')
            await page.fill('input[placeholder="Business Name (optional)"]', 'GitHub')
            await page.fill('input[placeholder="Street Address (optional)"]', '88 Colin P Kelly Jr St')
            await page.fill('input[placeholder="City (optional)"]', 'San Francisco')
            await page.fill('input[placeholder="State (optional)"]', 'CA')
            
            # Take a screenshot of the form before submission
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            form_screenshot = f"assessment_form_{timestamp}.png"
            await page.screenshot(path=form_screenshot, full_page=True)
            print(f"Form screenshot saved: {form_screenshot}")
            
            print("Submitting the form...")
            # Submit the form - look for the "Run Assessment" button
            submit_button = await page.wait_for_selector('button:has-text("Run Assessment")', timeout=5000)
            await submit_button.click()
            
            # Wait for results to appear
            print("Waiting for results to load...")
            
            # First wait for the status div to show processing messages
            status_visible = False
            try:
                await page.wait_for_selector('#status', state='visible', timeout=5000)
                status_visible = True
                print("Status message visible, assessment is processing...")
            except:
                print("No status message found")
            
            # Monitor status changes for up to 5 minutes
            start_time = datetime.now()
            last_status = ""
            results_loaded = False
            
            while (datetime.now() - start_time).seconds < 300:  # 5 minutes max
                # Check current status
                try:
                    status_element = await page.query_selector('#status')
                    if status_element:
                        current_status = await status_element.inner_text()
                        if current_status != last_status:
                            print(f"Status update: {current_status}")
                            last_status = current_status
                            
                        # Check if completed or error
                        status_class = await status_element.get_attribute('class')
                        if 'completed' in status_class or 'error' in status_class:
                            print(f"Assessment finished with status: {status_class}")
                            break
                except:
                    pass
                
                # Check if results table is visible
                try:
                    results_element = await page.query_selector('#results')
                    if results_element:
                        is_visible = await results_element.is_visible()
                        if is_visible:
                            print("Results table is now visible!")
                            results_loaded = True
                            # Wait a bit more for all results to populate
                            await page.wait_for_timeout(5000)
                            break
                except:
                    pass
                
                # Check if we have any rows in the results table
                try:
                    rows = await page.query_selector_all('#resultsBody tr')
                    if len(rows) > 0:
                        print(f"Found {len(rows)} result rows")
                        if len(rows) > 10:  # Assume we have enough results
                            results_loaded = True
                            await page.wait_for_timeout(3000)  # Wait a bit more
                            break
                except:
                    pass
                
                # Wait before checking again
                await page.wait_for_timeout(2000)
            
            # Take screenshots at different stages
            print("Capturing screenshots...")
            
            # Set viewport to capture a reasonable area
            await page.set_viewport_size({"width": 1400, "height": 1200})
            
            # Take viewport screenshot (not full page to avoid memory issues)
            results_screenshot = f"assessment_results_viewport_{timestamp}.png"
            await page.screenshot(path=results_screenshot, full_page=False)
            print(f"Viewport screenshot saved: {results_screenshot}")
            
            # Try to capture just the results section if we can find it
            try:
                results_element = await page.query_selector('#results')
                if results_element:
                    # Scroll the results into view
                    await results_element.scroll_into_view_if_needed()
                    await page.wait_for_timeout(1000)
                    
                    results_only_screenshot = f"assessment_results_only_{timestamp}.png"
                    await results_element.screenshot(path=results_only_screenshot)
                    print(f"Results section screenshot saved: {results_only_screenshot}")
                    
                    # Also try to capture the results table specifically
                    table_element = await page.query_selector('#resultsTable')
                    if table_element:
                        table_screenshot = f"assessment_results_table_{timestamp}.png"
                        await table_element.screenshot(path=table_screenshot)
                        print(f"Results table screenshot saved: {table_screenshot}")
            except Exception as e:
                print(f"Could not capture results section separately: {e}")
            
            # Scroll down to capture more results
            for i in range(5):
                await page.evaluate('window.scrollBy(0, 500)')
                await page.wait_for_timeout(500)
                scroll_screenshot = f"assessment_scroll_{i}_{timestamp}.png"
                await page.screenshot(path=scroll_screenshot, full_page=False)
                print(f"Scroll position {i} screenshot saved: {scroll_screenshot}")
            
            print("\nAll screenshots captured successfully!")
            print(f"Check the following files:")
            print(f"- {form_screenshot}")
            print(f"- {results_screenshot}")
            print("- Plus additional scroll and detail screenshots")
            
        except Exception as e:
            print(f"Error occurred: {e}")
            # Take an error screenshot
            error_screenshot = f"assessment_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await page.screenshot(path=error_screenshot, full_page=True)
            print(f"Error screenshot saved: {error_screenshot}")
            raise
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_assessment_results())
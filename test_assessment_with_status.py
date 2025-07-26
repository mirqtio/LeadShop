#!/usr/bin/env python3
"""Test the assessment UI by submitting a URL and monitoring status"""

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
            # Navigate to the simple assessment page on local instance
            await page.goto('http://localhost:8001/api/v1/simple-assessment', 
                          wait_until='networkidle',
                          timeout=30000)
            
            print(f"[{datetime.now()}] Page loaded successfully!")
            
            # Wait for the form to be ready - look for any input field
            await page.wait_for_selector('input[type="url"], input[placeholder*="https://"], input', timeout=10000)
            
            # Fill in the URL field with Mozilla's website
            test_url = "https://www.mozilla.org"
            print(f"[{datetime.now()}] Entering URL: {test_url}")
            # Try different selectors for the URL input
            try:
                await page.fill('input[type="url"]', test_url)
            except:
                try:
                    await page.fill('input[placeholder*="https://"]', test_url)
                except:
                    # Find the first text input
                    await page.fill('input:first-of-type', test_url)
            
            # Fill in business name - find the second input field
            try:
                await page.fill('input[placeholder*="Corporation"], input[placeholder*="Business"], input:nth-of-type(2)', "Mozilla Foundation")
            except:
                print(f"[{datetime.now()}] Could not find business name field, continuing...")
            
            # Find and click the submit button
            print(f"[{datetime.now()}] Clicking Run Assessment button...")
            try:
                await page.click('button[type="submit"]')
            except:
                try:
                    await page.click('button:has-text("Run Assessment")')
                except:
                    # Click the first button
                    await page.click('button:first-of-type')
            
            # Wait for the status to show
            print(f"[{datetime.now()}] Waiting for assessment to start...")
            await page.wait_for_selector('#status, .status', timeout=10000)
            
            # Monitor the assessment progress
            for i in range(30):  # Check for up to 5 minutes
                await asyncio.sleep(10)  # Wait 10 seconds between checks
                
                # Take a screenshot to see current state
                screenshot_path = f'/Users/charlieirwin/LeadShop/assessment_progress_{i}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"[{datetime.now()}] Progress screenshot {i+1} saved to: {screenshot_path}")
                
                # Check if assessment completed
                try:
                    # Check for completed status in simple UI
                    completed = await page.query_selector('.status.completed')
                    if completed:
                        print(f"[{datetime.now()}] Assessment completed!")
                        break
                    
                    # Check for error status
                    error = await page.query_selector('.status.error')
                    if error:
                        print(f"[{datetime.now()}] Assessment failed!")
                        break
                        
                    # Check if results are visible
                    results_visible = await page.is_visible('#results')
                    if results_visible:
                        print(f"[{datetime.now()}] Results are now visible!")
                        break
                        
                except Exception:
                    pass
                
                # Get current status text
                try:
                    status_elem = await page.query_selector('#status, .status')
                    if status_elem:
                        status_text = await status_elem.inner_text()
                        print(f"[{datetime.now()}] Current status: {status_text}")
                except Exception:
                    pass
            
            # Take final screenshot
            final_screenshot = f'/Users/charlieirwin/LeadShop/assessment_final_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
            await page.screenshot(path=final_screenshot, full_page=True)
            print(f"[{datetime.now()}] Final screenshot saved to: {final_screenshot}")
            
            # Try to extract any visible results
            try:
                page_text = await page.inner_text('body')
                print(f"[{datetime.now()}] Page content preview (first 1000 chars):")
                print(page_text[:1000])
            except Exception as e:
                print(f"[{datetime.now()}] Could not extract page text: {e}")
            
            return final_screenshot
            
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
        print(f"\nTest completed! Final screenshot: {screenshot_path}")
    except Exception as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
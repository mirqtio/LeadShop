"""Test the assessment UI with all integrations"""

import asyncio
import time
from playwright.async_api import async_playwright

async def test_ui_assessment():
    """Test the full assessment through the UI"""
    
    # Use a real URL for better testing
    test_url = "https://example.com"
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)  # Set to True for CI
        page = await browser.new_page()
        
        # Enable console logging
        page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
        
        # Capture network failures
        page.on("requestfailed", lambda request: print(f"Request failed: {request.url} - {request.failure}"))
        
        # Capture responses
        page.on("response", lambda response: print(f"Response: {response.url} - {response.status}") if response.status >= 400 else None)
        
        try:
            # Navigate to assessment page
            await page.goto("http://localhost:8001/api/v1/simple-assessment/")
            
            # Fill in the form
            print(f"Testing with URL: {test_url}")
            await page.fill('#url', test_url)
            await page.fill('#businessName', "UI Test Business")
            
            # Submit the form
            await page.click('#submitBtn')
            
            # Wait for assessment to complete
            print("Waiting for assessment to complete...")
            await page.wait_for_selector('.status.completed', timeout=60000)
            
            # Check if results are displayed
            await page.wait_for_selector('#results', state='visible', timeout=10000)
            
            # Check for all assessment sections
            sections = [
                ('PageSpeed', 'text=Mobile Analysis'),
                ('Security', 'text=Security Headers'),
                ('GBP', 'text=Google Business Profile'),
                ('SEMrush', 'text=SEMrush Domain Analysis'),
                ('Screenshot', 'text=Screenshot Capture'),
                ('Visual Analysis', 'text=Visual UX Analysis')
            ]
            
            for name, selector in sections:
                element = await page.query_selector(selector)
                if element:
                    print(f"✓ {name} section found")
                else:
                    print(f"✗ {name} section NOT found")
            
            # Get the assessment status
            status_text = await page.text_content('.status.completed')
            print(f"\nAssessment status: {status_text}")
            
            # Take a screenshot for review
            await page.screenshot(path=f"ui_test_{int(time.time())}.png")
            
            print("\n✅ UI assessment test completed!")
            
        except Exception as e:
            print(f"\n❌ UI assessment test failed!")
            print(f"   Error: {str(e)}")
            
            # Take error screenshot
            await page.screenshot(path=f"ui_test_error_{int(time.time())}.png")
            raise
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_ui_assessment())
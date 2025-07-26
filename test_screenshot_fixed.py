"""
Test screenshot functionality after restart
"""
import asyncio
from playwright.async_api import async_playwright
import time

async def test_screenshots_fixed():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Navigate to the simple assessment UI
        await page.goto('http://app:8000/api/v1/simple-assessment/')
        
        # Fill form with a test URL
        await page.fill('#url', 'https://www.example.com')
        await page.fill('#businessName', 'Example Company')
        
        # Submit the form
        await page.click('#submitBtn')
        
        # Wait for the assessment to complete
        print("Waiting for assessment to complete...")
        await page.wait_for_selector('#dbRow', state='visible', timeout=60000)
        
        # Wait a bit more for screenshots to render
        await page.wait_for_timeout(2000)
        
        # Check if screenshots section is visible
        screenshots_visible = await page.is_visible('#screenshots')
        print(f"Screenshots section visible: {screenshots_visible}")
        
        if screenshots_visible:
            # Check for screenshot images
            screenshot_images = await page.query_selector_all('#screenshots img')
            print(f"Number of screenshot images found: {len(screenshot_images)}")
            
            for i, img in enumerate(screenshot_images):
                src = await img.get_attribute('src')
                alt = await img.get_attribute('alt')
                print(f"\nScreenshot {i+1}:")
                print(f"  Alt text: {alt}")
                print(f"  Image src preview: {src[:100] if src else 'None'}...")
                
                # Check if image loaded successfully
                is_visible = await img.is_visible()
                print(f"  Image visible: {is_visible}")
        
        # Take a screenshot as proof
        timestamp = int(time.time())
        await page.screenshot(path=f'screenshot_test_proof_{timestamp}.png', full_page=True)
        print(f"\nFull page screenshot saved as: screenshot_test_proof_{timestamp}.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_screenshots_fixed())
"""
Capture proof of decomposed metrics display using Playwright
"""
import asyncio
from playwright.async_api import async_playwright
import time

async def capture_assessment_proof():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # Run headless in Docker
        context = await browser.new_context(viewport={'width': 1400, 'height': 900})
        page = await context.new_page()
        
        # Enable console logging
        page.on("console", lambda msg: print(f"Console: {msg.text}"))
        page.on("pageerror", lambda err: print(f"Page error: {err}"))
        
        try:
            # Navigate to the assessment page
            print("Navigating to assessment page...")
            await page.goto('http://localhost:8000/api/v1/simple-assessment/')  # Use internal port in Docker
            await page.wait_for_load_state('networkidle')
            
            # Take initial screenshot
            await page.screenshot(path='decomposed_1_initial.png')
            print("Captured initial page")
            
            # Fill the form
            print("Filling form...")
            await page.fill('#url', 'https://www.example.com')
            await page.fill('#businessName', 'Example Company')
            
            # Take screenshot after filling
            await page.screenshot(path='decomposed_2_filled.png')
            
            # Submit the form
            print("Submitting form...")
            await page.click('#submitBtn')
            
            # Wait for assessment to complete
            print("Waiting for assessment to complete...")
            await page.wait_for_selector('#dbRow', state='visible', timeout=60000)
            
            # Wait a bit more for everything to render
            await page.wait_for_timeout(2000)
            
            # Take screenshot of results
            await page.screenshot(path='decomposed_3_results_top.png')
            
            # Check if decomposed metrics section exists
            decomposed_exists = await page.locator('#decomposedMetrics').count() > 0
            print(f"Decomposed metrics div exists in DOM: {decomposed_exists}")
            
            if decomposed_exists:
                is_visible = await page.locator('#decomposedMetrics').is_visible()
                print(f"Decomposed metrics div is visible: {is_visible}")
                
                # Get the display style
                display_style = await page.locator('#decomposedMetrics').evaluate('el => window.getComputedStyle(el).display')
                print(f"Decomposed metrics display style: {display_style}")
            
            # Scroll down to capture more
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
            await page.wait_for_timeout(1000)
            await page.screenshot(path='decomposed_4_results_middle.png')
            
            # Scroll to bottom
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(1000)
            await page.screenshot(path='decomposed_5_results_bottom.png')
            
            # Take full page screenshot
            await page.screenshot(path='decomposed_6_full_page.png', full_page=True)
            
            # Check for the text "Decomposed Metrics"
            decomposed_text = await page.locator('text="Decomposed Metrics"').count()
            print(f"Found 'Decomposed Metrics' text {decomposed_text} times")
            
            # Get page content for debugging
            content = await page.content()
            with open('decomposed_page_content.html', 'w') as f:
                f.write(content)
            print("Saved page content to decomposed_page_content.html")
            
            # Execute JavaScript to check state
            js_check = await page.evaluate('''() => {
                const div = document.getElementById('decomposedMetrics');
                const dbRow = document.getElementById('dbRow');
                return {
                    decomposedExists: !!div,
                    decomposedDisplay: div ? div.style.display : 'not found',
                    decomposedVisible: div ? div.offsetHeight > 0 : false,
                    dbRowVisible: dbRow ? dbRow.offsetHeight > 0 : false,
                    hasRedBorder: div ? div.style.border.includes('red') : false
                };
            }''')
            print(f"JavaScript check: {js_check}")
            
            print("\nScreenshots captured:")
            print("- decomposed_1_initial.png")
            print("- decomposed_2_filled.png") 
            print("- decomposed_3_results_top.png")
            print("- decomposed_4_results_middle.png")
            print("- decomposed_5_results_bottom.png")
            print("- decomposed_6_full_page.png")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_assessment_proof())
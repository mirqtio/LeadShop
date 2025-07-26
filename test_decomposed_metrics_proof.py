"""
Test to prove decomposed metrics display correctly
"""
import asyncio
from playwright.async_api import async_playwright
import time

async def test_decomposed_metrics():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Navigate to the simple assessment UI
        await page.goto('http://app:8000/api/v1/simple-assessment/')
        
        # Verify apple.com is pre-filled
        url_value = await page.input_value('#url')
        print(f"URL field value: {url_value}")
        assert url_value == "https://www.apple.com"
        
        # Submit the form
        await page.click('#submitBtn')
        
        # Wait for the assessment to complete - apple.com takes longer
        print("Waiting for assessment to complete...")
        await page.wait_for_selector('#dbRow', state='visible', timeout=120000)
        
        # Wait a bit more for all metrics to render
        await page.wait_for_timeout(2000)
        
        # Check for decomposed metrics table
        table_visible = await page.is_visible('#dbTable')
        print(f"Decomposed metrics table visible: {table_visible}")
        
        # Count the number of metrics displayed
        metric_rows = await page.query_selector_all('#dbTableBody tr:not(.category-header)')
        metric_count = len(metric_rows)
        print(f"Number of metrics displayed: {metric_count}")
        
        # Get all category headers
        category_headers = await page.query_selector_all('.category-header')
        categories = []
        for header in category_headers:
            text = await header.text_content()
            categories.append(text)
        print(f"Categories found: {categories}")
        
        # Get sample metrics from each category
        sample_metrics = {}
        for category in categories[:3]:  # First 3 categories
            # Find metrics under this category
            category_cell = await page.query_selector(f'.category-header:has-text("{category}")')
            if category_cell:
                # Get the parent row and find following rows until next category
                row = await category_cell.evaluate_handle('(el) => el.parentElement')
                next_row = await row.evaluate_handle('(el) => el.nextElementSibling')
                
                metrics_in_category = []
                for _ in range(3):  # Get up to 3 metrics per category
                    if next_row:
                        is_category = await next_row.evaluate('(el) => el.querySelector(".category-header") !== null')
                        if not is_category:
                            cells = await next_row.query_selector_all('td')
                            if len(cells) >= 2:
                                metric_name = await cells[0].text_content()
                                metric_value = await cells[1].text_content()
                                metrics_in_category.append(f"{metric_name}: {metric_value}")
                            next_row = await next_row.evaluate_handle('(el) => el.nextElementSibling')
                        else:
                            break
                
                sample_metrics[category] = metrics_in_category
        
        print("\nSample metrics by category:")
        for category, metrics in sample_metrics.items():
            print(f"\n{category}:")
            for metric in metrics:
                print(f"  - {metric}")
        
        # Check for screenshots section
        screenshots_visible = await page.is_visible('#screenshots')
        print(f"\nScreenshots section visible: {screenshots_visible}")
        
        # Take a full page screenshot as proof
        timestamp = int(time.time())
        await page.screenshot(path=f'decomposed_metrics_proof_{timestamp}.png', full_page=True)
        print(f"\nFull page screenshot saved as: decomposed_metrics_proof_{timestamp}.png")
        
        # Also take viewport screenshots of key sections
        # 1. Form area
        await page.screenshot(path=f'proof_1_form_{timestamp}.png', clip={'x': 0, 'y': 0, 'width': 1400, 'height': 300})
        
        # 2. Top of results table
        await page.evaluate('document.querySelector("#dbRow").scrollIntoView()')
        await page.wait_for_timeout(500)
        await page.screenshot(path=f'proof_2_table_top_{timestamp}.png', clip={'x': 0, 'y': 250, 'width': 1400, 'height': 600})
        
        # 3. Middle of results
        await page.evaluate('window.scrollBy(0, 600)')
        await page.wait_for_timeout(500)
        await page.screenshot(path=f'proof_3_table_middle_{timestamp}.png', clip={'x': 0, 'y': 0, 'width': 1400, 'height': 800})
        
        print(f"\nAll proof screenshots saved with timestamp: {timestamp}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_decomposed_metrics())
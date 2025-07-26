"""
End-to-End Playwright test for Simple Assessment UI
Tests the complete flow: form submission, assessment execution, DB storage, and result display
"""

import asyncio
import logging
from playwright.async_api import async_playwright, expect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_simple_assessment():
    """Test the complete simple assessment workflow"""
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=True,  # Run headless in Docker
            args=['--no-sandbox', '--disable-setuid-sandbox']  # Required for Docker
        )
        
        try:
            context = await browser.new_context()
            page = await context.new_page()
            
            # Set longer timeout for slow operations
            page.set_default_timeout(120000)  # 2 minutes
            
            # Navigate to simple assessment UI
            logger.info("Navigating to simple assessment UI...")
            await page.goto('http://localhost:8000/api/v1/simple-assessment/')
            
            # Wait for page to load
            await page.wait_for_selector('h1:has-text("Simple Assessment")')
            logger.info("Page loaded successfully")
            
            # Fill in the form
            logger.info("Filling form with test data...")
            await page.fill('#url', 'https://www.google.com')
            await page.fill('#businessName', 'Google')
            
            # Take screenshot before submission
            await page.screenshot(path='test_before_submit.png')
            
            # Submit the form
            logger.info("Submitting form...")
            await page.click('#submitBtn')
            
            # Wait for status to show
            await page.wait_for_selector('#status', state='visible')
            
            # Wait for assessment to complete (this may take a while)
            logger.info("Waiting for assessment to complete...")
            
            # Wait for either success or error
            await page.wait_for_selector('#dbRow', state='visible', timeout=90000)  # 90 seconds
            
            # Check if we have the database row
            db_row_visible = await page.is_visible('#dbRow')
            assert db_row_visible, "Database row should be visible after assessment"
            
            # Check if we have decomposed metrics
            decomposed_metrics_visible = await page.is_visible('#decomposedMetrics')
            logger.info(f"Decomposed metrics visible: {decomposed_metrics_visible}")
            
            # Check for specific columns in the main table
            logger.info("Checking for expected database columns...")
            columns_to_check = [
                'id',
                'lead_id', 
                'pagespeed_data',
                'security_headers',
                'gbp_data',
                'semrush_data',
                'visual_analysis',
                'total_score'
            ]
            
            for column in columns_to_check:
                column_exists = await page.locator(f'td:has-text("{column}")').count() > 0
                logger.info(f"Column '{column}' exists: {column_exists}")
            
            # Check if decomposed metrics are displayed
            if decomposed_metrics_visible:
                logger.info("Checking decomposed metrics categories...")
                categories = [
                    'PageSpeed',
                    'Security', 
                    'Google Business Profile',
                    'SEMrush',
                    'Visual Assessment'
                ]
                
                for category in categories:
                    category_exists = await page.locator(f'td:has-text("{category}")').count() > 0
                    logger.info(f"Category '{category}' exists: {category_exists}")
            
            # Check for screenshots section
            screenshots_visible = await page.is_visible('#screenshots')
            logger.info(f"Screenshots section visible: {screenshots_visible}")
            
            # Take final screenshot
            await page.screenshot(path='test_after_complete.png', full_page=True)
            
            # Get the final status
            status_text = await page.text_content('#status')
            logger.info(f"Final status: {status_text}")
            
            # Basic assertions
            assert 'completed' in status_text.lower(), f"Assessment should complete successfully. Status: {status_text}"
            
            # Get assessment ID if displayed (look for the first exact "id" match)
            try:
                assessment_id_match = await page.locator('td:text-is("id") + td').first.text_content()
                if assessment_id_match:
                    logger.info(f"Assessment ID: {assessment_id_match}")
            except:
                logger.info("Could not extract assessment ID")
            
            logger.info("Test completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Test failed with error: {e}")
            # Take error screenshot
            await page.screenshot(path='test_error.png', full_page=True)
            
            # Log page content for debugging
            content = await page.content()
            with open('test_error_page.html', 'w') as f:
                f.write(content)
            
            raise
            
        finally:
            await browser.close()


async def main():
    """Run the test"""
    try:
        await test_simple_assessment()
        print("\n✅ Simple Assessment E2E Test PASSED!")
    except Exception as e:
        print(f"\n❌ Simple Assessment E2E Test FAILED: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
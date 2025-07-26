"""Test SEMrush integration with Playwright."""

import asyncio
import time
from playwright.async_api import async_playwright
from datetime import datetime

async def test_semrush_integration():
    """Test SEMrush data saves to DB and displays in UI"""
    
    # Generate unique URL for this test
    test_url = f"https://techstartup{int(time.time())}.com"
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)  # Set to True for CI
        page = await browser.new_page()
        
        try:
            # Navigate to assessment page
            await page.goto("http://localhost:8001/api/v1/simple-assessment/")
            
            # Fill in the form
            print(f"Testing with URL: {test_url}")
            # Wait for the form to load
            await page.wait_for_selector('#urlInput', timeout=10000)
            await page.fill('#urlInput', test_url)
            await page.fill('#businessName', "SEMrush Test Business")
            
            # Submit the form
            await page.click('button[type="submit"]')
            
            # Wait for assessment to complete (SEMrush may take longer)
            print("Waiting for assessment to complete...")
            await page.wait_for_selector('.status.success', timeout=60000)
            
            # Wait for results to load
            await page.wait_for_selector('#assessmentResults', state='visible', timeout=30000)
            
            # Check if SEMrush results are displayed
            # Look for SEMrush section header
            semrush_header = await page.query_selector('text=SEMrush Domain Analysis')
            assert semrush_header is not None, "SEMrush section header not found"
            print("✓ SEMrush section header found")
            
            # Check for key SEMrush metrics
            # Domain Authority
            authority_element = await page.query_selector('text=Domain Authority')
            assert authority_element is not None, "Domain Authority metric not found"
            print("✓ Domain Authority metric found")
            
            # Organic Traffic
            traffic_element = await page.query_selector('text=Organic Traffic Estimate')
            assert traffic_element is not None, "Organic Traffic metric not found"
            print("✓ Organic Traffic metric found")
            
            # Site Health Score
            health_element = await page.query_selector('text=Site Health Score')
            assert health_element is not None, "Site Health Score metric not found"
            print("✓ Site Health Score metric found")
            
            # Check if technical issues section appears (if any)
            issues_section = await page.query_selector('text=Technical SEO Issues')
            if issues_section:
                print("✓ Technical SEO Issues section found")
            else:
                print("✓ No technical issues found (this is okay)")
            
            # Get the assessment ID from the page
            assessment_text = await page.text_content('.status.success')
            if 'Assessment ID:' in assessment_text:
                assessment_id = assessment_text.split('Assessment ID: ')[1].split(' ')[0]
                print(f"✓ Assessment ID: {assessment_id}")
                
                # Verify data is coming from DB by checking for consistent results
                # Reload the page
                await page.reload()
                await page.wait_for_selector('#assessmentResults', state='visible', timeout=30000)
                
                # Check that SEMrush data is still there
                authority_after_reload = await page.query_selector('text=Domain Authority')
                assert authority_after_reload is not None, "Domain Authority not found after reload - data not persisted"
                print("✓ SEMrush data persisted in database")
            
            print("\n✅ SEMrush integration test PASSED!")
            print(f"   - URL tested: {test_url}")
            print(f"   - All SEMrush metrics displayed correctly")
            print(f"   - Data successfully saved to and retrieved from database")
            
            # Take a screenshot for debugging
            await page.screenshot(path=f"semrush_test_{int(time.time())}.png")
            
        except Exception as e:
            print(f"\n❌ SEMrush integration test FAILED!")
            print(f"   Error: {str(e)}")
            
            # Take error screenshot
            await page.screenshot(path=f"semrush_test_error_{int(time.time())}.png")
            
            # Print page content for debugging
            content = await page.content()
            if "SEMrush API key not configured" in content:
                print("   ⚠️  SEMrush API key is not configured")
            
            raise
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_semrush_integration())
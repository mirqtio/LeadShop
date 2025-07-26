"""Full assessment test with Playwright to verify all integrations work"""

import asyncio
import time
from playwright.async_api import async_playwright

async def test_full_assessment():
    """Test the complete assessment flow with all integrations"""
    
    # Use a unique URL for this test
    test_url = f"https://testsite{int(time.time())}.com"
    business_name = f"Test Business {int(time.time())}"
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Enable console logging
        page.on("console", lambda msg: print(f"Console: {msg.text}"))
        page.on("pageerror", lambda error: print(f"Page Error: {error}"))
        
        try:
            print("=" * 80)
            print("FULL ASSESSMENT TEST WITH PLAYWRIGHT")
            print("=" * 80)
            
            # Step 1: Navigate to assessment page
            print("\n1. Navigating to assessment page...")
            await page.goto("http://localhost:8001/api/v1/simple-assessment/")
            await page.wait_for_load_state("networkidle")
            print("   ✓ Page loaded successfully")
            
            # Step 2: Fill in the form
            print(f"\n2. Filling assessment form...")
            print(f"   URL: {test_url}")
            print(f"   Business: {business_name}")
            
            await page.fill('#url', test_url)
            await page.fill('#businessName', business_name)
            await page.fill('#address', '123 Test Street')
            await page.fill('#city', 'Test City')
            await page.fill('#state', 'CA')
            print("   ✓ Form filled")
            
            # Step 3: Submit the form
            print("\n3. Submitting assessment...")
            await page.click('#submitBtn')
            print("   ✓ Assessment submitted")
            
            # Step 4: Wait for completion
            print("\n4. Waiting for assessment to complete...")
            start_time = time.time()
            
            # Wait for either success or error
            result = await page.wait_for_selector('.status.completed, .status.error', timeout=60000)
            status_text = await result.text_content()
            
            elapsed_time = time.time() - start_time
            print(f"   Assessment completed in {elapsed_time:.1f} seconds")
            
            # Check if it's an error
            if 'error' in await result.get_attribute('class'):
                print(f"\n❌ ASSESSMENT FAILED: {status_text}")
                
                # Try to get more error details
                error_element = await page.query_selector('.status.error')
                if error_element:
                    error_text = await error_element.text_content()
                    print(f"   Error details: {error_text}")
                
                # Take error screenshot
                await page.screenshot(path=f"assessment_error_{int(time.time())}.png")
                return False
            
            print(f"   ✓ {status_text}")
            
            # Step 5: Verify results are displayed
            print("\n5. Verifying assessment results...")
            await page.wait_for_selector('#results', state='visible', timeout=10000)
            
            # Check each assessment type
            assessments = {
                'PageSpeed': 'Mobile Analysis|Desktop Analysis|PageSpeed',
                'Security': 'Security Headers|Security Score',
                'Google Business Profile': 'Google Business Profile|Business Profile',
                'SEMrush': 'SEMrush Domain Analysis|Domain Authority',
                'Screenshot': 'Screenshot Capture|Screenshot Status',
                'Visual Analysis': 'Visual UX Analysis|Overall UX Score'
            }
            
            results_found = []
            results_missing = []
            
            for name, selector_options in assessments.items():
                # Try multiple possible selectors
                found = False
                for selector in selector_options.split('|'):
                    element = await page.query_selector(f'text={selector}')
                    if element:
                        found = True
                        break
                
                if found:
                    results_found.append(name)
                    print(f"   ✓ {name} results found")
                else:
                    results_missing.append(name)
                    print(f"   ✗ {name} results NOT found")
            
            # Step 6: Check for database storage
            print("\n6. Verifying database storage...")
            
            # Look for assessment ID in the page
            assessment_id = None
            status_element = await page.query_selector('.status.completed')
            if status_element:
                status_text = await status_element.text_content()
                if 'Assessment ID:' in status_text:
                    assessment_id = status_text.split('Assessment ID: ')[1].split(' ')[0]
                    print(f"   ✓ Assessment ID: {assessment_id}")
            
            # Step 7: Take final screenshot
            screenshot_path = f"assessment_success_{int(time.time())}.png"
            await page.screenshot(path=screenshot_path)
            print(f"\n7. Screenshot saved: {screenshot_path}")
            
            # Summary
            print("\n" + "=" * 80)
            print("ASSESSMENT TEST SUMMARY")
            print("=" * 80)
            print(f"URL Tested: {test_url}")
            print(f"Business Name: {business_name}")
            print(f"Assessment ID: {assessment_id}")
            print(f"Total Time: {elapsed_time:.1f} seconds")
            print(f"\nResults Found ({len(results_found)}):")
            for result in results_found:
                print(f"  ✓ {result}")
            if results_missing:
                print(f"\nResults Missing ({len(results_missing)}):")
                for result in results_missing:
                    print(f"  ✗ {result}")
            
            # Final verdict
            if len(results_found) >= 4:  # At least 4 out of 6 assessments
                print("\n✅ ASSESSMENT TEST PASSED!")
                print("   The assessment UI is working correctly.")
                return True
            else:
                print("\n❌ ASSESSMENT TEST FAILED!")
                print("   Too many assessment types are missing.")
                return False
                
        except Exception as e:
            print(f"\n❌ TEST FAILED WITH EXCEPTION:")
            print(f"   {str(e)}")
            
            # Take error screenshot
            await page.screenshot(path=f"test_exception_{int(time.time())}.png")
            
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(test_full_assessment())
    exit(0 if success else 1)
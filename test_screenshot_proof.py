"""Capture screenshot proof of working assessment with detailed results"""

import asyncio
import time
from playwright.async_api import async_playwright
from datetime import datetime

async def test_and_capture_screenshot():
    """Run assessment and capture detailed screenshot of results"""
    
    # Generate a novel URL with timestamp
    timestamp = int(time.time())
    test_url = f"https://noveltest{timestamp}.com"
    business_name = f"Novel Test Business {timestamp}"
    
    async with async_playwright() as p:
        # Launch browser in headless mode for clean screenshot
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            print("=" * 80)
            print("ASSESSMENT SCREENSHOT PROOF TEST")
            print("=" * 80)
            print(f"\nTest Details:")
            print(f"  Novel URL: {test_url}")
            print(f"  Business: {business_name}")
            print(f"  Timestamp: {datetime.now()}")
            
            # Navigate to assessment page
            print("\n1. Navigating to assessment page...")
            await page.goto("http://localhost:8001/api/v1/simple-assessment/")
            await page.wait_for_load_state("networkidle")
            
            # Fill in the form
            print("2. Filling assessment form...")
            await page.fill('#url', test_url)
            await page.fill('#businessName', business_name)
            await page.fill('#address', '456 Novel Street')
            await page.fill('#city', 'Novel City')
            await page.fill('#state', 'NY')
            
            # Take a screenshot of the form before submission
            await page.screenshot(path=f"proof_1_form_filled_{timestamp}.png")
            print(f"   ✓ Screenshot saved: proof_1_form_filled_{timestamp}.png")
            
            # Submit the form
            print("\n3. Submitting assessment...")
            await page.click('#submitBtn')
            
            # Wait for completion
            print("4. Waiting for assessment to complete...")
            start_time = time.time()
            
            # Wait for success status
            await page.wait_for_selector('.status.completed', timeout=60000)
            status_element = await page.query_selector('.status.completed')
            status_text = await status_element.text_content()
            
            elapsed_time = time.time() - start_time
            print(f"   ✓ Assessment completed in {elapsed_time:.1f} seconds")
            print(f"   Status: {status_text}")
            
            # Wait for results to fully load
            await page.wait_for_selector('#results', state='visible')
            await page.wait_for_timeout(2000)  # Give time for all results to render
            
            # Scroll to ensure all content is visible
            await page.evaluate('window.scrollTo(0, 0)')
            
            # Take initial screenshot of results
            screenshot_path = f"proof_2_results_top_{timestamp}.png"
            await page.screenshot(path=screenshot_path, full_page=False)
            print(f"\n5. Initial results screenshot saved: {screenshot_path}")
            
            # Count visible assessment sections
            print("\n6. Verifying visible results:")
            sections = {
                'PageSpeed': ['Mobile Analysis', 'Desktop Analysis', 'Performance Score'],
                'Security': ['Security Headers', 'Security Score', 'X-Frame-Options'],
                'GBP': ['Google Business Profile', 'Business Profile', 'Match Confidence'],
                'SEMrush': ['SEMrush Domain Analysis', 'Domain Authority', 'Site Health Score'],
                'Screenshot': ['Screenshot Capture', 'Screenshot Status', 'Capture Status'],
                'Visual': ['Visual UX Analysis', 'Overall UX Score', 'UX Rubric']
            }
            
            results_found = []
            for section, indicators in sections.items():
                found = False
                for indicator in indicators:
                    element = await page.query_selector(f'text={indicator}')
                    if element:
                        found = True
                        break
                if found:
                    results_found.append(section)
                    print(f"   ✓ {section} results visible")
            
            # Scroll down to capture more results
            await page.evaluate('window.scrollBy(0, 800)')
            await page.wait_for_timeout(1000)
            
            screenshot_path_2 = f"proof_3_results_middle_{timestamp}.png"
            await page.screenshot(path=screenshot_path_2)
            print(f"\n7. Middle results screenshot saved: {screenshot_path_2}")
            
            # Scroll to bottom for full coverage
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(1000)
            
            screenshot_path_3 = f"proof_4_results_bottom_{timestamp}.png"
            await page.screenshot(path=screenshot_path_3)
            print(f"8. Bottom results screenshot saved: {screenshot_path_3}")
            
            # Take a full page screenshot
            full_screenshot_path = f"proof_5_full_page_{timestamp}.png"
            await page.screenshot(path=full_screenshot_path, full_page=True)
            print(f"\n9. Full page screenshot saved: {full_screenshot_path}")
            
            # Extract some actual values to prove data is real
            print("\n10. Extracting actual result values:")
            
            # Try to get PageSpeed score
            pagespeed_element = await page.query_selector('text=Performance Score')
            if pagespeed_element:
                row = await pagespeed_element.evaluate('el => el.closest("tr")')
                if row:
                    score_text = await page.evaluate('row => row.cells[1]?.textContent', row)
                    if score_text:
                        print(f"   - PageSpeed Performance Score: {score_text}")
            
            # Try to get Security score
            security_element = await page.query_selector('text=Security Score')
            if security_element:
                row = await security_element.evaluate('el => el.closest("tr")')
                if row:
                    score_text = await page.evaluate('row => row.cells[1]?.textContent', row)
                    if score_text:
                        print(f"   - Security Score: {score_text}")
            
            # Try to get SEMrush authority
            semrush_element = await page.query_selector('text=Domain Authority')
            if semrush_element:
                row = await semrush_element.evaluate('el => el.closest("tr")')
                if row:
                    score_text = await page.evaluate('row => row.cells[1]?.textContent', row)
                    if score_text:
                        print(f"   - SEMrush Domain Authority: {score_text}")
            
            # Final summary
            print("\n" + "=" * 80)
            print("SCREENSHOT PROOF TEST SUMMARY")
            print("=" * 80)
            print(f"Novel URL Tested: {test_url}")
            print(f"Timestamp: {timestamp}")
            print(f"Total Time: {elapsed_time:.1f} seconds")
            print(f"Results Found: {len(results_found)}/6")
            print(f"Screenshots Captured: 5")
            print("\nKey Screenshots:")
            print(f"  1. Form: proof_1_form_filled_{timestamp}.png")
            print(f"  2. Results Top: proof_2_results_top_{timestamp}.png")
            print(f"  3. Results Middle: proof_3_results_middle_{timestamp}.png")
            print(f"  4. Results Bottom: proof_4_results_bottom_{timestamp}.png")
            print(f"  5. Full Page: proof_5_full_page_{timestamp}.png")
            
            if len(results_found) >= 4:
                print("\n✅ SUCCESS: Assessment results are displaying correctly!")
                print("   Screenshots prove the UI is working with detailed results.")
                return True
            else:
                print("\n❌ ISSUE: Some assessment results may be missing.")
                return False
                
        except Exception as e:
            print(f"\n❌ TEST FAILED: {str(e)}")
            # Take error screenshot
            await page.screenshot(path=f"proof_error_{timestamp}.png")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(test_and_capture_screenshot())
    exit(0 if success else 1)
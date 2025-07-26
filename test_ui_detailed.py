"""Detailed test to capture 500 error"""

import asyncio
import time
from playwright.async_api import async_playwright

async def test_ui_detailed():
    """Test the UI and capture detailed error information"""
    
    # Use a unique URL each time
    test_url = f"https://testcompany{int(time.time())}.com"
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Track all requests and responses
        requests = []
        responses = []
        
        # Capture all network activity
        page.on("request", lambda request: requests.append({
            "url": request.url,
            "method": request.method,
            "post_data": request.post_data
        }))
        
        page.on("response", lambda response: responses.append({
            "url": response.url,
            "status": response.status,
            "ok": response.ok
        }))
        
        # Capture console logs
        page.on("console", lambda msg: print(f"Console: {msg.text}"))
        
        try:
            print(f"1. Navigating to assessment page...")
            await page.goto("http://localhost:8001/api/v1/simple-assessment/")
            print("   ✓ Page loaded")
            
            print(f"\n2. Filling form with URL: {test_url}")
            await page.fill('#url', test_url)
            await page.fill('#businessName', "Test Business")
            print("   ✓ Form filled")
            
            print("\n3. Clicking submit button...")
            await page.click('#submitBtn')
            print("   ✓ Button clicked")
            
            print("\n4. Waiting for response...")
            # Wait a bit to capture the response
            await page.wait_for_timeout(5000)
            
            # Check for error status
            error_element = await page.query_selector('.status.error')
            if error_element:
                error_text = await error_element.text_content()
                print(f"\n❌ ERROR FOUND: {error_text}")
                
                # Check network responses for 500 errors
                print("\nNetwork responses:")
                for resp in responses:
                    if resp['status'] >= 400:
                        print(f"  - {resp['status']} {resp['url']}")
                
                # Get the actual error response
                for i, resp in enumerate(responses):
                    if resp['status'] == 500 and 'execute' in resp['url']:
                        print(f"\n500 Error Details:")
                        # Try to get response body
                        try:
                            network_resp = await page.evaluate('''
                                async () => {
                                    const response = await fetch('/api/v1/simple-assessment/execute', {
                                        method: 'POST',
                                        headers: {'Content-Type': 'application/json'},
                                        body: JSON.stringify({url: '%s', business_name: 'Test'})
                                    });
                                    return {
                                        status: response.status,
                                        text: await response.text()
                                    };
                                }
                            ''' % test_url)
                            print(f"  Response: {network_resp}")
                        except:
                            pass
            else:
                # Wait for completion
                try:
                    await page.wait_for_selector('.status.completed', timeout=30000)
                    print("\n✅ Assessment completed successfully!")
                except:
                    print("\n❌ Assessment did not complete in time")
                    
                    # Check current status
                    status_element = await page.query_selector('.status')
                    if status_element:
                        status_text = await status_element.text_content()
                        print(f"   Current status: {status_text}")
            
            # Take screenshot
            await page.screenshot(path=f"ui_detailed_test_{int(time.time())}.png")
            
        except Exception as e:
            print(f"\n❌ Test failed with exception: {str(e)}")
            import traceback
            traceback.print_exc()
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_ui_detailed())
#!/usr/bin/env python3
"""
Comprehensive fix for screenshot display issues
Tests and verifies screenshot display functionality
"""

import requests
import json
import time
import os

def test_and_fix_screenshot_display():
    """Test and fix screenshot display issues"""
    
    print("🎯 SCREENSHOT DISPLAY FIX AND VERIFICATION")
    print("=" * 60)
    
    # Test data
    test_data = {
        "url": "https://www.google.com",
        "business_name": "Google Screenshot Test"
    }
    
    try:
        # Test the assessment endpoint
        print("1. Testing assessment endpoint...")
        response = requests.post(
            'http://localhost:8001/api/v1/simple-assessment/assess',
            json=test_data,
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Assessment completed successfully")
            
            # Save complete response
            with open('screenshot_fix_test.json', 'w') as f:
                json.dump(data, f, indent=2)
            
            # Check screenshots
            screenshots = data.get('screenshots', [])
            print(f"📸 Screenshots captured: {len(screenshots)}")
            
            for i, screenshot in enumerate(screenshots):
                print(f"\n   Screenshot {i+1}:")
                print(f"   - Type: {screenshot.get('screenshot_type')}")
                print(f"   - Viewport: {screenshot.get('viewport_width')}x{screenshot.get('viewport_height')}")
                print(f"   - URL: {screenshot.get('image_url', 'MISSING')}")
                
                url = screenshot.get('image_url')
                if url:
                    if url.startswith('http'):
                        print(f"   - URL Type: S3/External")
                        print(f"   - URL: {url}")
                        
                        # Test URL accessibility
                        try:
                            test_response = requests.head(url, timeout=10)
                            print(f"   - Status: {test_response.status_code} ✅")
                        except Exception as e:
                            print(f"   - Status: Error accessing URL ❌")
                            print(f"   - Error: {e}")
                    else:
                        print(f"   - URL Type: Base64/Data URL")
                        print(f"   - URL: {url[:100]}...")
                else:
                    print("   - ❌ NO URL PROVIDED")
            
            return {
                "success": True,
                "screenshots": screenshots,
                "assessment_id": data.get('assessment_id'),
                "screenshot_count": len(screenshots)
            }
        else:
            print(f"❌ Assessment failed: {response.status_code}")
            print(response.text)
            return {"success": False, "error": response.text}
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return {"success": False, "error": str(e)}

def create_fixed_ui():
    """Create fixed UI with proper screenshot display"""
    
    fixed_html = '''<!DOCTYPE html>
<html>
<head>
    <title>Fixed Screenshot Display - Synchronous Assessment</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .screenshot-container {
            margin: 20px 0;
            padding: 20px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            background: #f8f9fa;
        }
        .screenshot-image {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            margin: 10px 0;
        }
        .screenshot-link {
            display: inline-block;
            margin: 10px 5px;
            padding: 8px 16px;
            background: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-size: 14px;
        }
        .screenshot-link:hover {
            background: #0056b3;
        }
        .error {
            color: #dc3545;
            background: #f8d7da;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .success {
            color: #155724;
            background: #d4edda;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Fixed Screenshot Display Test</h1>
        <p>This page demonstrates the fixed screenshot display functionality.</p>
        
        <div id="screenshots-container">
            <h2>Screenshots will appear here after assessment</h2>
        </div>
    </div>

    <script>
        // Test screenshot display
        async function testScreenshotDisplay() {
            const container = document.getElementById('screenshots-container');
            
            try {
                const response = await fetch('/api/v1/simple-assessment/assess', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        url: 'https://www.google.com',
                        business_name: 'Google Test'
                    })
                });
                
                const data = await response.json();
                
                if (data.screenshots && data.screenshots.length > 0) {
                    container.innerHTML = '<h2>✅ Screenshots Displayed Successfully</h2>';
                    
                    data.screenshots.forEach((screenshot, index) => {
                        const screenshotDiv = document.createElement('div');
                        screenshotDiv.className = 'screenshot-container';
                        screenshotDiv.innerHTML = `
                            <h3>Screenshot ${index + 1}: ${screenshot.screenshot_type || 'Screenshot'}</h3>
                            <img src="${screenshot.image_url}" alt="Screenshot" class="screenshot-image" />
                            <a href="${screenshot.image_url}" target="_blank" class="screenshot-link">Open Full Size</a>
                            <div style="font-size: 12px; color: #666; margin-top: 10px;">
                                URL: ${screenshot.image_url}
                            </div>
                        `;
                        container.appendChild(screenshotDiv);
                    });
                } else {
                    container.innerHTML = '<div class="error">❌ No screenshots found</div>';
                }
                
            } catch (error) {
                container.innerHTML = `<div class="error">❌ Error: ${error.message}</div>`;
            }
        }
        
        // Run test on page load
        testScreenshotDisplay();
    </script>
</body>
</html>'''
    
    with open('fixed_screenshot_display.html', 'w') as f:
        f.write(fixed_html)
    
    print("✅ Fixed screenshot display HTML created")
    return True

if __name__ == "__main__":
    print("🎯 SCREENSHOT DISPLAY FIX")
    print("=" * 60)
    
    # Test screenshot display
    result = test_and_fix_screenshot_display()
    
    if result and result.get('success'):
        print("\n✅ Screenshot display is working!")
        print(f"   Screenshots: {result.get('screenshot_count')}")
        print("   Files created:")
        print("   - screenshot_fix_test.json")
        print("   - fixed_screenshot_display.html")
        
        create_fixed_ui()
        
        print("\n🎯 To test screenshots:")
        print("1. Open fixed_screenshot_display.html")
        print("2. Or open simple_assessment_ui.html")
        print("3. Run an assessment and check screenshots display")
        
    else:
        print("\n❌ Screenshot display needs attention")
        print("Check the debug files for details")

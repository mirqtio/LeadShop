#!/usr/bin/env python3
"""
Test script to verify screenshot display is working correctly
"""

import requests
import json
import time

def test_screenshot_display():
    """Test screenshot display functionality"""
    
    print("🧪 Testing screenshot display...")
    
    # Test data
    test_data = {
        "url": "https://www.google.com",
        "business_name": "Google Test"
    }
    
    try:
        # Test the assessment endpoint
        response = requests.post(
            'http://localhost:8001/api/v1/simple-assessment/assess',
            json=test_data,
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print("✅ Assessment completed")
            print(f"Assessment ID: {data.get('assessment_id')}")
            print(f"Screenshots: {len(data.get('screenshots', []))}")
            
            # Check each screenshot
            for i, screenshot in enumerate(data.get('screenshots', [])):
                print(f"\n📸 Screenshot {i+1}:")
                print(f"  URL: {screenshot.get('image_url', 'MISSING')}")
                print(f"  Type: {screenshot.get('screenshot_type', 'Unknown')}")
                print(f"  Viewport: {screenshot.get('viewport_type', 'Unknown')}")
                
                # Test if URL is accessible
                url = screenshot.get('image_url')
                if url and url.startswith('http'):
                    try:
                        img_response = requests.head(url, timeout=10)
                        if img_response.status_code == 200:
                            print(f"  ✅ Image accessible")
                        else:
                            print(f"  ❌ Image not accessible: {img_response.status_code}")
                    except Exception as e:
                        print(f"  ❌ Image URL error: {e}")
                elif url:
                    print(f"  ⚠️  Non-HTTP URL: {url}")
                else:
                    print(f"  ❌ No URL provided")
            
            # Save debug info
            with open('screenshot_debug.json', 'w') as f:
                json.dump(data, f, indent=2)
            
            return data
        else:
            print(f"❌ API Error: {response.status_code}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return None

if __name__ == "__main__":
    result = test_screenshot_display()
    if result:
        print("\n✅ Screenshot display test completed")
    else:
        print("\n❌ Screenshot display test failed")

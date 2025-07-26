"""
Test each assessment component individually
"""
import asyncio
from src.assessments.pagespeed import assess_pagespeed
from src.assessments.security_analysis import assess_security_headers
from src.assessments.screenshot_capture import capture_website_screenshots
import json

async def test_components():
    url = "https://www.example.com"
    lead_id = 1
    assessment_id = 1
    
    print("Testing individual assessment components...\n")
    
    # Test PageSpeed
    print("1. Testing PageSpeed...")
    try:
        result = await asyncio.wait_for(assess_pagespeed(url), timeout=30)
        print(f"   ✓ PageSpeed: Success")
        if result and 'mobile_analysis' in result:
            score = result['mobile_analysis'].get('core_web_vitals', {}).get('performance_score', 0)
            print(f"     Mobile Score: {score}")
    except asyncio.TimeoutError:
        print(f"   ✗ PageSpeed: Timeout")
    except Exception as e:
        print(f"   ✗ PageSpeed: {e}")
    
    # Test Security
    print("\n2. Testing Security Headers...")
    try:
        result = await asyncio.wait_for(assess_security_headers(url), timeout=10)
        print(f"   ✓ Security: Success")
        if result and 'security_score' in result:
            print(f"     Security Score: {result['security_score']}")
    except asyncio.TimeoutError:
        print(f"   ✗ Security: Timeout")
    except Exception as e:
        print(f"   ✗ Security: {e}")
    
    # Test Screenshots
    print("\n3. Testing Screenshot Capture...")
    try:
        result = await asyncio.wait_for(capture_website_screenshots(url, lead_id, assessment_id), timeout=30)
        print(f"   ✓ Screenshots: Success")
        if result:
            print(f"     Captured {len(result)} screenshots")
    except asyncio.TimeoutError:
        print(f"   ✗ Screenshots: Timeout")
    except Exception as e:
        print(f"   ✗ Screenshots: {e}")
    
    print("\n\nNote: Skipping SEMrush (API balance), GBP (needs proper params), and Visual Analysis (depends on screenshots)")

if __name__ == "__main__":
    asyncio.run(test_components())
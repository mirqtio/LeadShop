#!/usr/bin/env python3
"""
Test PageSpeed API directly to diagnose issues
"""

import asyncio
import httpx
from src.core.config import settings

async def test_pagespeed_direct():
    """Test PageSpeed API with various URLs"""
    
    # Test URLs
    test_urls = [
        "https://www.google.com/",
        "https://www.example.com/",
        "https://www.github.com/"
    ]
    
    api_key = settings.GOOGLE_PAGESPEED_API_KEY
    base_url = "https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed"
    
    print(f"Testing PageSpeed API with key: {api_key[:10]}...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for url in test_urls:
            print(f"\n🔍 Testing: {url}")
            
            params = {
                "url": url,
                "key": api_key,
                "strategy": "mobile",
                "category": ["performance", "accessibility", "best-practices", "seo"],
                "locale": "en_US"
            }
            
            try:
                response = await client.get(base_url, params=params)
                
                print(f"  Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    lighthouse_result = data.get("lighthouseResult", {})
                    categories = lighthouse_result.get("categories", {})
                    
                    if "performance" in categories:
                        score = categories["performance"].get("score", 0) * 100
                        print(f"  ✅ Performance Score: {score:.0f}")
                    else:
                        print(f"  ❌ No performance score in response")
                        
                    # Check for any error indicators
                    if "error" in data:
                        print(f"  ⚠️ Error in response: {data['error']}")
                else:
                    print(f"  ❌ Error: {response.text[:200]}")
                    
            except httpx.TimeoutException:
                print(f"  ❌ Timeout after 60 seconds")
            except Exception as e:
                print(f"  ❌ Exception: {type(e).__name__}: {str(e)}")
    
    print("\n\n📊 Testing with curl to compare...")
    
    # Test with curl to see if it's our client issue
    import subprocess
    
    curl_url = f"{base_url}?url=https://www.example.com/&key={api_key}&strategy=mobile"
    print(f"Running: curl '{curl_url[:100]}...'")
    
    try:
        result = subprocess.run(
            ["curl", "-s", "-m", "60", curl_url],
            capture_output=True,
            text=True,
            timeout=65
        )
        
        if result.returncode == 0:
            import json
            try:
                data = json.loads(result.stdout)
                if "error" in data:
                    print(f"❌ API Error: {data['error']}")
                else:
                    print(f"✅ Curl succeeded! Got response with {len(result.stdout)} bytes")
                    if "lighthouseResult" in data:
                        print("✅ Contains lighthouseResult")
            except:
                print(f"Response preview: {result.stdout[:200]}")
        else:
            print(f"❌ Curl failed with code {result.returncode}")
    except subprocess.TimeoutExpired:
        print("❌ Curl timeout")
    except Exception as e:
        print(f"❌ Curl error: {e}")

if __name__ == "__main__":
    asyncio.run(test_pagespeed_direct())
#!/usr/bin/env python3
"""
Test PageSpeed API parameter encoding
"""

import asyncio
import httpx
from urllib.parse import urlencode, urlparse, parse_qs
import requests

async def test_parameter_encoding():
    """Test how parameters are being encoded"""
    
    api_key = "AIzaSyAgsawn7gSnxiZ2stp_K1vS6oQ47FN_XZE"
    base_url = "https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed"
    
    # Test with httpx (what our code uses)
    print("🔍 Testing with httpx (our current implementation):")
    
    params = {
        "url": "https://www.google.com",
        "key": api_key,
        "strategy": "mobile",
        "category": ["performance", "accessibility", "best-practices", "seo"],
        "locale": "en_US"
    }
    
    async with httpx.AsyncClient() as client:
        # Create request to see URL
        request = client.build_request("GET", base_url, params=params)
        print(f"URL: {request.url}")
        
        # Parse the query string
        parsed = urlparse(str(request.url))
        query_params = parse_qs(parsed.query)
        print(f"\nParsed params:")
        for k, v in query_params.items():
            if k == 'key':
                print(f"  {k}: [hidden]")
            else:
                print(f"  {k}: {v}")
    
    print("\n\n🔍 Testing with requests library:")
    
    # Test with requests library
    response = requests.get(base_url, params=params)
    print(f"URL: {response.url[:100]}...")
    
    # Parse the query string
    parsed = urlparse(response.url)
    query_params = parse_qs(parsed.query)
    print(f"\nParsed params:")
    for k, v in query_params.items():
        if k == 'key':
            print(f"  {k}: [hidden]")
        else:
            print(f"  {k}: {v}")
    
    print("\n\n🔍 Testing manual URL construction (what should work):")
    
    # Build URL manually the way Google expects
    manual_params = [
        ("url", "https://www.google.com"),
        ("key", api_key),
        ("strategy", "mobile"),
        ("category", "performance"),
        ("category", "accessibility"), 
        ("category", "best-practices"),
        ("category", "seo"),
        ("locale", "en_US")
    ]
    
    query_string = urlencode(manual_params)
    manual_url = f"{base_url}?{query_string}"
    print(f"Manual URL: {manual_url[:100]}...")
    
    # Test the manual URL
    print("\n📊 Testing manual URL with curl:")
    import subprocess
    
    result = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", manual_url],
        capture_output=True,
        text=True
    )
    
    print(f"HTTP Status: {result.stdout}")
    
    # Now test with httpx using manual construction
    print("\n\n🔧 Testing httpx with manual parameter encoding:")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Don't use params dict, use pre-built URL
        response = await client.get(manual_url)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "lighthouseResult" in data:
                categories = data["lighthouseResult"].get("categories", {})
                if "performance" in categories:
                    score = categories["performance"].get("score", 0) * 100
                    print(f"✅ Performance Score: {score:.0f}")
        else:
            print(f"❌ Error: {response.text[:200]}")

if __name__ == "__main__":
    asyncio.run(test_parameter_encoding())
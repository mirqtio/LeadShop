#!/usr/bin/env python3
"""
Test PageSpeed with multiple URLs to see which ones work
"""

import asyncio
import httpx

async def test_urls():
    """Test various URLs with PageSpeed API"""
    
    test_urls = [
        ("https://www.google.com", "Google"),
        ("https://www.apple.com", "Apple"),
        ("https://www.microsoft.com", "Microsoft"),
        ("https://www.amazon.com", "Amazon"),
        ("https://www.wikipedia.org", "Wikipedia"),
        ("https://www.stackoverflow.com", "Stack Overflow"),
        ("https://www.reddit.com", "Reddit"),
        ("https://www.bbc.com", "BBC"),
        ("https://www.nytimes.com", "NY Times"),
        ("https://www.tesla.com", "Tesla")
    ]
    
    api_key = "AIzaSyAgsawn7gSnxiZ2stp_K1vS6oQ47FN_XZE"
    base_url = "https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed"
    
    print("Testing PageSpeed API with various URLs:\n")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for url, name in test_urls:
            params = {
                "url": url,
                "key": api_key,
                "strategy": "mobile",
                "category": ["performance"],
                "locale": "en_US"
            }
            
            try:
                response = await client.get(base_url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    lighthouse = data.get("lighthouseResult", {})
                    categories = lighthouse.get("categories", {})
                    score = categories.get("performance", {}).get("score", 0) * 100
                    print(f"✅ {name:20} Score: {score:3.0f} - Success")
                else:
                    error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    error_msg = error_data.get("error", {}).get("message", response.text[:100])
                    print(f"❌ {name:20} Status: {response.status_code} - {error_msg[:50]}")
                    
            except Exception as e:
                print(f"❌ {name:20} Error: {type(e).__name__}: {str(e)[:50]}")
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(test_urls())
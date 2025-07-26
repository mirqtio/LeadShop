#!/usr/bin/env python3
"""
Test script to get raw PageSpeed data and save it
"""

import asyncio
import json
from src.assessments.pagespeed import get_pagespeed_client

async def test_pagespeed():
    print("Testing PageSpeed API...")
    
    client = get_pagespeed_client()
    
    # Try a simple site that should work
    url = "https://www.example.org"
    
    try:
        print(f"Analyzing {url}...")
        results = await client.analyze_mobile_first(url)
        
        # Save the raw results
        with open('pagespeed_raw_results.json', 'w') as f:
            output = {
                "mobile": results["mobile"].dict() if "mobile" in results else None,
                "desktop": results["desktop"].dict() if "desktop" in results else None
            }
            json.dump(output, f, indent=2)
            
        print("Results saved to pagespeed_raw_results.json")
        
        # Print summary
        if "mobile" in results:
            mobile = results["mobile"]
            print(f"\nMobile Performance Score: {mobile.core_web_vitals.performance_score}")
            print(f"FCP: {mobile.core_web_vitals.first_contentful_paint}ms")
            print(f"LCP: {mobile.core_web_vitals.largest_contentful_paint}ms")
            print(f"CLS: {mobile.core_web_vitals.cumulative_layout_shift}")
            print(f"TBT: {mobile.core_web_vitals.total_blocking_time}ms")
            print(f"TTI: {mobile.core_web_vitals.time_to_interactive}ms")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_pagespeed())
#!/usr/bin/env python3
"""
Run a simple assessment test to verify the system is working
"""

import asyncio
import httpx
from datetime import datetime

async def run_test():
    print("🚀 Running simple assessment test...")
    
    # Create HTTP client
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Submit assessment
        url = "http://localhost:8001/api/v1/simple-assessment/submit"
        data = {
            "businessUrl": "https://www.microsoft.com",
            "businessName": "Microsoft Corporation",
            "city": "Redmond",
            "state": "WA"
        }
        
        print(f"📤 Submitting assessment for {data['businessName']}...")
        print(f"   URL: {data['businessUrl']}")
        
        try:
            response = await client.post(url, data=data)
            response.raise_for_status()
            
            result = response.json()
            print(f"✅ Assessment submitted! ID: {result.get('assessmentId')}")
            print(f"   Response: {result}")
            
            # If we got an assessment ID, it means the system is working
            if result.get('assessmentId'):
                print(f"\n✅ SUCCESS: Assessment system is operational!")
                print(f"   Assessment ID: {result['assessmentId']}")
                print(f"   Time: {datetime.now()}")
                return result['assessmentId']
            else:
                print(f"\n❌ ERROR: No assessment ID returned")
                print(f"   Response: {result}")
                
        except Exception as e:
            print(f"\n❌ ERROR: {type(e).__name__}: {e}")
            return None

if __name__ == "__main__":
    assessment_id = asyncio.run(run_test())
    if assessment_id:
        print(f"\n🎯 Next step: Check assessment results at:")
        print(f"   http://localhost:8001/api/v1/simple-assessment")
        print(f"   Or check database for assessment ID: {assessment_id}")
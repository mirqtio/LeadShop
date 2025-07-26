#!/usr/bin/env python3
"""
Final test of complete assessment system
"""
import asyncio
import httpx
import json
from datetime import datetime

async def test_assessment():
    """Test the complete assessment endpoint"""
    
    url = "https://www.github.com"
    business_name = "GitHub"
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Start assessment
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Starting assessment for {url}...")
        
        response = await client.post(
            "http://localhost:8001/api/v1/complete-assessment/assess",
            json={"url": url, "business_name": business_name}
        )
        
        if response.status_code != 200:
            print(f"Error starting assessment: {response.text}")
            return
            
        data = response.json()
        assessment_id = data["assessment_id"]
        print(f"Assessment ID: {assessment_id}")
        print(f"Status: {data['status']}")
        print(f"Score: {data.get('score', 'N/A')}")
        print(f"Message: {data['message']}")
        
        # Wait a moment then check status
        await asyncio.sleep(2)
        
        # Check status
        status_response = await client.get(
            f"http://localhost:8001/api/v1/complete-assessment/status/{assessment_id}"
        )
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Status check:")
            print(f"Status: {status_data.get('status', 'unknown')}")
            print(f"Progress: {status_data.get('progress', 0)}%")
            print(f"Score: {status_data.get('score', 'N/A')}")
            print(f"Database saved: {status_data.get('database_saved', False)}")
            
            components = status_data.get('components', {})
            if components:
                print("\nComponent statuses:")
                for comp, status in components.items():
                    print(f"  - {comp}: {status}")
            
            # Check results
            results = status_data.get('results', {})
            if results:
                print("\nComponent results:")
                for comp, result in results.items():
                    if result:
                        if isinstance(result, dict):
                            success = result.get('success', False)
                            if success:
                                print(f"  - {comp}: ✅ Success")
                            else:
                                print(f"  - {comp}: ❌ Failed - {result.get('error_message', 'Unknown error')}")
                        else:
                            print(f"  - {comp}: ✅ Has data")
                    else:
                        print(f"  - {comp}: ❌ No data")

if __name__ == "__main__":
    asyncio.run(test_assessment())
#!/usr/bin/env python3
"""
Test complete assessment without database saves in individual components
"""
import asyncio
import httpx
import json
from datetime import datetime

async def test_assessment():
    """Test the complete assessment endpoint"""
    
    url = "https://www.example.com"
    business_name = "Example Company"
    
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
        print(f"Assessment started with ID: {assessment_id}")
        
        # Poll for status
        while True:
            await asyncio.sleep(5)
            
            status_response = await client.get(
                f"http://localhost:8001/api/v1/complete-assessment/status/{assessment_id}"
            )
            
            status_data = status_response.json()
            status = status_data.get("status", "unknown")
            progress = status_data.get("progress", 0)
            
            # Print component status
            components = status_data.get("components", {})
            comp_status = " | ".join([f"{k}:{v}" for k, v in components.items() if v != "pending"])
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Status: {status} | Progress: {progress}% | {comp_status}")
            
            if status in ["completed", "failed"]:
                print(f"\nFinal status: {status}")
                
                if status == "completed":
                    print(f"Overall score: {status_data.get('score', 'N/A')}")
                    print(f"Database saved: {status_data.get('database_saved', False)}")
                    
                    # Check database results
                    if status_data.get('db_results'):
                        print("\nDatabase results:")
                        for component, data in status_data['db_results'].items():
                            if data:
                                print(f"  - {component}: ✓")
                            else:
                                print(f"  - {component}: ✗")
                
                elif status == "failed":
                    print(f"Error: {status_data.get('error', 'Unknown error')}")
                
                # Check actual database
                print("\nChecking database directly...")
                db_check = await client.get(
                    f"http://localhost:8001/api/v1/assessment-ui/results/{assessment_id}"
                )
                if db_check.status_code == 200:
                    db_data = db_check.json()
                    print(f"Database total_score: {db_data.get('execution', {}).get('overall_score', 'N/A')}")
                else:
                    print(f"Could not fetch from database: {db_check.status_code}")
                
                break

if __name__ == "__main__":
    asyncio.run(test_assessment())
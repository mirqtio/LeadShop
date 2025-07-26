#!/usr/bin/env python3
"""
Test screenshot URL storage fix
"""

import requests
import json
import time
import asyncio

def run_test_assessment():
    """Run a quick test assessment"""
    
    print("🚀 Testing screenshot URL storage fix...")
    
    # Use a fast-loading site for quick test
    assessment_data = {
        "url": "https://www.example.com",
        "business_name": "Example Test",
        "city": "New York", 
        "state": "NY"
    }
    
    print(f"📤 Submitting test assessment: {json.dumps(assessment_data, indent=2)}")
    
    response = requests.post(
        "http://localhost:8001/api/v1/simple-assessment/execute",
        json=assessment_data,
        timeout=120
    )
    
    if response.status_code == 200:
        print("✅ Assessment completed!")
        result = response.json()
        
        # Extract assessment ID
        assessment_id = None
        if 'assessment_id' in result:
            assessment_id = result['assessment_id']
        elif 'results' in result and 'assessment_id' in result['results']:
            assessment_id = result['results']['assessment_id']
        
        print(f"📊 Assessment ID: {assessment_id}")
        return assessment_id
    else:
        print(f"❌ Assessment failed: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return None


async def check_screenshot_urls(assessment_id):
    """Check if screenshot URLs are now stored"""
    
    import subprocess
    
    print(f"\n🔍 Checking screenshot URLs for assessment {assessment_id}...")
    
    cmd = f"""
import asyncio
from sqlalchemy import select
from src.core.database import AsyncSessionLocal
from src.models.screenshot import Screenshot

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Screenshot)
            .where(Screenshot.assessment_id == {assessment_id})
        )
        screenshots = result.scalars().all()
        
        print(f'\\nFound {{len(screenshots)}} screenshots:')
        for s in screenshots:
            print(f'\\n📷 Screenshot ID: {{s.id}}')
            print(f'  Type: {{s.screenshot_type}}')
            print(f'  Status: {{s.status}}')
            print(f'  Has URL: {{"YES" if s.image_url else "NO"}}')
            if s.image_url:
                print(f'  URL: {{s.image_url[:100]}}...')
            print(f'  Dimensions: {{s.image_width}}x{{s.image_height}}')

asyncio.run(check())
"""
    
    result = subprocess.run(
        ["docker", "exec", "leadfactory_app", "python", "-c", cmd],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    
    if "Has URL: YES" in result.stdout:
        print("\n✅ SUCCESS! Screenshot URLs are now being stored!")
        print("🎉 The fix is working - screenshots can now be displayed using the stored URLs")
    else:
        print("\n❌ URLs still not being stored. May need to check the fix.")


if __name__ == "__main__":
    assessment_id = run_test_assessment()
    
    if assessment_id:
        # Wait for processing
        time.sleep(3)
        asyncio.run(check_screenshot_urls(assessment_id))
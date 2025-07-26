#!/usr/bin/env python3
"""
Complete Security UI Verification Test
Tests the entire flow from submission to UI display
"""

import asyncio
from playwright.async_api import async_playwright
import time
import subprocess
import json
from datetime import datetime
import requests

async def test_complete_security_verification():
    # Generate unique URL with timestamp
    timestamp = int(time.time())
    test_url = f"https://www.mozilla.org?complete_test={timestamp}"
    
    print("="*80)
    print("COMPLETE SECURITY UI VERIFICATION TEST")
    print("="*80)
    print(f"Test URL: {test_url}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # First, test the API directly
    print("PHASE 1: Testing API Response")
    print("-" * 40)
    
    api_response = requests.post(
        "http://localhost:8001/api/v1/simple-assessment/execute",
        json={
            "url": test_url,
            "business_name": "Complete Test Business"
        }
    )
    
    print(f"API Status Code: {api_response.status_code}")
    
    if api_response.status_code == 200:
        data = api_response.json()
        print(f"Task ID: {data.get('task_id', 'N/A')}")
        print(f"Status: {data.get('status', 'N/A')}")
        
        results = data.get('results', {})
        
        # Check for security data
        if 'security_data' in results and results['security_data']:
            print("\n✅ SECURITY DATA FOUND IN API RESPONSE!")
            security_data = results['security_data']
            print(f"  Security Score: {security_data.get('security_score', 'N/A')}")
            print(f"  Has HTTPS: {security_data.get('has_https', 'N/A')}")
            print(f"  SSL Valid: {security_data.get('ssl_valid', 'N/A')}")
            print(f"  Vulnerabilities: {security_data.get('vulnerabilities_count', 'N/A')}")
        else:
            print("\n❌ NO SECURITY DATA IN API RESPONSE")
            print("  This is the root issue - security assessment is not returning data")
            
            # Check if security assessment failed
            if 'assessments' in data:
                print("\n  Raw assessments data:")
                print(json.dumps(data.get('assessments', {}), indent=2))
    
    # Now test the UI
    print("\n\nPHASE 2: Testing UI Display")
    print("-" * 40)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Enable console logging
        page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
        
        try:
            # Navigate to assessment UI
            print("1. Navigating to assessment UI...")
            await page.goto("http://localhost:8001/api/v1/simple-assessment")
            await page.wait_for_load_state("networkidle")
            
            # Submit assessment
            print("2. Submitting assessment...")
            await page.fill('#url', test_url)
            await page.click('#submitBtn')
            
            # Wait for completion
            print("3. Waiting for results...")
            await page.wait_for_selector('.status.completed', timeout=90000)
            await asyncio.sleep(2)
            
            # Check what's displayed
            print("4. Checking UI display...")
            
            # Get all table rows
            rows = await page.query_selector_all('#resultsBody tr')
            print(f"   Total rows in results table: {len(rows)}")
            
            # Look for security-related content
            security_found = False
            for i, row in enumerate(rows):
                text = await row.text_content()
                if 'security' in text.lower() or 'ssl' in text.lower() or 'https' in text.lower():
                    security_found = True
                    print(f"   Security row {i}: {text.strip()[:100]}...")
            
            if not security_found:
                print("   ❌ No security data found in UI")
            else:
                print("   ✅ Security data displayed in UI")
            
            # Take screenshot
            screenshot_path = f'security_complete_test_{timestamp}.png'
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"\n5. Screenshot saved: {screenshot_path}")
            
            # Check database
            print("\n\nPHASE 3: Database Verification")
            print("-" * 40)
            
            db_result = subprocess.run(
                ["docker-compose", "exec", "-T", "db", "psql", "-U", "leadfactory", "-d", "leadfactory", "-t", "-c",
                 f"""
                 SELECT 
                     COUNT(DISTINCT a.id) as assessments,
                     COUNT(DISTINCT sa.id) as security_analyses,
                     COUNT(DISTINCT sh.id) as security_headers,
                     COUNT(DISTINCT sv.id) as vulnerabilities
                 FROM assessments a
                 JOIN leads l ON a.lead_id = l.id
                 LEFT JOIN security_analysis sa ON sa.assessment_id = a.id
                 LEFT JOIN security_headers sh ON sh.security_analysis_id = sa.id
                 LEFT JOIN security_vulnerabilities sv ON sv.security_analysis_id = sa.id
                 WHERE l.url LIKE '%complete_test={timestamp}%'
                 """],
                capture_output=True,
                text=True
            )
            
            if db_result.returncode == 0 and db_result.stdout.strip():
                parts = db_result.stdout.strip().split('|')
                if len(parts) >= 4:
                    print(f"Assessments found: {parts[0].strip()}")
                    print(f"Security analyses: {parts[1].strip()}")
                    print(f"Security headers: {parts[2].strip()}")
                    print(f"Vulnerabilities: {parts[3].strip()}")
            
            # Final summary
            print("\n\n" + "="*80)
            print("TEST SUMMARY")
            print("="*80)
            
            api_has_security = 'security_data' in results and results['security_data']
            
            print(f"\nAPI Response:")
            print(f"  ✅ PageSpeed data: {'pagespeed_data' in results and results['pagespeed_data']}")
            print(f"  {'✅' if api_has_security else '❌'} Security data: {api_has_security}")
            
            print(f"\nUI Display:")
            print(f"  ✅ Results table displayed")
            print(f"  {'✅' if security_found else '❌'} Security data shown: {security_found}")
            
            print(f"\nScreenshot: {screenshot_path}")
            
            if not api_has_security:
                print("\n⚠️  ROOT ISSUE: Security assessment is not returning data in the API")
                print("    The UI cannot display what it doesn't receive from the backend")
            
            return api_has_security and security_found
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            await page.screenshot(path=f'error_{timestamp}.png')
            return False
            
        finally:
            await asyncio.sleep(10)
            await browser.close()

async def main():
    print("Starting Complete Security Verification Test...")
    print("Make sure the server is running on http://localhost:8001")
    print()
    
    success = await test_complete_security_verification()
    
    print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
#!/usr/bin/env python3
"""
Final comprehensive test for Security UI display
Tests the simple assessment UI to verify security data is shown
"""

import asyncio
from playwright.async_api import async_playwright
import time
import subprocess
import json
from datetime import datetime

async def test_security_ui_final():
    # Generate unique URL with timestamp
    timestamp = int(time.time())
    test_url = f"https://www.mozilla.org?final={timestamp}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Enable console logging
        page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
        
        try:
            print("="*70)
            print("SECURITY UI DISPLAY VERIFICATION - FINAL TEST")
            print("="*70)
            print(f"Test URL: {test_url}")
            print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()
            
            # Step 1: Navigate to simple assessment UI
            print("Step 1: Navigating to simple assessment UI...")
            await page.goto("http://localhost:8001/api/v1/simple-assessment")
            await page.wait_for_load_state("networkidle")
            print("✓ Simple assessment UI loaded")
            
            # Step 2: Enter URL and submit
            print(f"\nStep 2: Entering test URL: {test_url}")
            await page.fill('#url', test_url)
            print("✓ URL entered")
            
            # Step 3: Submit assessment
            print("\nStep 3: Submitting assessment...")
            
            # Capture API responses
            api_responses = []
            async def capture_response(response):
                if 'simple-assessment' in response.url:
                    try:
                        data = await response.json()
                        api_responses.append({
                            'url': response.url,
                            'status': response.status,
                            'data': data
                        })
                        print(f"  API Response: {response.url} - Status: {response.status}")
                    except:
                        pass
            
            page.on("response", capture_response)
            
            await page.click('#submitBtn')
            print("✓ Assessment submitted")
            
            # Step 4: Wait for completion
            print("\nStep 4: Waiting for assessment to complete...")
            
            # Wait for the status to show completed
            try:
                await page.wait_for_selector('.status.completed', timeout=90000)
                print("✓ Assessment completed")
            except:
                print("⚠️  Timeout waiting for completion status")
            
            # Wait for results table to be visible
            await page.wait_for_selector('#resultsDiv', state='visible', timeout=5000)
            await asyncio.sleep(2)  # Let results fully render
            
            # Step 5: Check for security data in the UI
            print("\nStep 5: Checking for security data in UI...")
            print("-" * 50)
            
            # Get all table rows from results
            results_rows = await page.query_selector_all('#resultsBody tr')
            print(f"Total result rows found: {len(results_rows)}")
            
            security_data_found = False
            security_info = {}
            
            for row in results_rows:
                cells = await row.query_selector_all('td')
                if len(cells) >= 4:
                    component = await cells[0].text_content()
                    score = await cells[1].text_content()
                    status = await cells[2].text_content()
                    details = await cells[3].text_content()
                    
                    print(f"\nComponent: {component}")
                    print(f"  Score: {score}")
                    print(f"  Status: {status}")
                    print(f"  Details: {details}")
                    
                    # Check if this is security component
                    if 'SECURITY' in component.upper():
                        security_data_found = True
                        security_info = {
                            'component': component,
                            'score': score,
                            'status': status,
                            'details': details
                        }
            
            # Step 6: Take screenshot
            print("\nStep 6: Taking screenshot...")
            screenshot_path = f'test_security_final_{timestamp}.png'
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"✓ Screenshot saved: {screenshot_path}")
            
            # Step 7: Verify database has security data
            print("\nStep 7: Verifying security data in database...")
            
            # Query for the assessment
            db_result = subprocess.run(
                ["docker-compose", "exec", "-T", "db", "psql", "-U", "leadfactory", "-d", "leadfactory", "-t", "-c",
                 f"""
                 SELECT 
                     a.id as assessment_id,
                     sa.id as security_analysis_id,
                     sa.security_score,
                     sa.has_https,
                     sa.ssl_valid,
                     sa.ssl_grade,
                     sa.vulnerabilities_count,
                     COUNT(sh.id) as headers_count
                 FROM assessments a
                 JOIN leads l ON a.lead_id = l.id
                 LEFT JOIN security_analysis sa ON sa.assessment_id = a.id
                 LEFT JOIN security_headers sh ON sh.security_analysis_id = sa.id
                 WHERE l.url LIKE '%final={timestamp}%'
                 GROUP BY a.id, sa.id, sa.security_score, sa.has_https, 
                          sa.ssl_valid, sa.ssl_grade, sa.vulnerabilities_count
                 ORDER BY a.created_at DESC
                 LIMIT 1
                 """],
                capture_output=True,
                text=True
            )
            
            if db_result.returncode == 0 and db_result.stdout.strip():
                print("\n✓ Security data found in database:")
                parts = db_result.stdout.strip().split('|')
                if len(parts) >= 8:
                    print(f"  Assessment ID: {parts[0].strip()}")
                    print(f"  Security Analysis ID: {parts[1].strip()}")
                    print(f"  Security Score: {parts[2].strip()}")
                    print(f"  Has HTTPS: {parts[3].strip()}")
                    print(f"  SSL Valid: {parts[4].strip()}")
                    print(f"  SSL Grade: {parts[5].strip()}")
                    print(f"  Vulnerabilities Count: {parts[6].strip()}")
                    print(f"  Security Headers Analyzed: {parts[7].strip()}")
            else:
                print("✗ No security data found in database")
            
            # Check for vulnerabilities
            if db_result.returncode == 0 and parts[1].strip() != '':
                vuln_result = subprocess.run(
                    ["docker-compose", "exec", "-T", "db", "psql", "-U", "leadfactory", "-d", "leadfactory", "-t", "-c",
                     f"""
                     SELECT vulnerability_type, severity, description
                     FROM security_vulnerabilities
                     WHERE security_analysis_id = {parts[1].strip()}
                     LIMIT 5
                     """],
                    capture_output=True,
                    text=True
                )
                
                if vuln_result.returncode == 0 and vuln_result.stdout.strip():
                    print("\n✓ Sample vulnerabilities:")
                    for line in vuln_result.stdout.strip().split('\n'):
                        if line.strip():
                            print(f"  {line.strip()}")
            
            # Summary
            print("\n" + "="*70)
            print("TEST SUMMARY")
            print("="*70)
            
            if security_data_found:
                print(f"\n✅ SECURITY DATA FOUND IN UI")
                print(f"   Component: {security_info['component']}")
                print(f"   Score: {security_info['score']}")
                print(f"   Status: {security_info['status']}")
            else:
                print("\n❌ NO SECURITY DATA FOUND IN UI")
                print("   The security component may not be displayed or the assessment failed")
            
            print(f"\n✓ Screenshot saved: {screenshot_path}")
            print(f"✓ API responses captured: {len(api_responses)}")
            
            # Debug: print API responses
            if api_responses:
                print("\nAPI Response Details:")
                for resp in api_responses:
                    print(f"  URL: {resp['url']}")
                    print(f"  Status: {resp['status']}")
                    if 'data' in resp and 'results' in resp['data']:
                        print(f"  Task ID: {resp['data'].get('task_id', 'N/A')}")
            
            return security_data_found
            
        except Exception as e:
            print(f"\n❌ Error during test: {e}")
            error_screenshot = f'test_security_error_{timestamp}.png'
            await page.screenshot(path=error_screenshot)
            print(f"Error screenshot saved: {error_screenshot}")
            
            # Save page HTML for debugging
            try:
                html = await page.content()
                debug_file = f'debug_security_final_{timestamp}.html'
                with open(debug_file, 'w') as f:
                    f.write(html)
                print(f"Debug HTML saved: {debug_file}")
            except:
                pass
                
            return False
            
        finally:
            # Keep browser open for inspection
            print("\nKeeping browser open for 15 seconds for manual inspection...")
            await asyncio.sleep(15)
            await browser.close()

async def main():
    print("Starting Final Security UI Display Test...")
    print("Make sure the server is running on http://localhost:8001")
    print()
    
    success = await test_security_ui_final()
    
    print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
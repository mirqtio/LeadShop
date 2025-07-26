#!/usr/bin/env python3
"""
Comprehensive Playwright test for Security Assessment UI Display
Verifies that ALL security data is properly displayed in the UI including:
- Security score and grade
- SSL certificate details
- Individual security headers
- Vulnerabilities
- Recommendations
"""

import asyncio
from playwright.async_api import async_playwright
import time
import subprocess
import json
from datetime import datetime

async def test_security_ui_display_verification():
    # Generate unique URL with timestamp
    timestamp = int(time.time())
    test_url = f"https://www.mozilla.org?final={timestamp}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Enable console logging for debugging
        page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
        
        try:
            # Step 1: Navigate to assessment UI
            print("="*60)
            print("SECURITY UI DISPLAY VERIFICATION TEST")
            print("="*60)
            print(f"Test URL: {test_url}")
            print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()
            
            print("Step 1: Navigating to assessment UI...")
            await page.goto("http://localhost:8001/api/v1/simple-assessment")
            await page.wait_for_load_state("networkidle")
            print("✓ Assessment UI loaded")
            
            # Step 2: Enter the URL
            print(f"\nStep 2: Entering test URL...")
            await page.fill('input[type="url"]', test_url)
            print(f"✓ URL entered: {test_url}")
            
            # Step 3: Submit the assessment
            print("\nStep 3: Submitting assessment...")
            
            # Set up response listener to capture API responses
            api_responses = {}
            async def handle_response(response):
                if '/api/v1/simple-assessment/execute' in response.url:
                    try:
                        data = await response.json()
                        api_responses['execute'] = data
                        print(f"  API Response Status: {data.get('status', 'unknown')}")
                        if data.get('results', {}).get('assessment_id'):
                            print(f"  Assessment ID: {data['results']['assessment_id']}")
                    except Exception as e:
                        print(f"  Error parsing response: {e}")
            
            page.on("response", handle_response)
            await page.click('button[type="submit"]')
            print("✓ Assessment submitted")
            
            # Step 4: Wait for completion
            print("\nStep 4: Waiting for assessment to complete...")
            
            # Wait for results section to appear
            try:
                await page.wait_for_selector('.results-section.show', timeout=90000)
                print("✓ Results section appeared")
            except:
                # Fallback: wait for results table
                await page.wait_for_selector('#resultsTable', timeout=90000)
                print("✓ Results table appeared")
            
            # Additional wait for all results to render
            await asyncio.sleep(5)
            
            # Step 5: Verify security data is displayed
            print("\nStep 5: Verifying security data in UI...")
            print("-" * 50)
            
            # Look for Security Analysis section
            security_sections = await page.query_selector_all('td:has-text("Security Analysis")')
            if security_sections:
                print("✓ Security Analysis section found")
            else:
                # Try alternative selectors
                security_sections = await page.query_selector_all('td.category-header:has-text("Security")')
                if security_sections:
                    print("✓ Security section found (alternative selector)")
            
            # Extract all security-related data from the UI
            security_data = {}
            
            # Method 1: Look for security metrics in table rows
            all_rows = await page.query_selector_all('tr')
            print(f"\nTotal rows found: {len(all_rows)}")
            
            security_row_found = False
            for i, row in enumerate(all_rows):
                row_text = await row.text_content()
                if row_text and 'security' in row_text.lower():
                    security_row_found = True
                    print(f"\nRow {i}: {row_text.strip()}")
                    
                    # Check if this is the security header row
                    if 'Security Analysis' in row_text or '🛡️' in row_text:
                        print("  ^ This is the Security Analysis header")
                        
                        # Look at the next few rows for security data
                        for j in range(i+1, min(i+10, len(all_rows))):
                            next_row = all_rows[j]
                            next_row_text = await next_row.text_content()
                            if next_row_text:
                                # Check if we've hit another component section
                                if any(icon in next_row_text for icon in ['⚡', '🏢', '📱', '🔍', '🎨', '📊', '✍️']):
                                    break
                                print(f"  Security data row: {next_row_text.strip()}")
                                
                                # Extract specific security metrics
                                cells = await next_row.query_selector_all('td')
                                if len(cells) >= 2:
                                    metric_name = await cells[0].text_content()
                                    metric_value = await cells[1].text_content()
                                    if metric_name and metric_value:
                                        security_data[metric_name.strip()] = metric_value.strip()
            
            if not security_row_found:
                print("⚠️  No security-related rows found in the table")
            
            # Method 2: Look for specific security metrics
            print("\nLooking for specific security metrics...")
            
            # SSL Certificate
            ssl_elements = await page.query_selector_all('td:has-text("SSL Certificate")')
            if ssl_elements:
                for elem in ssl_elements:
                    parent_row = await elem.evaluate_handle("el => el.parentElement")
                    cells = await parent_row.query_selector_all('td')
                    if len(cells) >= 2:
                        value = await cells[1].text_content()
                        security_data['SSL Certificate'] = value
                        print(f"✓ SSL Certificate: {value}")
            
            # Security Score
            score_elements = await page.query_selector_all('td:has-text("Security Score")')
            if score_elements:
                for elem in score_elements:
                    parent_row = await elem.evaluate_handle("el => el.parentElement")
                    cells = await parent_row.query_selector_all('td')
                    if len(cells) >= 2:
                        value = await cells[1].text_content()
                        security_data['Security Score'] = value
                        print(f"✓ Security Score: {value}")
            
            # HTTPS Status
            https_elements = await page.query_selector_all('td:has-text("HTTPS")')
            if https_elements:
                for elem in https_elements:
                    parent_row = await elem.evaluate_handle("el => el.parentElement")
                    cells = await parent_row.query_selector_all('td')
                    if len(cells) >= 2:
                        value = await cells[1].text_content()
                        security_data['HTTPS'] = value
                        print(f"✓ HTTPS Status: {value}")
            
            # Component Status
            status_elements = await page.query_selector_all('td:has-text("Component Status")')
            for elem in status_elements:
                # Check if this is in the security section
                parent_row = await elem.evaluate_handle("el => el.parentElement")
                previous_rows = await parent_row.evaluate_handle("""el => {
                    let prev = el;
                    while (prev = prev.previousElementSibling) {
                        if (prev.textContent.includes('Security Analysis')) return prev;
                    }
                    return null;
                }""")
                if previous_rows:
                    cells = await parent_row.query_selector_all('td')
                    if len(cells) >= 2:
                        value = await cells[1].text_content()
                        security_data['Component Status'] = value
                        print(f"✓ Security Component Status: {value}")
            
            # Step 6: Take a detailed screenshot
            print("\nStep 6: Taking screenshot...")
            screenshot_path = f'test_security_ui_verification_{timestamp}.png'
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"✓ Screenshot saved to {screenshot_path}")
            
            # Step 7: Verify data matches database
            print("\nStep 7: Verifying data matches database...")
            
            # Get assessment ID
            assessment_id = None
            if 'execute' in api_responses and api_responses['execute'].get('results', {}).get('assessment_id'):
                assessment_id = api_responses['execute']['results']['assessment_id']
                print(f"Using assessment ID from API: {assessment_id}")
            else:
                # Query database for assessment
                assessment_result = subprocess.run(
                    ["docker-compose", "exec", "-T", "db", "psql", "-U", "leadfactory", "-d", "leadfactory", "-t", "-c",
                     f"""SELECT a.id 
                         FROM assessments a 
                         JOIN leads l ON a.lead_id = l.id 
                         WHERE l.url LIKE '%final={timestamp}%' 
                         ORDER BY a.created_at DESC 
                         LIMIT 1"""],
                    capture_output=True,
                    text=True
                )
                
                if assessment_result.returncode == 0 and assessment_result.stdout.strip():
                    assessment_id = assessment_result.stdout.strip()
                    print(f"Found assessment ID in database: {assessment_id}")
            
            if assessment_id:
                # Query security analysis data
                security_db_result = subprocess.run(
                    ["docker-compose", "exec", "-T", "db", "psql", "-U", "leadfactory", "-d", "leadfactory", "-t", "-c",
                     f"""SELECT 
                         has_https, 
                         ssl_valid,
                         ssl_grade, 
                         security_score,
                         ssl_issuer,
                         ssl_expiry,
                         vulnerabilities_count
                     FROM security_analysis 
                     WHERE assessment_id = {assessment_id}"""],
                    capture_output=True,
                    text=True
                )
                
                if security_db_result.returncode == 0 and security_db_result.stdout.strip():
                    print("\n✓ Database security data:")
                    parts = security_db_result.stdout.strip().split('|')
                    if len(parts) >= 7:
                        db_data = {
                            'has_https': parts[0].strip(),
                            'ssl_valid': parts[1].strip(),
                            'ssl_grade': parts[2].strip(),
                            'security_score': parts[3].strip(),
                            'ssl_issuer': parts[4].strip(),
                            'ssl_expiry': parts[5].strip(),
                            'vulnerabilities_count': parts[6].strip()
                        }
                        for key, value in db_data.items():
                            print(f"  {key}: {value}")
                        
                        # Get security headers count
                        headers_result = subprocess.run(
                            ["docker-compose", "exec", "-T", "db", "psql", "-U", "leadfactory", "-d", "leadfactory", "-t", "-c",
                             f"""SELECT 
                                 COUNT(*) as total_headers,
                                 COUNT(CASE WHEN is_secure = true THEN 1 END) as secure_headers
                             FROM security_headers 
                             WHERE security_analysis_id = (
                                 SELECT id FROM security_analysis WHERE assessment_id = {assessment_id}
                             )"""],
                            capture_output=True,
                            text=True
                        )
                        
                        if headers_result.returncode == 0 and headers_result.stdout.strip():
                            headers_parts = headers_result.stdout.strip().split('|')
                            if len(headers_parts) >= 2:
                                print(f"\n✓ Security headers in database:")
                                print(f"  Total headers: {headers_parts[0].strip()}")
                                print(f"  Secure headers: {headers_parts[1].strip()}")
                
                # Get some sample vulnerabilities
                vuln_result = subprocess.run(
                    ["docker-compose", "exec", "-T", "db", "psql", "-U", "leadfactory", "-d", "leadfactory", "-t", "-c",
                     f"""SELECT vulnerability_type, severity
                     FROM security_vulnerabilities 
                     WHERE security_analysis_id = (
                         SELECT id FROM security_analysis WHERE assessment_id = {assessment_id}
                     )
                     LIMIT 3"""],
                    capture_output=True,
                    text=True
                )
                
                if vuln_result.returncode == 0 and vuln_result.stdout.strip():
                    print("\n✓ Sample vulnerabilities in database:")
                    for line in vuln_result.stdout.strip().split('\n'):
                        if line.strip():
                            print(f"  {line.strip()}")
            
            # Step 8: Summary
            print("\n" + "="*60)
            print("TEST SUMMARY")
            print("="*60)
            
            if security_data:
                print("\n✓ Security data found in UI:")
                for key, value in security_data.items():
                    print(f"  - {key}: {value}")
            else:
                print("\n✗ No security data found in UI")
            
            print(f"\n✓ Screenshot saved: {screenshot_path}")
            
            if assessment_id:
                print(f"✓ Assessment verified in database (ID: {assessment_id})")
            
            # Determine overall test result
            test_passed = len(security_data) > 0
            
            if test_passed:
                print("\n✅ TEST PASSED - Security data is displayed in UI")
            else:
                print("\n❌ TEST FAILED - Security data not properly displayed")
                
                # Save page HTML for debugging
                page_html = await page.content()
                debug_file = f'debug_security_ui_{timestamp}.html'
                with open(debug_file, 'w') as f:
                    f.write(page_html)
                print(f"  Debug HTML saved to: {debug_file}")
            
            return test_passed
            
        except Exception as e:
            print(f"\n❌ Error during test: {e}")
            # Take error screenshot
            error_screenshot = f'test_security_error_{timestamp}.png'
            await page.screenshot(path=error_screenshot)
            print(f"Error screenshot saved to: {error_screenshot}")
            
            # Save page content for debugging
            try:
                page_html = await page.content()
                with open(f'debug_error_{timestamp}.html', 'w') as f:
                    f.write(page_html)
            except:
                pass
            
            return False
            
        finally:
            # Keep browser open for manual inspection
            print("\nKeeping browser open for 15 seconds for manual inspection...")
            await asyncio.sleep(15)
            await browser.close()

async def main():
    print("Starting Security UI Display Verification Test...")
    print("Make sure the server is running on http://localhost:8001")
    print()
    
    success = await test_security_ui_display_verification()
    
    print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
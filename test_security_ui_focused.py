#!/usr/bin/env python3
"""
Focused test for verifying Security data display in the UI
Tests that security assessment results are properly shown
"""

import asyncio
from playwright.async_api import async_playwright
import time
import subprocess
from datetime import datetime

async def test_security_display():
    # Generate unique URL
    timestamp = int(time.time())
    test_url = f"https://www.mozilla.org?security_test={timestamp}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            print("="*60)
            print("SECURITY UI DISPLAY TEST")
            print("="*60)
            print(f"Test URL: {test_url}")
            print()
            
            # Navigate to assessment UI
            print("1. Navigating to assessment UI...")
            await page.goto("http://localhost:8001/api/v1/simple-assessment")
            await page.wait_for_load_state("networkidle")
            
            # Enter URL and submit
            print("2. Submitting assessment...")
            await page.fill('input[type="url"]', test_url)
            await page.click('button[type="submit"]')
            
            # Wait for completion
            print("3. Waiting for results...")
            await page.wait_for_selector('.results-section.show', timeout=90000)
            await asyncio.sleep(3)  # Let all results render
            
            # Look for security data
            print("\n4. Checking for security data in UI:")
            print("-" * 40)
            
            # Find all table rows
            rows = await page.query_selector_all('tr')
            
            security_found = False
            security_rows = []
            
            # Scan through rows looking for security content
            for i, row in enumerate(rows):
                text = await row.text_content()
                if text and ('security' in text.lower() or 'ssl' in text.lower() or 'https' in text.lower()):
                    security_found = True
                    security_rows.append((i, text.strip()))
            
            # Display findings
            if security_found:
                print("✓ Security data found in UI:")
                for row_num, text in security_rows:
                    print(f"  Row {row_num}: {text[:100]}...")
            else:
                print("✗ No security data found in UI")
            
            # Take screenshot
            screenshot_path = f'security_display_test_{timestamp}.png'
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"\n5. Screenshot saved: {screenshot_path}")
            
            # Get assessment ID from database
            print("\n6. Checking database for security data...")
            result = subprocess.run(
                ["docker-compose", "exec", "-T", "db", "psql", "-U", "leadfactory", "-d", "leadfactory", "-t", "-c",
                 f"""SELECT a.id, sa.security_score, sa.has_https, sa.ssl_grade
                     FROM assessments a 
                     JOIN leads l ON a.lead_id = l.id
                     LEFT JOIN security_analysis sa ON sa.assessment_id = a.id
                     WHERE l.url LIKE '%security_test={timestamp}%'
                     ORDER BY a.created_at DESC LIMIT 1"""],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split('|')
                if len(parts) >= 4:
                    print(f"  Assessment ID: {parts[0].strip()}")
                    print(f"  Security Score: {parts[1].strip()}")
                    print(f"  Has HTTPS: {parts[2].strip()}")
                    print(f"  SSL Grade: {parts[3].strip()}")
            else:
                print("  No security data found in database")
            
            # Summary
            print("\n" + "="*60)
            if security_found:
                print("✅ TEST PASSED - Security data is displayed in UI")
            else:
                print("❌ TEST FAILED - Security data not found in UI")
                
                # Save page HTML for debugging
                html = await page.content()
                with open(f'debug_security_{timestamp}.html', 'w') as f:
                    f.write(html)
                print(f"Debug HTML saved to: debug_security_{timestamp}.html")
            
            return security_found
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            await page.screenshot(path=f'error_{timestamp}.png')
            return False
            
        finally:
            await asyncio.sleep(10)  # Keep browser open
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(test_security_display())
    exit(0 if success else 1)
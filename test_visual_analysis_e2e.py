"""
End-to-End Test for Visual Analysis Feature
Tests the complete flow including screenshot capture, visual analysis, and database storage
"""

import asyncio
import os
from playwright.async_api import async_playwright, expect
import pytest
from datetime import datetime
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test configuration
TEST_URL = "http://localhost:8001"  # Docker exposes on port 8001
TEST_WEBSITE_URL = f"https://www.spotify.com?visual={int(datetime.now().timestamp())}"
TEST_BUSINESS_NAME = "Spotify Test"

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "leadshop_db",
    "user": "leadshop_user",
    "password": "leadshop_pass"
}


def check_database_for_visual_analysis(url: str):
    """Check database for visual analysis results"""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # First, find the assessment
        cur.execute("""
            SELECT id, created_at, status 
            FROM assessments 
            WHERE business_website = %s 
            ORDER BY created_at DESC 
            LIMIT 1
        """, (url,))
        assessment = cur.fetchone()
        
        if not assessment:
            print("No assessment found in database")
            return None
            
        print(f"Found assessment ID: {assessment['id']}, Status: {assessment['status']}")
        
        # Check for screenshots
        cur.execute("""
            SELECT id, screenshot_type, s3_key, width, height, created_at 
            FROM screenshots 
            WHERE assessment_id = %s
        """, (assessment['id'],))
        screenshots = cur.fetchall()
        
        print(f"Found {len(screenshots)} screenshots:")
        for screenshot in screenshots:
            print(f"  - Type: {screenshot['screenshot_type']}, Size: {screenshot['width']}x{screenshot['height']}")
            print(f"    S3 Key: {screenshot['s3_key']}")
        
        # Check for visual analysis
        cur.execute("""
            SELECT 
                id, screenshot_id, status, 
                design_score, usability_score, accessibility_score,
                professionalism_score, trust_score,
                ai_summary, created_at
            FROM visual_analyses 
            WHERE assessment_id = %s
        """, (assessment['id'],))
        visual_analyses = cur.fetchall()
        
        print(f"\nFound {len(visual_analyses)} visual analyses:")
        for analysis in visual_analyses:
            print(f"  - ID: {analysis['id']}, Status: {analysis['status']}")
            print(f"    Scores: Design={analysis['design_score']}, Usability={analysis['usability_score']}")
            print(f"    Accessibility={analysis['accessibility_score']}, Professional={analysis['professionalism_score']}")
            print(f"    Trust={analysis['trust_score']}")
            if analysis['ai_summary']:
                print(f"    AI Summary: {analysis['ai_summary'][:100]}...")
        
        # Check for UX issues
        if visual_analyses:
            cur.execute("""
                SELECT 
                    COUNT(*) as count,
                    severity,
                    issue_type
                FROM ux_issues 
                WHERE visual_analysis_id = ANY(%s)
                GROUP BY severity, issue_type
                ORDER BY severity
            """, ([va['id'] for va in visual_analyses],))
            ux_issues = cur.fetchall()
            
            if ux_issues:
                print("\nUX Issues Summary:")
                for issue in ux_issues:
                    print(f"  - {issue['severity'].upper()}: {issue['count']} {issue['issue_type']} issues")
        
        return {
            'assessment': assessment,
            'screenshots': screenshots,
            'visual_analyses': visual_analyses
        }
        
    except Exception as e:
        print(f"Database error: {e}")
        return None
    finally:
        if conn:
            conn.close()


async def test_visual_analysis_e2e():
    """Test the complete visual analysis flow with real API calls"""
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # 1. Navigate to simple assessment UI
            print(f"1. Navigating to {TEST_URL}/api/v1/simple-assessment")
            await page.goto(f"{TEST_URL}/api/v1/simple-assessment", wait_until="networkidle")
            print("✓ Navigated to simple assessment UI")
            
            # 2. Fill in the assessment form with unique URL
            url_input = page.locator("#url")
            await url_input.fill(TEST_WEBSITE_URL)
            print(f"✓ Filled URL: {TEST_WEBSITE_URL}")
            
            # 3. Submit the assessment
            submit_btn = page.locator("#submitBtn")
            await submit_btn.click()
            print("✓ Clicked submit button")
            
            # 4. Wait for assessment to start
            status_div = page.locator("#status")
            await expect(status_div).to_be_visible(timeout=5000)
            
            # 5. Monitor assessment progress with focus on visual analysis
            print("\nMonitoring assessment progress (focusing on visual analysis)...")
            max_wait_time = 240  # 4 minutes max - visual analysis takes time
            start_time = time.time()
            assessment_completed = False
            visual_analysis_found = False
            
            while time.time() - start_time < max_wait_time:
                # Check current status
                status_text = await status_div.text_content()
                print(f"Status: {status_text}")
                
                # Check if results are displayed
                results_div = page.locator("#results")
                is_visible = await results_div.is_visible()
                
                if is_visible:
                    # Check if we have results in the table
                    results_rows = page.locator("#resultsBody tr")
                    row_count = await results_rows.count()
                    
                    if row_count > 0:
                        # Look specifically for visual analysis results
                        metric_cells = await page.locator("#resultsBody tr td:first-child").all_text_contents()
                        
                        # Check for visual analysis metrics
                        visual_metrics = [
                            "visual_analysis",
                            "design_score",
                            "usability_score",
                            "accessibility_score",
                            "professionalism_score",
                            "trust_score",
                            "ai_summary",
                            "screenshot"
                        ]
                        
                        for metric in metric_cells:
                            metric_lower = metric.lower()
                            if any(vm in metric_lower for vm in visual_metrics):
                                visual_analysis_found = True
                                break
                        
                        if visual_analysis_found:
                            print(f"✓ Visual analysis completed! Found {row_count} result rows")
                            assessment_completed = True
                            break
                        else:
                            print(f"Assessment has {row_count} rows but no visual analysis yet...")
                
                # Check for errors
                if "error" in status_text.lower() or "failed" in status_text.lower():
                    print(f"✗ Assessment failed: {status_text}")
                    break
                
                # Wait before next check
                await page.wait_for_timeout(3000)
            
            if not assessment_completed:
                print(f"✗ Assessment did not complete within {max_wait_time} seconds")
                await page.screenshot(path="visual_analysis_timeout.png")
            else:
                # 6. Verify visual analysis results are displayed
                print("\nVerifying visual analysis results...")
                
                # Get all metrics
                metric_cells = await page.locator("#resultsBody tr td:first-child").all_text_contents()
                value_cells = await page.locator("#resultsBody tr td:last-child").all_text_contents()
                
                # Create a dictionary of metrics
                metrics_dict = {}
                for i in range(len(metric_cells)):
                    if i < len(value_cells):
                        metrics_dict[metric_cells[i].lower()] = value_cells[i]
                
                # Check for specific visual analysis metrics
                visual_scores = {
                    'design_score': None,
                    'usability_score': None,
                    'accessibility_score': None,
                    'professionalism_score': None,
                    'trust_score': None
                }
                
                print("\nVisual Analysis Scores Found:")
                for score_name in visual_scores:
                    for metric_name, value in metrics_dict.items():
                        if score_name in metric_name:
                            visual_scores[score_name] = value
                            print(f"  ✓ {score_name}: {value}")
                            break
                
                # Count how many scores we found
                found_scores = sum(1 for v in visual_scores.values() if v is not None)
                print(f"\nFound {found_scores}/5 visual analysis scores")
                
                # Look for AI summary
                ai_summary_found = False
                for metric_name in metrics_dict:
                    if 'ai_summary' in metric_name or 'summary' in metric_name:
                        ai_summary_found = True
                        print(f"✓ AI Summary found: {metrics_dict[metric_name][:100]}...")
                        break
                
                # Look for screenshot information
                screenshot_found = False
                for metric_name in metrics_dict:
                    if 'screenshot' in metric_name:
                        screenshot_found = True
                        print(f"✓ Screenshot information found")
                        break
                
                # 7. Take screenshot of visual analysis results
                await page.screenshot(path="visual_analysis_results.png", full_page=True)
                print("\n✓ Screenshot saved as visual_analysis_results.png")
                
                # 8. Check database for visual analysis data
                print("\n" + "="*50)
                print("Checking database for visual analysis data...")
                db_results = check_database_for_visual_analysis(TEST_WEBSITE_URL)
                
                if db_results:
                    print("\n✓ Database verification complete!")
                    
                    # Validate we have all expected data
                    if db_results['screenshots']:
                        print(f"✓ Screenshots stored: {len(db_results['screenshots'])}")
                    else:
                        print("✗ No screenshots found in database")
                    
                    if db_results['visual_analyses']:
                        print(f"✓ Visual analyses stored: {len(db_results['visual_analyses'])}")
                        
                        # Check if all scores are present
                        for analysis in db_results['visual_analyses']:
                            if all(analysis.get(score) is not None for score in 
                                   ['design_score', 'usability_score', 'accessibility_score', 
                                    'professionalism_score', 'trust_score']):
                                print("✓ All visual analysis scores present in database")
                            else:
                                print("✗ Some visual analysis scores missing in database")
                    else:
                        print("✗ No visual analyses found in database")
                else:
                    print("✗ Could not verify database data")
                
                print("\n" + "="*50)
                
                # Summary
                print("\n✅ Visual Analysis E2E Test Summary:")
                print(f"  - Assessment completed: {'Yes' if assessment_completed else 'No'}")
                print(f"  - Visual analysis found in UI: {'Yes' if visual_analysis_found else 'No'}")
                print(f"  - Visual scores displayed: {found_scores}/5")
                print(f"  - AI summary present: {'Yes' if ai_summary_found else 'No'}")
                print(f"  - Screenshot info present: {'Yes' if screenshot_found else 'No'}")
                print(f"  - Database verification: {'Success' if db_results else 'Failed'}")
            
        except Exception as e:
            # Take screenshot on failure
            await page.screenshot(path="visual_analysis_error.png")
            print(f"\n❌ Test failed: {str(e)}")
            print("Screenshot saved as visual_analysis_error.png")
            raise
            
        finally:
            await browser.close()


if __name__ == "__main__":
    # Run the test
    print("Running Visual Analysis End-to-End Test...")
    print(f"Test URL: {TEST_WEBSITE_URL}")
    print("="*60 + "\n")
    
    asyncio.run(test_visual_analysis_e2e())
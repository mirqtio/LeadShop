#!/usr/bin/env python3
"""
Test decomposed scores display by fetching results from database
"""

import asyncio
import requests
from playwright.async_api import async_playwright
import time

async def test_decomposed_scores():
    # First, let's check what assessments we have in the database
    # We'll use assessment ID 102 (Airbnb) which has some data
    
    assessment_id = 102
    
    # Fetch the results from the API
    response = requests.get(f"http://localhost:8001/api/v1/simple-assessment/results/{assessment_id}")
    
    if response.status_code == 200:
        print(f"✅ Successfully fetched results for assessment {assessment_id}")
        data = response.json()
        
        # Check if we have decomposed scores
        if 'decomposed_scores' in data and data['decomposed_scores']:
            print(f"✅ Found decomposed scores in response")
            scores = data['decomposed_scores']
            
            # Count non-null metrics
            non_null = {k: v for k, v in scores.items() if v is not None}
            print(f"📊 Decomposed metrics found: {len(non_null)} / 53")
            
            # Print available metrics
            print("\n🔍 Available decomposed metrics:")
            for metric, value in non_null.items():
                print(f"  - {metric}: {value}")
        else:
            print("❌ No decomposed scores in response")
    else:
        print(f"❌ Failed to fetch results: {response.status_code}")
    
    # Now let's display this in the UI
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Navigate to the assessment UI
        await page.goto("http://localhost:8001/api/v1/simple-assessment")
        print("\n📱 Opened assessment UI")
        
        # Inject JavaScript to manually display results
        await page.evaluate(f"""
            // Hide the form and show results
            document.getElementById('assessmentForm').style.display = 'none';
            document.getElementById('status').style.display = 'block';
            document.getElementById('status').className = 'status completed';
            document.getElementById('status').textContent = 'Displaying results from assessment {assessment_id}';
            document.getElementById('results').style.display = 'block';
            
            // Fetch and display results
            fetch('/api/v1/simple-assessment/results/{assessment_id}')
                .then(response => response.json())
                .then(data => {{
                    console.log('Fetched data:', data);
                    
                    // Display regular results
                    if (data.pagespeed_data) displayPageSpeedResults(data.pagespeed_data);
                    if (data.security_data) displaySecurityResults(data.security_data);
                    if (data.gbp_data) displayGBPResults(data.gbp_data, data.gbp_summary);
                    if (data.screenshot_data) displayScreenshotResults(data.screenshot_data);
                    if (data.visual_analysis_data) displayVisualAnalysisResults(data.visual_analysis_data);
                    if (data.semrush_data) displaySEMrushResults(data.semrush_data);
                    
                    // Display decomposed scores
                    if (data.decomposed_scores) {{
                        displayDecomposedScores(data.decomposed_scores);
                    }}
                }});
        """)
        
        # Wait for results to load
        await page.wait_for_timeout(3000)
        
        # Scroll to the decomposed scores section
        await page.evaluate("""
            // Find the decomposed scores section
            const rows = document.querySelectorAll('tr');
            for (const row of rows) {
                if (row.textContent.includes('DECOMPOSED SCORES FROM DATABASE')) {
                    row.scrollIntoView();
                    break;
                }
            }
        """)
        
        # Take screenshots
        timestamp = int(time.time())
        
        # Full page screenshot
        await page.screenshot(path=f"decomposed_scores_full_{timestamp}.png", full_page=True)
        print(f"\n📸 Saved full page screenshot: decomposed_scores_full_{timestamp}.png")
        
        # Focused screenshot of decomposed scores section
        decomposed_section = await page.query_selector('text=DECOMPOSED SCORES FROM DATABASE')
        if decomposed_section:
            # Get the table containing decomposed scores
            table = await decomposed_section.evaluate_handle("el => el.closest('table')")
            await table.screenshot(path=f"decomposed_scores_section_{timestamp}.png")
            print(f"📸 Saved decomposed scores section: decomposed_scores_section_{timestamp}.png")
        
        # Keep browser open for manual inspection
        print("\n👀 Browser will stay open for 30 seconds for manual inspection...")
        await page.wait_for_timeout(30000)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_decomposed_scores())
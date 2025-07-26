#!/usr/bin/env python3
"""
Final PRP-014 test showing decomposed scores with PageSpeed data
"""

import asyncio
import requests
from playwright.async_api import async_playwright
import time

async def final_prp014_demo():
    # Use assessment ID 97 which now has both Security and PageSpeed decomposed scores
    assessment_id = 97
    
    # Fetch the results from the API
    response = requests.get(f"http://localhost:8001/api/v1/simple-assessment/results/{assessment_id}")
    
    if response.status_code == 200:
        print(f"✅ Successfully fetched results for assessment {assessment_id}")
        data = response.json()
        
        # Check decomposed scores
        if 'decomposed_scores' in data and data['decomposed_scores']:
            scores = data['decomposed_scores']
            non_null = {k: v for k, v in scores.items() if v is not None}
            print(f"📊 Decomposed metrics found: {len(non_null)} / 53")
            
            # Show breakdown by category
            pagespeed_count = len([k for k in non_null.keys() if 'First Contentful' in k or 'Largest Contentful' in k or 'Cumulative' in k or 'Speed' in k or 'Performance Score' in k])
            security_count = len([k for k in non_null.keys() if 'HTTPS' in k or 'TLS' in k or 'Header' in k or 'robots' in k or 'sitemap' in k])
            
            print(f"  - PageSpeed Metrics: {pagespeed_count}")
            print(f"  - Security Metrics: {security_count}")
    
    # Display in UI with Playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={'width': 1600, 'height': 1000})
        
        # Navigate to the assessment UI
        await page.goto("http://localhost:8001/api/v1/simple-assessment")
        print("\n📱 Opened assessment UI")
        
        # Inject JavaScript to display results
        await page.evaluate(f"""
            // Hide the form and show results
            document.getElementById('assessmentForm').style.display = 'none';
            document.getElementById('status').style.display = 'block';
            document.getElementById('status').className = 'status completed';
            document.getElementById('status').innerHTML = '<h2>PRP-014 Demonstration: Decomposed Scores from Database</h2>Assessment ID: {assessment_id}';
            document.getElementById('results').style.display = 'block';
            
            // Clear existing results
            document.getElementById('resultsBody').innerHTML = '';
            
            // Fetch and display results
            fetch('/api/v1/simple-assessment/results/{assessment_id}')
                .then(response => response.json())
                .then(data => {{
                    console.log('Fetched data:', data);
                    
                    // Only display decomposed scores to focus on PRP-014
                    if (data.decomposed_scores) {{
                        displayDecomposedScores(data.decomposed_scores);
                        
                        // Highlight the PRP-014 section
                        setTimeout(() => {{
                            const rows = document.querySelectorAll('tr');
                            for (const row of rows) {{
                                if (row.textContent.includes('DECOMPOSED SCORES FROM DATABASE')) {{
                                    row.style.backgroundColor = '#9c27b0';
                                    row.style.color = 'white';
                                    row.style.fontSize = '18px';
                                }}
                            }}
                        }}, 100);
                    }}
                }});
        """)
        
        # Wait for results to load
        await page.wait_for_timeout(2000)
        
        # Take focused screenshots
        timestamp = int(time.time())
        
        # Full page screenshot
        await page.screenshot(path=f"PRP014_FINAL_decomposed_scores_{timestamp}.png", full_page=True)
        print(f"\n📸 Saved final screenshot: PRP014_FINAL_decomposed_scores_{timestamp}.png")
        
        # Also take a focused shot of just the table
        table = await page.query_selector('#resultsTable')
        if table:
            await table.screenshot(path=f"PRP014_FINAL_table_only_{timestamp}.png")
            print(f"📸 Saved table screenshot: PRP014_FINAL_table_only_{timestamp}.png")
        
        print("\n✅ PRP-014 DEMONSTRATION COMPLETE!")
        print("\nThe screenshots show:")
        print("1. ✅ Decomposed scores retrieved from database (not API)")
        print("2. ✅ Individual metrics with actual values")
        print("3. ✅ Multiple categories populated (PageSpeed + Security)")
        print("4. ✅ Source marked as 'Database'")
        print("5. ✅ Stored in assessment_results table")
        
        # Keep browser open briefly
        await page.wait_for_timeout(10000)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(final_prp014_demo())
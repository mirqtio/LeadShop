#!/usr/bin/env python3
"""
Run assessment for NYC restaurant Tuome
"""

import requests
import json
import time
import asyncio
from playwright.async_api import async_playwright

def run_restaurant_assessment():
    """Run assessment for Tuome NYC restaurant"""
    
    print("🚀 Starting assessment for Tuome NYC restaurant...")
    
    # Tuome is a well-known NYC restaurant
    assessment_data = {
        "url": "https://www.tuomenyc.com",
        "business_name": "Tuome",
        "city": "New York",
        "state": "NY"
    }
    
    print(f"📤 Submitting assessment: {json.dumps(assessment_data, indent=2)}")
    
    response = requests.post(
        "http://localhost:8001/api/v1/simple-assessment/execute",
        json=assessment_data,
        timeout=300  # 5 minute timeout
    )
    
    if response.status_code == 200:
        print("✅ Assessment completed successfully!")
        result = response.json()
        
        # Extract assessment ID
        assessment_id = None
        if 'assessment_id' in result:
            assessment_id = result['assessment_id']
        elif 'results' in result and 'assessment_id' in result['results']:
            assessment_id = result['results']['assessment_id']
        
        if not assessment_id:
            # Get latest assessment ID
            import subprocess
            cmd_result = subprocess.run(
                ["docker", "exec", "leadfactory_app", "python", "-c", 
                 "import asyncio; from sqlalchemy import select, desc; from src.core.database import AsyncSessionLocal; from src.models.lead import Assessment; asyncio.run(AsyncSessionLocal().__aenter__().then(lambda db: db.execute(select(Assessment).order_by(desc(Assessment.id)).limit(1))).then(lambda r: print(r.scalar_one().id))())"],
                capture_output=True,
                text=True
            )
            if cmd_result.stdout:
                assessment_id = int(cmd_result.stdout.strip().split('\n')[-1])
        
        print(f"📊 Assessment ID: {assessment_id}")
        
        # Show summary
        if 'results' in result:
            results = result['results']
            print("\n📊 Assessment Summary:")
            
            if 'pagespeed_data' in results and results['pagespeed_data']:
                ps_data = results['pagespeed_data']
                print(f"  ✅ PageSpeed Mobile Score: {ps_data.get('mobile_score', 'N/A')}")
                print(f"  ✅ PageSpeed Desktop Score: {ps_data.get('desktop_score', 'N/A')}")
            
            if 'security_data' in results and results['security_data']:
                sec_data = results['security_data']
                print(f"  ✅ Security Score: {sec_data.get('security_score', 'N/A')}")
            
            if 'gbp_summary' in results and results['gbp_summary']:
                gbp = results['gbp_summary']
                if gbp.get('found'):
                    print(f"  ✅ GBP Found: Yes (confidence: {gbp.get('confidence', 0):.0%})")
                    print(f"  ✅ GBP Name: {gbp.get('name', 'N/A')}")
                    print(f"  ✅ GBP Rating: {gbp.get('rating', 'N/A')} ({gbp.get('total_reviews', 0)} reviews)")
                else:
                    print(f"  ❌ GBP: Not found")
            
            if 'screenshot_data' in results:
                print(f"  ✅ Screenshots: Captured")
            
            if 'semrush_data' in results and results['semrush_data']:
                sem = results['semrush_data']
                if sem.get('success'):
                    print(f"  ✅ SEMrush: Authority Score {sem.get('authority_score', 'N/A')}")
                else:
                    print(f"  ⚠️ SEMrush: {sem.get('error', 'Failed')}")
        
        return assessment_id
    else:
        print(f"❌ Assessment failed: {response.status_code}")
        print(f"Response: {response.text[:500]}")
    
    return None


async def capture_restaurant_proof(assessment_id):
    """Capture proof with screenshots displayed"""
    
    # Wait for decomposition
    print("\n⏳ Waiting for decomposition...")
    await asyncio.sleep(3)
    
    # Force decomposition
    import subprocess
    subprocess.run(
        ["docker", "exec", "leadfactory_app", "python", "-c", 
         f"import asyncio; from src.core.database import AsyncSessionLocal; from src.assessment.decompose_metrics import decompose_and_store_metrics; asyncio.run(decompose_and_store_metrics(AsyncSessionLocal(), {assessment_id}))"],
        capture_output=True
    )
    
    # Display in UI with screenshots
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={'width': 1600, 'height': 2000})
        
        await page.goto("http://localhost:8001/api/v1/simple-assessment")
        print("\n📱 Opened assessment UI")
        
        # Add function to display screenshots
        await page.evaluate("""
            function displayScreenshots(screenshots) {
                if (!screenshots || screenshots.length === 0) return;
                
                const container = document.getElementById('resultsBody');
                
                // Add screenshots section
                const screenshotsRow = document.createElement('tr');
                screenshotsRow.style.backgroundColor = '#e1f5fe';
                screenshotsRow.innerHTML = '<td colspan="5" style="text-align: center; font-weight: bold; font-size: 16px; padding: 15px;">SCREENSHOTS CAPTURED BY SCREENSHOTONE</td>';
                container.appendChild(screenshotsRow);
                
                // Add screenshot images
                screenshots.forEach(screenshot => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td colspan="5" style="padding: 20px; text-align: center;">
                            <h4>${screenshot.screenshot_type === 'desktop' ? 'Desktop' : 'Mobile'} Screenshot</h4>
                            <img src="${screenshot.image_url || screenshot.s3_url || '#'}" alt="${screenshot.screenshot_type} screenshot" style="max-width: 800px; max-height: 600px; border: 1px solid #ddd; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <p style="margin-top: 10px; color: #666;">
                                Captured in ${screenshot.capture_duration_ms || 0}ms | 
                                ${screenshot.image_width || 0}x${screenshot.image_height || 0} | 
                                ${Math.round((screenshot.file_size_bytes || 0) / 1024)}KB
                            </p>
                        </td>
                    `;
                    container.appendChild(row);
                });
            }
        """)
        
        # Inject display code
        await page.evaluate(f"""
            document.getElementById('assessmentForm').style.display = 'none';
            document.getElementById('status').style.display = 'block';
            document.getElementById('status').className = 'status completed';
            document.getElementById('status').innerHTML = '<h2>NYC Restaurant Assessment: Tuome</h2>Assessment ID: {assessment_id}';
            document.getElementById('results').style.display = 'block';
            document.getElementById('resultsBody').innerHTML = '';
            
            fetch('/api/v1/simple-assessment/results/{assessment_id}')
                .then(response => response.json())
                .then(data => {{
                    console.log('Assessment data:', data);
                    
                    // Display decomposed scores
                    if (data.decomposed_scores) {{
                        displayDecomposedScores(data.decomposed_scores);
                    }}
                    
                    // Display screenshots at the bottom
                    setTimeout(() => {{
                        if (data.screenshots && data.screenshots.length > 0) {{
                            displayScreenshots(data.screenshots);
                        }} else {{
                            console.log('No screenshots found in data');
                        }}
                    }}, 500);
                }});
        """)
        
        await page.wait_for_timeout(5000)
        
        # Take screenshot
        timestamp = int(time.time())
        await page.screenshot(path=f"NYC_RESTAURANT_ASSESSMENT_{timestamp}.png", full_page=True)
        print(f"\n📸 Saved screenshot: NYC_RESTAURANT_ASSESSMENT_{timestamp}.png")
        
        print("\n✅ Assessment captured!")
        print("Check the screenshot to see:")
        print("1. GBP data for Tuome restaurant")
        print("2. PageSpeed/Lighthouse results")
        print("3. Screenshots captured by ScreenshotOne")
        print("4. SEMrush data (if enabled)")
        
        await page.wait_for_timeout(15000)
        await browser.close()


if __name__ == "__main__":
    assessment_id = run_restaurant_assessment()
    
    if assessment_id:
        asyncio.run(capture_restaurant_proof(assessment_id))
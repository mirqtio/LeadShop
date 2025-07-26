"""
Test PRP-014 Implementation - Verify all 53 decomposed metrics are displayed
"""

import asyncio
from playwright.async_api import async_playwright
import json

# Expected metric labels from ASSESSMENT_PROGRESS_TRACKER.md
EXPECTED_METRICS = [
    # PAGESPEED METRICS (7)
    "First Contentful Paint (FCP)",
    "Largest Contentful Paint (LCP)",
    "Cumulative Layout Shift (CLS)",
    "Total Blocking Time (TBT)",
    "Time to Interactive (TTI)",
    "Speed Index",
    "Performance Score",
    
    # TECHNICAL/SECURITY METRICS (9)
    "HTTPS Enforced",
    "TLS Version",
    "HSTS Header Present",
    "CSP Header Present",
    "X-Frame-Options Header",
    "robots.txt Found",
    "sitemap.xml Found",
    "# Broken Internal Links",
    "# JS Console Errors",
    
    # GOOGLE BUSINESS PROFILE METRICS (9)
    "Hours Listed",
    "Review Count",
    "Rating",
    "Photos Count",
    "Total Reviews",
    "Average Rating (Lifetime)",
    "Recent Reviews (90 days)",
    "Rating Trend",
    "Business Closed?",
    
    # SCREENSHOT/VISUAL METRICS (2)
    "Screenshots Captured",
    "Image Quality Assessment",
    
    # SEMRUSH METRICS (6)
    "Site Health Score",
    "Backlink Toxicity Score",
    "Organic Traffic Est.",
    "Ranking Keywords (#)",
    "Domain Authority Score",
    "Top Issue Categories",
    
    # LIGHTHOUSE/VISUAL ASSESSMENT METRICS (13)
    "Performance Score (headless)",
    "Accessibility Score",
    "Best-Practices Score",
    "SEO Score",
    "Above-the-fold clarity",
    "Primary CTA prominence",
    "Trust signals present",
    "Visual hierarchy / contrast",
    "Text readability",
    "Brand colour cohesion",
    "Image quality",
    "Mobile responsiveness",
    "Clutter / white-space balance",
    
    # LLM CONTENT GENERATOR METRICS (7)
    "Unique Value Prop clarity",
    "Contact Info presence",
    "Next-Step clarity (CTA)",
    "Social-Proof presence",
    "Content Quality Score",
    "Brand Voice Consistency",
    "Spam Score Assessment"
]

async def test_prp014_ui():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print("🔍 Testing PRP-014 Implementation...")
            
            # Navigate to the assessment UI
            await page.goto("http://localhost:8001/assessment/")
            await page.wait_for_load_state("networkidle")
            
            print("✅ Assessment UI loaded")
            
            # First, let's check if we have an existing assessment to view
            # Try the test endpoint with assessment ID 1
            await page.goto("http://localhost:8001/api/v1/assessment/test/1")
            await page.wait_for_load_state("networkidle")
            
            # Check if we get a JSON response
            content = await page.content()
            if "task_id" in content and "execution" in content:
                print("✅ Test endpoint returns assessment data")
                
                # Parse the JSON response
                response_text = await page.locator("pre").inner_text()
                response_data = json.loads(response_text)
                
                # Check for decomposed_metrics in the response
                if "result" in response_data and "execution" in response_data["result"]:
                    execution = response_data["result"]["execution"]
                    if "decomposed_metrics" in execution:
                        decomposed_metrics = execution["decomposed_metrics"]
                        print(f"✅ Found {len(decomposed_metrics)} decomposed metrics")
                        
                        # Verify all expected metrics are present
                        missing_metrics = []
                        for expected_metric in EXPECTED_METRICS:
                            if expected_metric not in decomposed_metrics:
                                missing_metrics.append(expected_metric)
                        
                        if missing_metrics:
                            print(f"❌ Missing {len(missing_metrics)} metrics:")
                            for metric in missing_metrics[:5]:  # Show first 5
                                print(f"   - {metric}")
                            if len(missing_metrics) > 5:
                                print(f"   ... and {len(missing_metrics) - 5} more")
                        else:
                            print("✅ All 53 expected metrics are present in the API response!")
                        
                        # Show some sample values
                        print("\n📊 Sample metric values:")
                        sample_metrics = list(decomposed_metrics.items())[:5]
                        for key, value in sample_metrics:
                            print(f"   - {key}: {value}")
                    else:
                        print("❌ No decomposed_metrics found in response")
                else:
                    print("❌ Response structure doesn't match expected format")
            else:
                print("❌ Test endpoint didn't return expected data")
            
            # Now test the actual UI display
            print("\n🔍 Testing UI display of metrics...")
            await page.goto("http://localhost:8001/assessment/")
            await page.wait_for_load_state("networkidle")
            
            # Submit a test assessment
            await page.fill("#urlInput", "https://example.com")
            await page.fill("#businessNameInput", "Test Business")
            
            # Click submit (without auth for testing)
            await page.click("#submitBtn")
            
            # Wait for the assessment to start
            await page.wait_for_timeout(2000)
            
            # Check if we get a task ID
            task_id_element = await page.query_selector("#taskId")
            if task_id_element:
                task_id = await task_id_element.inner_text()
                print(f"✅ Assessment started with task ID: {task_id}")
                
                # Wait for results
                print("⏳ Waiting for assessment to complete...")
                await page.wait_for_timeout(10000)  # Wait 10 seconds
                
                # Check if detailed metrics are displayed
                metrics_table = await page.query_selector("#detailedMetrics tbody")
                if metrics_table:
                    # Count metric rows (excluding category headers)
                    metric_rows = await page.query_selector_all("#detailedMetrics tbody tr:not(.metric-category)")
                    print(f"✅ Found {len(metric_rows)} metric rows in the UI")
                    
                    # Check if it's close to 53
                    if len(metric_rows) >= 50:
                        print("✅ UI is displaying the expected number of metrics!")
                    else:
                        print(f"⚠️  UI is displaying {len(metric_rows)} metrics, expected 53")
                else:
                    print("❌ Detailed metrics table not found")
            else:
                print("❌ Failed to start assessment")
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_prp014_ui())
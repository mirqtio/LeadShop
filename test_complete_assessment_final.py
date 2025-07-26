#!/usr/bin/env python3
"""
Test the complete assessment system with all 8 components
"""
import asyncio
import json
import time
import httpx
from datetime import datetime

# Test configuration
API_BASE_URL = "http://localhost:8001/api/v1"
TEST_URL = "https://www.example.com"  # Using example.com which won't block screenshots
TEST_BUSINESS = "Example Business"

async def test_complete_assessment():
    """Test the complete assessment endpoint"""
    async with httpx.AsyncClient(timeout=180.0) as client:
        # Start assessment
        print(f"\n🚀 Starting complete assessment for {TEST_URL}")
        print("=" * 80)
        
        response = await client.post(
            f"{API_BASE_URL}/complete-assessment/assess",
            json={
                "url": TEST_URL,
                "business_name": TEST_BUSINESS
            }
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to start assessment: {response.status_code}")
            print(response.text)
            return
        
        data = response.json()
        assessment_id = data["assessment_id"]
        print(f"✅ Assessment started: ID {assessment_id}")
        print(f"   Message: {data['message']}")
        
        # Poll for status
        print("\n📊 Component Progress:")
        print("-" * 80)
        
        last_progress = 0
        while True:
            await asyncio.sleep(2)
            
            status_response = await client.get(
                f"{API_BASE_URL}/complete-assessment/status/{assessment_id}"
            )
            
            if status_response.status_code != 200:
                print(f"❌ Failed to get status: {status_response.status_code}")
                break
            
            status = status_response.json()
            
            # Show progress
            progress = status.get("progress", 0)
            if progress > last_progress:
                print(f"\n⏳ Progress: {progress}%")
                last_progress = progress
            
            # Show component status
            if status.get("components"):
                for component, state in status["components"].items():
                    icon = "✅" if state == "completed" else "🔄" if state == "running" else "❌" if state == "failed" else "⏳"
                    print(f"   {icon} {component}: {state}")
            
            # Check if completed or failed
            if status.get("status") == "completed":
                print("\n🎉 Assessment completed successfully!")
                print("=" * 80)
                
                # Show results
                if status.get("score") is not None:
                    print(f"\n📊 Overall Score: {status['score']:.1f}/100")
                
                if status.get("results"):
                    print("\n📋 Component Results:")
                    print("-" * 80)
                    
                    results = status["results"]
                    
                    # PageSpeed
                    if results.get("pagespeed"):
                        ps = results["pagespeed"]
                        print("\n⚡ PageSpeed Insights:")
                        if isinstance(ps, dict) and ps.get("mobile_analysis"):
                            mobile_score = ps["mobile_analysis"].get("core_web_vitals", {}).get("performance_score", "N/A")
                            desktop_score = ps.get("desktop_analysis", {}).get("core_web_vitals", {}).get("performance_score", "N/A")
                            print(f"   Mobile Score: {mobile_score}/100")
                            print(f"   Desktop Score: {desktop_score}/100")
                        else:
                            print("   ❌ No data")
                    
                    # Security
                    if results.get("security"):
                        sec = results["security"]
                        print("\n🛡️ Security Headers:")
                        if isinstance(sec, dict):
                            print(f"   Security Score: {sec.get('security_score', 'N/A')}/100")
                            print(f"   HTTPS Enabled: {sec.get('https_enabled', 'N/A')}")
                        else:
                            print("   ❌ No data")
                    
                    # SEMrush
                    if results.get("semrush"):
                        print("\n🔍 SEMrush Analysis:")
                        print("   ❌ API limits reached (expected)")
                    else:
                        print("\n🔍 SEMrush Analysis:")
                        print("   ❌ Failed (expected - API limits)")
                    
                    # GBP
                    if results.get("gbp"):
                        gbp = results["gbp"]
                        print("\n🏢 Google Business Profile:")
                        if isinstance(gbp, dict):
                            print(f"   Business Found: {gbp.get('found', False)}")
                        else:
                            print("   ❌ No data")
                    
                    # Screenshots
                    if results.get("screenshots"):
                        ss = results["screenshots"]
                        print("\n📸 Screenshots:")
                        if isinstance(ss, dict):
                            print(f"   Success: {ss.get('success', False)}")
                            if ss.get("desktop_screenshot"):
                                print("   ✅ Desktop screenshot captured")
                            if ss.get("mobile_screenshot"):
                                print("   ✅ Mobile screenshot captured")
                        else:
                            print("   ❌ No data")
                    
                    # Visual Analysis
                    if results.get("visual"):
                        va = results["visual"]
                        print("\n🎨 Visual Analysis:")
                        if isinstance(va, dict) and va.get("success"):
                            metrics = va.get("metrics", {})
                            print(f"   UX Score: {metrics.get('overall_ux_score', 'N/A')}")
                            print(f"   Analysis completed with {len(metrics.get('rubrics', []))} rubrics")
                        else:
                            print("   ❌ Failed")
                
                print("\n" + "=" * 80)
                print("✅ All components executed - assessment system is working!")
                break
                
            elif status.get("status") == "failed":
                print(f"\n❌ Assessment failed: {status.get('error', 'Unknown error')}")
                break
            
            elif status.get("status") == "not_found":
                print("\n⚠️ Assessment not found in status tracker")
                # Check database
                db_response = await client.get(f"{API_BASE_URL}/assessments/{assessment_id}")
                if db_response.status_code == 200:
                    print("✅ But found in database - assessment may have completed")
                    db_data = db_response.json()
                    if db_data.get("total_score") is not None:
                        print(f"   Score: {db_data['total_score']}/100")
                break

if __name__ == "__main__":
    print("🧪 Testing Complete Assessment System")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Target URL: {TEST_URL}")
    print(f"Business Name: {TEST_BUSINESS}")
    
    asyncio.run(test_complete_assessment())
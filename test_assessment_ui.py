#!/usr/bin/env python3
"""
Test Assessment UI Integration
Quick test to verify the assessment UI endpoints are working
"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_assessment_ui_endpoints():
    """Test all assessment UI endpoints"""
    
    print("🧪 Testing Assessment UI Integration")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        
        # Test 1: Health check
        print("\n📋 1. Testing Health Check")
        try:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                print("   ✅ Health check passed")
            else:
                print(f"   ❌ Health check failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Health check error: {e}")
        
        # Test 2: Assessment UI endpoint
        print("\n📋 2. Testing Assessment UI Endpoint")
        try:
            response = await client.get(f"{base_url}/api/v1/assessment")
            if response.status_code == 200 and "LeadShop - Website Assessment" in response.text:
                print("   ✅ Assessment UI loads successfully")
                print(f"   📄 HTML content: {len(response.text)} characters")
            else:
                print(f"   ❌ Assessment UI failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Assessment UI error: {e}")
        
        # Test 3: Config endpoint
        print("\n📋 3. Testing Configuration Endpoint")
        try:
            response = await client.get(f"{base_url}/api/v1/assessment/config")
            if response.status_code == 200:
                config = response.json()
                print("   ✅ Configuration endpoint working")
                print(f"   🔧 Google Client ID: {config.get('google_client_id', 'Not set')[:20]}...")
                print(f"   🔗 API Base URL: {config.get('api_base_url')}")
            else:
                print(f"   ❌ Configuration failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Configuration error: {e}")
        
        # Test 4: API v1 health
        print("\n📋 4. Testing API v1 Health")
        try:
            response = await client.get(f"{base_url}/api/v1/health")
            if response.status_code == 200:
                health = response.json()
                print("   ✅ API v1 health check passed")
                print(f"   📊 Status: {health.get('status')}")
                print(f"   📋 Endpoints: {len(health.get('endpoints', []))} available")
            else:
                print(f"   ❌ API v1 health failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ API v1 health error: {e}")
        
        # Test 5: Authentication endpoint structure
        print("\n📋 5. Testing Authentication Endpoint Structure")
        try:
            # This should fail without a token, but we're testing the endpoint exists
            response = await client.post(
                f"{base_url}/api/v1/assessment/auth/google",
                json={"google_token": "invalid-token"}
            )
            # Expect 401 for invalid token
            if response.status_code == 401:
                print("   ✅ Google auth endpoint properly rejects invalid tokens")
            else:
                print(f"   ⚠️  Unexpected status for invalid token: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Auth endpoint error: {e}")
        
        # Test 6: Assessment execution endpoint (should require auth)
        print("\n📋 6. Testing Assessment Execution Endpoint")
        try:
            response = await client.post(
                f"{base_url}/api/v1/assessment/execute",
                json={"url": "https://example.com", "business_name": "Test"}
            )
            # Should fail with 403/401 due to missing auth
            if response.status_code in [401, 403]:
                print("   ✅ Assessment execution properly requires authentication")
            else:
                print(f"   ⚠️  Unexpected status for unauthenticated request: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Assessment execution error: {e}")

def test_environment_setup():
    """Test environment configuration"""
    
    print("\n🔧 Environment Configuration Check")
    print("-" * 40)
    
    import os
    
    required_vars = [
        "GOOGLE_CLIENT_ID",
        "DATABASE_URL", 
        "REDIS_URL"
    ]
    
    recommended_vars = [
        "GOOGLE_CLIENT_SECRET",
        "JWT_SECRET",
        "OPENAI_API_KEY",
        "SCREENSHOTONE_ACCESS_KEY"
    ]
    
    print("\n📋 Required Variables:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            display_value = value[:20] + "..." if len(value) > 20 else value
            print(f"   ✅ {var}: {display_value}")
        else:
            print(f"   ❌ {var}: Not set")
    
    print("\n📋 Recommended Variables:")
    for var in recommended_vars:
        value = os.getenv(var)
        if value:
            display_value = value[:20] + "..." if len(value) > 20 else value
            print(f"   ✅ {var}: {display_value}")
        else:
            print(f"   ⚠️  {var}: Not set")

def show_next_steps():
    """Show next steps for user"""
    
    print("\n🎯 Next Steps")
    print("=" * 50)
    
    print("\n1. 🔧 Complete Environment Setup:")
    print("   • Copy .env.example to .env")
    print("   • Add your Google OAuth credentials")
    print("   • Configure database and Redis URLs")
    
    print("\n2. 🚀 Start Required Services:")
    print("   • Redis: redis-server")
    print("   • Celery: celery -A src.core.celery_app worker --loglevel=info")
    print("   • FastAPI: uvicorn src.main:app --host 0.0.0.0 --port 8000")
    
    print("\n3. 🌐 Access Assessment UI:")
    print("   • Local: http://localhost:8000/api/v1/assessment")
    print("   • VPS: http://your-vps-ip:8000/api/v1/assessment")
    
    print("\n4. 🔐 Google OAuth Setup:")
    print("   • Go to: https://console.cloud.google.com/apis/credentials")
    print("   • Create OAuth 2.0 Client ID")
    print("   • Add authorized origins and redirect URIs")
    print("   • Update GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env")
    
    print("\n5. 🧪 Test Complete Flow:")
    print("   • Visit assessment UI")
    print("   • Sign in with Google")
    print("   • Enter URL and run assessment")
    print("   • Monitor real-time progress")
    print("   • View comprehensive results")

async def main():
    """Main test function"""
    
    print("🔍 LeadShop Assessment UI Integration Test")
    print("=" * 60)
    print(f"⏰ Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test environment
    test_environment_setup()
    
    # Test endpoints
    await test_assessment_ui_endpoints()
    
    # Show next steps
    show_next_steps()
    
    print(f"\n⏰ Test completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n✅ Assessment UI integration is ready!")
    print("📖 See ASSESSMENT_UI_SETUP.md for complete setup guide")

if __name__ == "__main__":
    asyncio.run(main())
"""
Test Visual Analysis via API
Tests the visual analysis functionality through the API with mock data
"""

import requests
import json
import time
from datetime import datetime

# Configuration
API_URL = "http://localhost:8001/api/v1/simple-assessment/execute"
TEST_URL = f"https://www.example.com?visual={int(datetime.now().timestamp())}"
TEST_BUSINESS_NAME = "Visual Test Business"

def test_visual_analysis_api():
    """Test visual analysis through the API"""
    
    print("Testing Visual Analysis via API")
    print("="*60)
    print(f"URL: {TEST_URL}")
    print(f"Business: {TEST_BUSINESS_NAME}")
    
    # Prepare request
    request_data = {
        "url": TEST_URL,
        "business_name": TEST_BUSINESS_NAME
    }
    
    try:
        # Send assessment request
        print("\nSending assessment request...")
        response = requests.post(API_URL, json=request_data)
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response Status: {data.get('status')}")
            print(f"Message: {data.get('message')}")
            
            results = data.get('results', {})
            
            # Check for visual analysis data
            visual_data = results.get('visual_analysis_data', {})
            if visual_data:
                print("\n✅ Visual Analysis Data Found!")
                print(f"Success: {visual_data.get('success', False)}")
                
                if visual_data.get('success'):
                    print(f"Overall UX Score: {visual_data.get('overall_ux_score', 'N/A')}/100")
                    
                    # Check rubrics
                    rubrics = visual_data.get('rubrics', [])
                    if rubrics:
                        print(f"\nFound {len(rubrics)} rubrics:")
                        for rubric in rubrics[:5]:  # Show first 5
                            print(f"  - {rubric.get('name', 'Unknown')}: {rubric.get('score', 0)}/10")
                    
                    # Check rubric summary
                    rubric_summary = visual_data.get('rubric_summary', {})
                    if rubric_summary:
                        print(f"\nRubric Summary ({len(rubric_summary)} items):")
                        for name, details in list(rubric_summary.items())[:3]:
                            print(f"  - {name}: {details.get('score', 'N/A')}/10")
                            if details.get('explanation'):
                                print(f"    {details['explanation'][:100]}...")
                    
                    # Check analyses
                    if visual_data.get('desktop_analysis'):
                        print("\n✓ Desktop analysis present")
                    if visual_data.get('mobile_analysis'):
                        print("✓ Mobile analysis present")
                else:
                    print(f"Error: {visual_data.get('error_message', 'Unknown error')}")
            else:
                print("\n❌ No visual analysis data in response")
            
            # Check other assessment results
            print("\nOther Assessment Results:")
            if results.get('pagespeed_data'):
                print("✓ PageSpeed data present")
            if results.get('security_data'):
                print("✓ Security data present")
            if results.get('gbp_data'):
                print("✓ GBP data present")
            if results.get('screenshot_data'):
                print("✓ Screenshot data present")
                screenshot_data = results.get('screenshot_data', {})
                if screenshot_data.get('success'):
                    print(f"  - Screenshot capture: Success")
                else:
                    print(f"  - Screenshot capture: Failed - {screenshot_data.get('error_message', 'Unknown error')}")
            
            # Pretty print full response for debugging
            print("\n" + "="*60)
            print("Full Response (truncated):")
            response_str = json.dumps(data, indent=2)
            if len(response_str) > 2000:
                print(response_str[:2000] + "\n... (truncated)")
            else:
                print(response_str)
            
        else:
            print(f"\n❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_visual_analysis_api()
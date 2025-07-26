"""
Mock Visual Analysis Test
Tests visual analysis with mock screenshot URLs since ScreenshotOne API is not configured
"""

import asyncio
import os
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test configuration
TEST_URL = f"https://www.example.com?visual={int(datetime.now().timestamp())}"
TEST_BUSINESS_NAME = "Example Test"

# Mock screenshot URLs (using placeholder images)
MOCK_DESKTOP_SCREENSHOT = "https://via.placeholder.com/1920x1080/4A90E2/FFFFFF?text=Desktop+Screenshot"
MOCK_MOBILE_SCREENSHOT = "https://via.placeholder.com/390x844/E94B3C/FFFFFF?text=Mobile+Screenshot"

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "leadshop_db",
    "user": "leadshop_user",
    "password": "leadshop_pass"
}


async def test_visual_analysis_directly():
    """Test visual analysis module directly with mock screenshots"""
    
    print("Testing Visual Analysis Module Directly...")
    print("="*60)
    
    try:
        # Import the visual analysis module
        from src.assessments.visual_analysis import assess_visual_analysis
        
        # Create a mock lead_id and assessment_id
        lead_id = 999999  # Mock ID
        assessment_id = 999999  # Mock ID
        
        print(f"\nTesting with:")
        print(f"  URL: {TEST_URL}")
        print(f"  Desktop Screenshot: {MOCK_DESKTOP_SCREENSHOT}")
        print(f"  Mobile Screenshot: {MOCK_MOBILE_SCREENSHOT}")
        print(f"  Lead ID: {lead_id}")
        print(f"  Assessment ID: {assessment_id}")
        
        # Run visual analysis
        print("\nRunning visual analysis...")
        result = await assess_visual_analysis(
            url=TEST_URL,
            desktop_screenshot_url=MOCK_DESKTOP_SCREENSHOT,
            mobile_screenshot_url=MOCK_MOBILE_SCREENSHOT,
            lead_id=lead_id,
            assessment_id=assessment_id,
            screenshot_id=None  # No screenshot ID since we're using mock URLs
        )
        
        print("\n✅ Visual Analysis Completed!")
        print(f"Success: {result.success}")
        
        if result.success and result.metrics:
            print(f"\nOverall UX Score: {result.metrics.overall_ux_score}/100")
            
            print("\nRubric Scores:")
            for rubric in result.metrics.rubrics:
                print(f"  - {rubric.name}: {rubric.score}/10")
                print(f"    {rubric.explanation}")
                if rubric.recommendations:
                    print(f"    Recommendations: {', '.join(rubric.recommendations[:2])}")
            
            if result.metrics.desktop_analysis:
                print(f"\nDesktop Analysis:")
                print(f"  Layout Score: {result.metrics.desktop_analysis.layout_score}/10")
                print(f"  Typography Score: {result.metrics.desktop_analysis.typography_score}/10")
                print(f"  Color Scheme Score: {result.metrics.desktop_analysis.color_scheme_score}/10")
            
            if result.metrics.mobile_analysis:
                print(f"\nMobile Analysis:")
                print(f"  Touch Target Score: {result.metrics.mobile_analysis.touch_target_score}/10")
                print(f"  Content Adaptation Score: {result.metrics.mobile_analysis.content_adaptation_score}/10")
                print(f"  Performance Score: {result.metrics.mobile_analysis.performance_score}/10")
            
            if result.metrics.key_findings:
                print(f"\nKey Findings: {result.metrics.key_findings}")
            
            if result.metrics.competitive_positioning:
                print(f"\nCompetitive Positioning: {result.metrics.competitive_positioning}")
            
        else:
            print(f"Error: {result.error_message}")
        
        print(f"\nTotal Duration: {result.total_duration_ms}ms")
        
        # Check if it was saved to database
        if assessment_id != 999999:  # Only check if using real assessment_id
            print("\nChecking database...")
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT id, design_score, usability_score, accessibility_score,
                       professionalism_score, trust_score, status
                FROM visual_analyses
                WHERE assessment_id = %s
            """, (assessment_id,))
            
            db_result = cur.fetchone()
            if db_result:
                print("✅ Visual analysis saved to database!")
                print(f"  Database ID: {db_result['id']}")
                print(f"  Status: {db_result['status']}")
            else:
                print("❌ Visual analysis not found in database")
            
            conn.close()
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_visual_analysis_with_orchestrator():
    """Test visual analysis through the orchestrator with mock data"""
    
    print("\n\nTesting Visual Analysis through Orchestrator...")
    print("="*60)
    
    try:
        # Import the orchestrator
        from src.assessments.orchestrator_with_security import run_assessments
        
        # Monkey patch the screenshot capture to return mock data
        from src.assessments import screenshot_capture
        
        # Save original function
        original_capture = screenshot_capture.capture_website_screenshots
        
        # Create mock function
        async def mock_capture_website_screenshots(url: str, lead_id: int, assessment_id=None):
            from src.assessments.screenshot_capture import ScreenshotResults, ScreenshotMetadata
            
            print(f"Mock screenshot capture called for {url}")
            
            desktop_meta = ScreenshotMetadata(
                viewport="desktop",
                width=1920,
                height=1080,
                file_size_bytes=100000,
                format="webp",
                quality=85,
                capture_timestamp=datetime.now().isoformat(),
                s3_url=None,
                signed_url=MOCK_DESKTOP_SCREENSHOT,
                capture_duration_ms=1000
            )
            
            mobile_meta = ScreenshotMetadata(
                viewport="mobile",
                width=390,
                height=844,
                file_size_bytes=50000,
                format="webp",
                quality=85,
                capture_timestamp=datetime.now().isoformat(),
                s3_url=None,
                signed_url=MOCK_MOBILE_SCREENSHOT,
                capture_duration_ms=800
            )
            
            return ScreenshotResults(
                url=url,
                success=True,
                desktop_screenshot=desktop_meta,
                mobile_screenshot=mobile_meta,
                error_message=None,
                total_duration_ms=1800,
                cost_records=[]
            )
        
        # Replace with mock
        screenshot_capture.capture_website_screenshots = mock_capture_website_screenshots
        
        try:
            print(f"\nRunning assessments for: {TEST_URL}")
            results = await run_assessments(
                url=TEST_URL,
                business_name=TEST_BUSINESS_NAME,
                assessment_id=None  # Let it create a new one
            )
            
            print(f"\nAssessment Status: {results['status']}")
            
            # Check visual analysis results
            if 'visual_analysis' in results['assessments']:
                va_result = results['assessments']['visual_analysis']
                print(f"\nVisual Analysis Status: {va_result['status']}")
                
                if va_result['status'] == 'success' and va_result.get('data'):
                    data = va_result['data']
                    if hasattr(data, 'metrics') and data.metrics:
                        print(f"✅ Visual Analysis Score: {data.metrics.overall_ux_score}/100")
                    else:
                        print("Visual analysis data structure:", data)
            
            # Check formatted visual analysis data
            if 'visual_analysis_data' in results:
                va_data = results['visual_analysis_data']
                print(f"\nFormatted Visual Analysis Data:")
                print(f"  Success: {va_data.get('success', False)}")
                if va_data.get('success'):
                    print(f"  Overall UX Score: {va_data.get('overall_ux_score', 'N/A')}")
                    if 'rubric_summary' in va_data:
                        print("  Rubric Summary:")
                        for name, details in va_data['rubric_summary'].items():
                            print(f"    - {name}: {details.get('score', 'N/A')}/10")
                else:
                    print(f"  Error: {va_data.get('error_message', 'Unknown error')}")
            
        finally:
            # Restore original function
            screenshot_capture.capture_website_screenshots = original_capture
        
    except Exception as e:
        print(f"\n❌ Orchestrator test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run both tests
    print("Visual Analysis Mock Testing")
    print("="*80)
    
    # Test 1: Direct visual analysis
    asyncio.run(test_visual_analysis_directly())
    
    # Test 2: Through orchestrator
    asyncio.run(test_visual_analysis_with_orchestrator())
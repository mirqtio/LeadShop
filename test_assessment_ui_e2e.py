"""
End-to-end test for comprehensive assessment UI
Tests the complete flow from authentication to viewing all decomposed scores
"""

import asyncio
import os
from playwright.async_api import async_playwright, Page, expect
import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test configuration
TEST_URL = os.getenv("TEST_URL", "http://localhost:8000")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
TEST_WEBSITE_URL = "https://example.com"
TEST_BUSINESS_NAME = "Example Corporation"


async def test_assessment_ui_complete_flow():
    """Test the complete assessment UI flow from login to results display"""
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate to assessment UI
            print(f"1. Navigating to {TEST_URL}/assessment")
            await page.goto(f"{TEST_URL}/assessment")
            await page.wait_for_load_state("networkidle")
            
            # Verify page loaded
            await expect(page).to_have_title("LeadShop - Comprehensive Website Assessment")
            print("✓ Page loaded successfully")
            
            # Check for authentication section
            auth_section = page.locator("#authSection")
            await expect(auth_section).to_be_visible()
            print("✓ Authentication section visible")
            
            # Check for Google Sign-In button
            google_signin = page.locator(".g_id_signin")
            await expect(google_signin).to_be_visible()
            print("✓ Google Sign-In button present")
            
            # Mock authentication (since we can't automate Google OAuth)
            # In a real test, you would need to handle the OAuth flow
            # For now, we'll inject mock authentication data
            await page.evaluate("""
                // Mock successful authentication
                window.currentUser = {
                    email: 'test@example.com',
                    name: 'Test User',
                    picture: 'https://via.placeholder.com/32'
                };
                window.accessToken = 'mock-access-token';
                
                // Store in localStorage
                localStorage.setItem('access_token', 'mock-access-token');
                localStorage.setItem('user_data', JSON.stringify(window.currentUser));
                
                // Show assessment form
                document.getElementById('authSection').style.display = 'none';
                document.getElementById('assessmentFormSection').style.display = 'block';
                
                // Update user info
                document.getElementById('userPicture').src = window.currentUser.picture;
                document.getElementById('userName').textContent = window.currentUser.name;
                document.getElementById('userEmail').textContent = window.currentUser.email;
            """)
            print("✓ Mock authentication completed")
            
            # Verify assessment form is visible
            assessment_form = page.locator("#assessmentFormSection")
            await expect(assessment_form).to_be_visible()
            print("✓ Assessment form visible")
            
            # Fill in the form
            await page.fill("#websiteUrl", TEST_WEBSITE_URL)
            await page.fill("#businessName", TEST_BUSINESS_NAME)
            print(f"✓ Filled form with URL: {TEST_WEBSITE_URL}")
            
            # Mock the API responses for testing
            async def handle_execute_route(route):
                await route.fulfill(json={
                    "task_id": "test-task-123",
                    "status": "started",
                    "message": "Assessment started"
                })
            
            await page.route("**/api/v1/assessment/execute", handle_execute_route)
            
            # Mock the status polling responses
            call_count = 0
            
            async def handle_status_route(route):
                nonlocal call_count
                call_count += 1
                
                if call_count <= 2:
                    # First few calls - in progress
                    await route.fulfill(json={
                        "task_id": "test-task-123",
                        "status": "in_progress",
                        "message": "Assessment running",
                        "progress": {
                            "message": "Running PageSpeed analysis...",
                            "components": {
                                "pagespeed": {"status": "running"},
                                "security": {"status": "pending"},
                                "tech_scraper": {"status": "pending"},
                                "gbp": {"status": "pending"},
                                "screenshots": {"status": "pending"},
                                "semrush": {"status": "pending"},
                                "visual_analysis": {"status": "pending"},
                                "score_calculation": {"status": "pending"}
                            }
                        }
                    })
                else:
                    # Final call - completed with full results
                    await route.fulfill(json={
                        "task_id": "test-task-123",
                        "status": "completed",
                        "message": "Assessment completed",
                        "result": {
                            "execution": {
                                "overall_score": 78,
                                "success_rate": 0.875,
                                "successful_components": 7,
                                "total_components": 8,
                                "total_duration_ms": 12450,
                                "total_cost_cents": 35,
                                "pagespeed_result": {
                                    "status": {"value": "success"},
                                    "duration_ms": 3200,
                                    "data": {
                                        "desktop_score": 92,
                                        "mobile_score": 68,
                                        "desktop_metrics": {
                                            "first_contentful_paint_ms": 1200,
                                            "largest_contentful_paint_ms": 2100,
                                            "cumulative_layout_shift": 0.05,
                                            "total_blocking_time_ms": 150,
                                            "time_to_interactive_ms": 3200
                                        }
                                    }
                                },
                                "security_result": {
                                    "status": {"value": "success"},
                                    "duration_ms": 450,
                                    "data": {
                                        "ssl_valid": True,
                                        "https_redirect": True,
                                        "security_headers_score": 85,
                                        "headers_present": {
                                            "hsts": True,
                                            "csp": False,
                                            "x_frame_options": True
                                        }
                                    }
                                },
                                "gbp_result": {
                                    "status": {"value": "success"},
                                    "duration_ms": 1800,
                                    "data": {
                                        "place_found": True,
                                        "rating": 4.2,
                                        "user_ratings_total": 156,
                                        "business_status": "OPERATIONAL"
                                    }
                                },
                                "semrush_result": {
                                    "status": {"value": "failed"},
                                    "error": "API key not configured",
                                    "duration_ms": 100
                                },
                                "visual_analysis_result": {
                                    "status": {"value": "success"},
                                    "duration_ms": 2500,
                                    "data": {
                                        "scores": [7, 8, 6, 7, 8, 5, 7, 8, 6],
                                        "overall_score": 6.9
                                    }
                                }
                            }
                        }
                    })
            
            await page.route("**/api/v1/assessment/status/test-task-123", handle_status_route)
            
            # Click analyze button
            analyze_btn = page.locator("#analyzeBtn")
            await analyze_btn.click()
            print("✓ Clicked analyze button")
            
            # Wait for progress section to appear
            progress_section = page.locator("#progressSection")
            await expect(progress_section).to_be_visible(timeout=5000)
            print("✓ Progress section visible")
            
            # Check component status cards
            component_cards = page.locator(".component-card")
            await expect(component_cards).to_have_count(8, timeout=5000)
            print("✓ All 8 component status cards displayed")
            
            # Wait for results to appear
            results_container = page.locator("#resultsContainer")
            await expect(results_container).to_have_class("results-container show", timeout=10000)
            print("✓ Results container visible")
            
            # Verify overall scores section
            overall_scores = page.locator("#overallScores .score-card")
            await expect(overall_scores).to_have_count(5)
            print("✓ Overall scores displayed")
            
            # Check specific score values
            score_values = await page.locator("#overallScores .score-value").all_text_contents()
            assert "78" in score_values[0]  # Overall score
            assert "87%" in score_values[1]  # Success rate
            assert "7/8" in score_values[2]  # Components
            print("✓ Score values correct")
            
            # Verify metrics table has data
            metrics_rows = page.locator("#metricsTableBody tr")
            await expect(metrics_rows.first()).to_be_visible()
            
            # Check for PageSpeed metrics
            desktop_score_row = page.locator("td:has-text('Desktop Score')").locator("..")
            await expect(desktop_score_row).to_be_visible()
            desktop_score_value = await desktop_score_row.locator(".metric-value").text_content()
            assert "92" in desktop_score_value
            print("✓ PageSpeed Desktop Score: 92")
            
            # Check for Mobile Score
            mobile_score_row = page.locator("td:has-text('Mobile Score')").locator("..")
            await expect(mobile_score_row).to_be_visible()
            mobile_score_value = await mobile_score_row.locator(".metric-value").text_content()
            assert "68" in mobile_score_value
            print("✓ PageSpeed Mobile Score: 68")
            
            # Check for Security metrics
            ssl_row = page.locator("td:has-text('SSL Valid')").locator("..")
            await expect(ssl_row).to_be_visible()
            ssl_value = await ssl_row.locator(".metric-value").text_content()
            assert "Yes" in ssl_value
            print("✓ SSL Valid: Yes")
            
            # Check for Google Business Profile
            gbp_row = page.locator("td:has-text('Average Rating')").locator("..")
            await expect(gbp_row).to_be_visible()
            gbp_value = await gbp_row.locator(".metric-value").text_content()
            assert "4.2" in gbp_value
            print("✓ GBP Rating: 4.2")
            
            # Check visual scores section
            visual_section = page.locator("#visualScoresSection")
            await expect(visual_section).to_be_visible()
            visual_scores = page.locator(".visual-score-item")
            await expect(visual_scores).to_have_count(9)
            print("✓ All 9 visual score rubrics displayed")
            
            # Check for error section (should have SEMrush error)
            errors_section = page.locator("#errorsSection")
            await expect(errors_section).to_be_visible()
            error_containers = page.locator(".error-container")
            await expect(error_containers).to_have_count(1)
            print("✓ Error section shows failed component")
            
            # Test sign out functionality
            sign_out_btn = page.locator("#signOutBtn")
            await sign_out_btn.click()
            
            # Verify we're back at auth section
            await expect(auth_section).to_be_visible()
            await expect(assessment_form).not_to_be_visible()
            print("✓ Sign out successful")
            
            print("\n✅ All UI tests passed successfully!")
            
        except Exception as e:
            # Take screenshot on failure
            await page.screenshot(path="test_failure.png")
            print(f"\n❌ Test failed: {str(e)}")
            print("Screenshot saved as test_failure.png")
            raise
            
        finally:
            await browser.close()


# Alternative test using pytest-playwright
@pytest.mark.asyncio
async def test_assessment_ui_components(page: Page):
    """Test individual UI components and interactions"""
    
    # Navigate to assessment UI
    await page.goto(f"{TEST_URL}/assessment")
    
    # Test responsive design
    # Desktop view
    await page.set_viewport_size({"width": 1400, "height": 900})
    await page.wait_for_load_state("networkidle")
    
    # Check header is visible
    header = page.locator(".header")
    await expect(header).to_be_visible()
    
    # Mobile view
    await page.set_viewport_size({"width": 375, "height": 667})
    await page.wait_for_timeout(500)
    
    # Check mobile responsive classes applied
    container = page.locator(".container")
    await expect(container).to_be_visible()
    
    # Test form validation
    await page.evaluate("""
        // Show form for testing
        document.getElementById('authSection').style.display = 'none';
        document.getElementById('assessmentFormSection').style.display = 'block';
    """)
    
    # Try to submit empty form
    analyze_btn = page.locator("#analyzeBtn")
    await analyze_btn.click()
    
    # Should not submit due to required field
    url_input = page.locator("#websiteUrl")
    await expect(url_input).to_have_attribute("required", "")
    
    # Test URL auto-formatting
    await url_input.fill("example.com")
    await url_input.blur()
    value = await url_input.input_value()
    assert value == "https://example.com"
    print("✓ URL auto-formatting works")
    
    # Test alert messages
    await page.evaluate("""
        window.showAlert('error', 'Test error message');
        window.showAlert('success', 'Test success message');
        window.showAlert('info', 'Test info message');
    """)
    
    error_alert = page.locator("#errorMessage")
    success_alert = page.locator("#successMessage")
    info_alert = page.locator("#infoMessage")
    
    await expect(error_alert).to_have_class("alert alert-error show")
    await expect(success_alert).to_have_class("alert alert-success show")
    await expect(info_alert).to_have_class("alert alert-info show")
    print("✓ Alert system works")


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_assessment_ui_complete_flow())
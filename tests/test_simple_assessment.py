import re
from playwright.sync_api import Page, expect

# To run this test, you need to have FastAPI running.
# Use the command: uvicorn src.main:app --reload
# The test assumes the server is running on http://127.0.0.1:8000

BASE_URL = "http://127.0.0.1:8000"

def test_simple_assessment_flow(page: Page):
    # Navigate to the simple assessment UI page
    page.goto(f"{BASE_URL}/api/v1/simple-assessment/")

    # Expect a title "Simple Assessment - Database Row Display".
    expect(page).to_have_title("Simple Assessment - Database Row Display")

    # Fill in the form
    page.locator('input[name="url"]').fill("https://www.windriver.com/")
    page.locator('input[name="business_name"]').fill("Wind River")

    # Click the submit button
    page.locator('button[type="submit"]').click()

    # Wait for the status to indicate completion and for results to be visible
    # The timeout is set to 120 seconds because the assessment can be slow.
    status_element = page.locator("#status")
    expect(status_element).to_contain_text("Assessment completed successfully", timeout=120000)

    # Check for the main results container
    results_container = page.locator("#results-container")
    expect(results_container).to_be_visible()

    # Check if the assessment ID is displayed
    assessment_id_element = page.locator("#assessment-id")
    expect(assessment_id_element).to_contain_text(re.compile(r"Assessment ID: \d+"))

    # Check if the raw DB row is displayed
    db_row_element = page.locator("#db-row")
    expect(db_row_element).to_be_visible()
    expect(db_row_element).to_contain_text("Raw Assessment DB Row")

    # Check if decomposed metrics are displayed
    decomposed_metrics_element = page.locator("#decomposed-metrics")
    expect(decomposed_metrics_element).to_be_visible()
    expect(decomposed_metrics_element).to_contain_text("Decomposed Metrics")

    # Check if screenshots are displayed
    screenshots_element = page.locator("#screenshots")
    expect(screenshots_element).to_be_visible()
    expect(screenshots_element).to_contain_text("Screenshots")

    # Verify that at least one screenshot image is present
    screenshot_image = screenshots_element.locator("img")
    expect(screenshot_image.first).to_be_visible()

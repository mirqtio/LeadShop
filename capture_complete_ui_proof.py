#!/usr/bin/env python3
"""
Capture screenshots of the complete assessment UI
"""
import time
from playwright.sync_api import sync_playwright

def capture_screenshots():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        # Navigate to the complete assessment UI
        print("📸 Navigating to complete assessment UI...")
        page.goto('http://localhost:8001/static/complete_assessment_ui.html')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        # Take initial screenshot
        page.screenshot(path='complete_ui_initial.png', full_page=True)
        print("✅ Captured initial UI")
        
        # Fill in the form
        page.fill('#url', 'https://www.apple.com')
        page.fill('#businessName', 'Apple Inc.')
        
        # Take screenshot with form filled
        page.screenshot(path='complete_ui_filled.png', full_page=True)
        print("✅ Captured filled form")
        
        # Click submit
        page.click('#submitBtn')
        
        # Wait for assessment to start
        time.sleep(3)
        
        # Take screenshot of running assessment
        page.screenshot(path='complete_ui_running.png', full_page=True)
        print("✅ Captured running assessment")
        
        # Wait longer to see if we get results
        time.sleep(30)
        
        # Take final screenshot
        page.screenshot(path='complete_ui_progress.png', full_page=True)
        print("✅ Captured progress state")
        
        browser.close()
        print("\n✅ All screenshots captured!")

if __name__ == "__main__":
    capture_screenshots()
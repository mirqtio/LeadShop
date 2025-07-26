#!/usr/bin/env python3
"""Simple browser test to capture assessment results."""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

def test_assessment():
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # Create driver
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print("1. Opening assessment UI...")
        driver.get("http://localhost:8001/api/v1/simple-assessment")
        time.sleep(2)
        
        print("2. Filling form...")
        driver.find_element(By.CSS_SELECTOR, 'input[placeholder="https://example.com"]').send_keys("https://www.tesla.com")
        driver.find_element(By.CSS_SELECTOR, 'input[placeholder="Business Name (optional)"]').send_keys("Tesla")
        driver.find_element(By.CSS_SELECTOR, 'input[placeholder="City (optional)"]').send_keys("Austin")
        driver.find_element(By.CSS_SELECTOR, 'input[placeholder="State (optional)"]').send_keys("TX")
        
        # Take screenshot
        driver.save_screenshot("selenium_1_form_filled.png")
        
        print("3. Submitting assessment...")
        driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
        
        print("4. Waiting for results (60 seconds)...")
        # Wait for results
        wait = WebDriverWait(driver, 120)
        results = wait.until(EC.presence_of_element_located((By.ID, "results")))
        
        print("5. Results loaded! Waiting for full content...")
        time.sleep(10)  # Extra wait for all content
        
        # Take full page screenshot
        driver.save_screenshot("selenium_2_initial_results.png")
        
        # Scroll down to find decomposed scores
        print("6. Looking for decomposed scores...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        driver.save_screenshot("selenium_3_bottom_page.png")
        
        # Try to find decomposed scores text
        page_source = driver.page_source
        if "DECOMPOSED SCORES FROM DATABASE" in page_source:
            print("✓ Found decomposed scores section!")
            
            # Try to scroll to it
            elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'DECOMPOSED SCORES FROM DATABASE')]")
            if elements:
                driver.execute_script("arguments[0].scrollIntoView(true);", elements[0])
                time.sleep(1)
                driver.save_screenshot("selenium_4_decomposed_scores.png")
        else:
            print("✗ Decomposed scores section not found")
        
        print("\nTest completed! Check screenshots:")
        print("- selenium_1_form_filled.png")
        print("- selenium_2_initial_results.png") 
        print("- selenium_3_bottom_page.png")
        print("- selenium_4_decomposed_scores.png")
        
    except Exception as e:
        print(f"Error: {e}")
        driver.save_screenshot("selenium_error.png")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_assessment()
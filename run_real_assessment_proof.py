#!/usr/bin/env python3
"""
Run a real assessment and capture actual results
"""

import subprocess
import time
import os

print("🚀 Running real assessment through UI...")

# Use osascript to control Chrome
script = '''
tell application "Google Chrome"
    activate
    
    -- Open new tab with assessment UI
    set newTab to make new tab at end of tabs of window 1
    set URL of newTab to "http://localhost:8001/api/v1/simple-assessment"
    
    delay 3
    
    -- Fill in form fields using JavaScript
    tell newTab to execute javascript "
        document.getElementById('businessUrl').value = 'https://www.microsoft.com';
        document.getElementById('businessName').value = 'Microsoft Corporation';
        document.getElementById('city').value = 'Redmond';
        document.getElementById('state').value = 'WA';
    "
    
    delay 1
    
    -- Click submit button
    tell newTab to execute javascript "document.getElementById('submitBtn').click();"
    
    -- Wait for results
    delay 60
    
    -- Scroll to show all results
    tell newTab to execute javascript "window.scrollTo(0, document.body.scrollHeight);"
    
end tell
'''

# Run the AppleScript
subprocess.run(['osascript', '-e', script])

print("\n✅ Assessment submitted for Microsoft Corporation")
print("⏳ Waiting for results to load...")
print("\n📸 Please take a screenshot manually to capture the results!")
print("\nThe assessment should show:")
print("- PageSpeed scores")
print("- Security analysis")
print("- SEMrush data (Authority, Traffic, Keywords)")
print("- Google Business Profile (if available)")
print("- Screenshots captured")
print("- All decomposed scores from database")
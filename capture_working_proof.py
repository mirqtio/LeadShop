#!/usr/bin/env python3
import subprocess
import time
from datetime import datetime

# Take screenshot of the assessment UI
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
screenshot_path = f"assessment_working_{timestamp}.png"

# Use screencapture on macOS
subprocess.run(["screencapture", "-x", "-R", "0,0,1200,900", screenshot_path])
print(f"Screenshot saved to: {screenshot_path}")
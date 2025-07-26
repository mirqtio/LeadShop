"""
Fix all cost_records serialization issues across assessment modules
"""

import os
import re

# List of files to fix
files_to_fix = [
    "/Users/charlieirwin/LeadShop/src/assessments/screenshot_capture.py",
    "/Users/charlieirwin/LeadShop/src/assessments/gbp_integration.py",
    "/Users/charlieirwin/LeadShop/src/assessments/pagespeed.py",
    "/Users/charlieirwin/LeadShop/src/assessments/semrush_integration.py",
    "/Users/charlieirwin/LeadShop/src/assessments/security_analysis.py"
]

# Pattern to find cost_records assignments in return statements
pattern = r'cost_records=cost_records'
replacement = 'cost_records=[]  # Exclude SQLAlchemy objects to avoid serialization issues'

for file_path in files_to_fix:
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Replace all occurrences
        new_content = content.replace(pattern, replacement)
        
        if new_content != content:
            with open(file_path, 'w') as f:
                f.write(new_content)
            print(f"Fixed {file_path}")
        else:
            print(f"No changes needed in {file_path}")
    else:
        print(f"File not found: {file_path}")

print("\nAll files processed.")
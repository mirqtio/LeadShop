"""
Fix for visual analysis serialization issue
"""

import os
import sys

# Read the visual_analysis.py file
file_path = "/Users/charlieirwin/LeadShop/src/assessments/visual_analysis.py"

with open(file_path, 'r') as f:
    content = f.read()

# Find and replace the problematic line
# Change cost_records to not include the actual SQLAlchemy objects
old_line = "cost_records=cost_records"
new_line = "cost_records=[]  # Exclude SQLAlchemy objects to avoid serialization issues"

content = content.replace(old_line, new_line)

# Write the fixed content back
with open(file_path, 'w') as f:
    f.write(content)

print("Fixed visual_analysis.py to avoid serialization issues with AssessmentCost objects")
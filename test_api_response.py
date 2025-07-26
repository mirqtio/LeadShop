#!/usr/bin/env python3
"""Test the API response to see what data is returned"""

import requests
import json
import time

# Generate unique URL
timestamp = int(time.time())
test_url = f"https://www.mozilla.org?api_test={timestamp}"

print(f"Testing API with URL: {test_url}")

# Submit assessment
response = requests.post(
    "http://localhost:8001/api/v1/simple-assessment/execute",
    json={
        "url": test_url,
        "business_name": "API Test Business"
    }
)

print(f"\nStatus Code: {response.status_code}")
print(f"\nResponse:")
print(json.dumps(response.json(), indent=2))

# Extract task_id if available
data = response.json()
if 'task_id' in data:
    print(f"\nTask ID: {data['task_id']}")
    
# Show what's in results
if 'results' in data:
    print(f"\nResults keys: {list(data['results'].keys())}")
    if 'security_data' in data['results']:
        print("\n✓ Security data is in the response!")
        print(json.dumps(data['results']['security_data'], indent=2))
    else:
        print("\n✗ No security data in the response")
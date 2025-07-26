#!/usr/bin/env python3
"""Quick test of Google.com with PageSpeed"""

import requests

# Direct test with minimal parameters
url = "https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed"
params = {
    "url": "https://google.com",  # Try without www
    "key": "AIzaSyAgsawn7gSnxiZ2stp_K1vS6oQ47FN_XZE",
    "strategy": "mobile"
}

print("Testing google.com (without www)...")
response = requests.get(url, params=params, timeout=30)
print(f"Status: {response.status_code}")

if response.status_code != 200:
    print(f"Error: {response.json().get('error', {}).get('message', 'Unknown')}")
else:
    data = response.json()
    score = data.get("lighthouseResult", {}).get("categories", {}).get("performance", {}).get("score", 0) * 100
    print(f"Score: {score}")

# Try with www
print("\nTesting www.google.com (with www)...")
params["url"] = "https://www.google.com"
response = requests.get(url, params=params, timeout=30)
print(f"Status: {response.status_code}")

if response.status_code != 200:
    print(f"Error: {response.json().get('error', {}).get('message', 'Unknown')}")

# Try Apple
print("\nTesting www.apple.com...")
params["url"] = "https://www.apple.com"
response = requests.get(url, params=params, timeout=30)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    score = data.get("lighthouseResult", {}).get("categories", {}).get("performance", {}).get("score", 0) * 100
    print(f"Score: {score}")
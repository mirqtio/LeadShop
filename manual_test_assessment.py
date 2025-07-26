#!/usr/bin/env python3
"""Manually trigger assessment and wait for completion."""

import requests
import time
import json

def run_assessment():
    url = "http://localhost:8001/api/v1/simple-assessment/run"
    
    data = {
        "url": "https://www.airbnb.com",
        "business_name": "Airbnb",
        "address": "888 Brannan Street",
        "city": "San Francisco",
        "state": "CA"
    }
    
    print("Submitting assessment for Airbnb...")
    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"Assessment ID: {result.get('assessment_id')}")
        print("Assessment submitted successfully!")
        print("\nWaiting for assessment to complete...")
        print("This may take 30-60 seconds...")
        return result.get('assessment_id')
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

if __name__ == "__main__":
    assessment_id = run_assessment()
    if assessment_id:
        print(f"\nAssessment is running with ID: {assessment_id}")
        print("Please wait for it to complete and then navigate to:")
        print("http://localhost:8001/api/v1/simple-assessment")
        print("The results should appear automatically.")
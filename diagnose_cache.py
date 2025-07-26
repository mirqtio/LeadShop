#!/usr/bin/env python3
"""
Diagnose the caching issue by comparing what different methods see
"""
import requests
import subprocess
import hashlib

def get_content_curl():
    """Get content using curl"""
    result = subprocess.run(
        ["curl", "-s", "http://localhost:8001/api/v1/simple-assessment/"],
        capture_output=True,
        text=True
    )
    return result.stdout

def get_content_requests():
    """Get content using Python requests"""
    response = requests.get("http://localhost:8001/api/v1/simple-assessment/")
    return response.text

def get_content_docker():
    """Get content from inside Docker"""
    result = subprocess.run(
        ["docker", "exec", "leadfactory_app", "curl", "-s", "http://localhost:8000/api/v1/simple-assessment/"],
        capture_output=True,
        text=True
    )
    return result.stdout

def analyze_content(content, source):
    """Analyze content characteristics"""
    print(f"\n=== {source} ===")
    print(f"Length: {len(content)} bytes")
    print(f"MD5: {hashlib.md5(content.encode()).hexdigest()}")
    print(f"First line: {content.split(chr(10))[0][:100]}")
    print(f"Has 'Decomposed Metrics': {'Decomposed Metrics' in content}")
    print(f"Has 'Scripts section': {'Scripts section' in content}")
    print(f"Has timestamp comment: {'Generated at' in content}")
    
    # Count key elements
    form_count = content.count('<form')
    table_count = content.count('<table')
    script_count = content.count('<script')
    
    print(f"Form tags: {form_count}")
    print(f"Table tags: {table_count}")
    print(f"Script tags: {script_count}")

if __name__ == "__main__":
    print("Diagnosing cache issue...")
    
    # Test different methods
    try:
        curl_content = get_content_curl()
        analyze_content(curl_content, "CURL from host")
    except Exception as e:
        print(f"CURL failed: {e}")
    
    try:
        requests_content = get_content_requests()
        analyze_content(requests_content, "Python requests from host")
    except Exception as e:
        print(f"Requests failed: {e}")
    
    try:
        docker_content = get_content_docker()
        analyze_content(docker_content, "CURL from inside Docker")
    except Exception as e:
        print(f"Docker curl failed: {e}")
    
    # Compare v2 endpoint
    print("\n" + "="*50)
    print("Testing /v2 endpoint:")
    try:
        v2_response = requests.get("http://localhost:8001/api/v1/simple-assessment/v2")
        analyze_content(v2_response.text, "V2 endpoint")
    except Exception as e:
        print(f"V2 failed: {e}")
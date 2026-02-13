
import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(method, url, name, expected_status, token=None, json_data=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{url}", headers=headers, timeout=5)
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{url}", headers=headers, json=json_data, timeout=5)
        elif method == "PUT":
            response = requests.put(f"{BASE_URL}{url}", headers=headers, json=json_data, timeout=5)
        elif method == "DELETE":
            response = requests.delete(f"{BASE_URL}{url}", headers=headers, timeout=5)
        
        if response.status_code in expected_status:
            print(f"PASS: {name} ({method} {url}) returned {response.status_code}")
            return True
        else:
            print(f"FAIL: {name} ({method} {url}) returned {response.status_code}, expected {expected_status}")
            print(f"Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"ERROR: {name} ({method} {url}) failed: {e}")
        return False

def main():
    print("Starting Authorization Verification...")
    
    # 1. Test Public Endpoints
    test_endpoint("GET", "/jobs", "Get Jobs (Public)", [200])
    
    # Test POST /jobs (User requested public)
    # We need a valid job payload
    job_payload = {
        "title": "Test Job Public",
        "department": "Engineering",
        "location": "Remote",
        "type": "full-time",
        "experience_level": "entry",
        "description": "Test"
    }
    test_endpoint("POST", "/jobs", "Create Job (Public)", [200, 201], json_data=job_payload)

    # 2. Test Protected Endpoints (No Token)
    test_endpoint("GET", "/applications", "Get Applications (No Token)", [401, 403])
    test_endpoint("GET", "/video-questions", "Get Video Questions (No Token)", [401, 403])
    
    # 3. Test Protected Endpoints (With Token)
    # Login first
    login_data = {"email": "admin@pulsepharma.com", "password": "pavan@123"}
    # Note: Login expects form data, not json
    try:
        response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
        if response.status_code == 200:
            token = response.json().get("access_token")
            print("Login Successful, got token.")
            
            test_endpoint("GET", "/applications", "Get Applications (With Token)", [200], token=token)
            test_endpoint("GET", "/video-questions", "Get Video Questions (With Token)", [200], token=token)
            
        else:
            print(f"FAIL: Login failed with {response.status_code}")
            return
    except Exception as e:
        print(f"ERROR: Login failed: {e}")
        return

if __name__ == "__main__":
    main()

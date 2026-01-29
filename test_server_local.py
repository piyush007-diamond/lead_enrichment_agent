import requests
import json
import time
import subprocess
import sys

def run_tests():
    print("🚀 Starting Local Server Validation...")
    
    # 1. Start Server in Background
    # We assume 'uvicorn execution.server:app' will run on port 8000
    # server_process = subprocess.Popen(
    #    [sys.executable, "-m", "uvicorn", "execution.server:app", "--port", "8000"],
    #    stdout=subprocess.DEVNULL,
    #    stderr=subprocess.PIPE
    # )
    
    # print("⏳ Waiting 5s for server startup...")
    # time.sleep(5)
    server_process = None
    
    base_url = "http://localhost:8000"
    
    try:
        # 2. Test Health
        print("\n--- Test 1: Health Check ---")
        resp = requests.get(base_url + "/")
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
        if resp.status_code == 200 and resp.json().get("status") == "online":
            print("✅ PASS")
        else:
            print("❌ FAIL")
            
        # 3. Test Availability (Date Parser + GCal + Slot Calc)
        print("\n--- Test 2: Check Availability ---")
        payload = {"date": "tomorrow", "query_type": "single"}
        resp = requests.post(base_url + "/tools/checkAvailability", json=payload)
        print(f"Payload: {payload}")
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Result: {data.get('result')[:100]}...") # Truncate for display
        if resp.status_code == 200 and "result" in data:
            print("✅ PASS")
        else:
            print("❌ FAIL")
            
        # 4. Test Save Patient (Supabase)
        print("\n--- Test 3: Save Patient ---")
        patient_payload = {
            "name": "Integration TestUser",
            "phone_number": "TEST_INTEGRATION_999",
            "vapi_call_id": "test-call-id"
        }
        resp = requests.post(base_url + "/tools/savePatient", json=patient_payload)
        print(f"Payload: {patient_payload}")
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Response: {data}")
        if resp.status_code == 200 and data.get("success") is True:
            print("✅ PASS")
        else:
            print("❌ FAIL")
            
    except Exception as e:
        print(f"❌ Exception during tests: {e}")
    finally:
        print("\n🛑 Stopping Server...")
        if server_process:
            server_process.terminate()
            server_process.wait()

if __name__ == "__main__":
    run_tests()

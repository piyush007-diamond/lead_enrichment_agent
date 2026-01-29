import requests

URL = "https://h2kyerajpzj4.share.zrok.io/tools/checkAvailability"

# Test Case: Missing Date (simulating "yes" confirmation where date is lost)
PAYLOAD = {
    "message": {
        "toolCallList": [
            {
                "id": "manual-test-null-date",
                "arguments": {
                    "date": None  # Simulate missing date
                }
            }
        ]
    }
}

print(f"Testing NULL date at {URL}...")
try:
    r = requests.post(URL, json=PAYLOAD)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
except Exception as e:
    print(f"Error: {e}")

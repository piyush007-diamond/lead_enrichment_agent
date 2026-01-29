import requests

URL = "https://ee0bc7bfc30d.ngrok-free.app/tools/checkAvailability"
PAYLOAD = {
    "date": "next friday",
    "toolCallId": "manual-test-123"
}

print(f"Sending POST to {URL}...")
try:
    headers = {
        "ngrok-skip-browser-warning": "1",
        "User-Agent": "MyCustomAgent/1.0"
    }
    r = requests.post(URL, json=PAYLOAD, headers=headers)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
except Exception as e:
    print(f"Error: {e}")

import requests

URL = "https://h2kyerajpzj4.share.zrok.io/tools/checkAvailability"
PAYLOAD = {
    "date": "next friday",
    "toolCallId": "manual-test-zrok"
}

print(f"Testing zrok tunnel: {URL}")
try:
    r = requests.post(URL, json=PAYLOAD)
    print(f"✓ Status: {r.status_code}")
    print(f"✓ Response: {r.text}")
except Exception as e:
    print(f"✗ Error: {e}")

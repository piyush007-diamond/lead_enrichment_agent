import requests
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("VAPI_PRIVATE_KEY")
ASSISTANT_ID = "3cca2179-339f-4f68-935c-5d1c0208fbbe"
BASE_URL = "https://api.vapi.ai"

if not API_KEY:
    print("Error: VAPI_PRIVATE_KEY not found in .env")
    exit(1)

def test_chat():
    url = f"{BASE_URL}/chat"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "assistantId": ASSISTANT_ID,
        "input": "next friday"
    }
    
    print(f"Sending test message to Vapi Assistant: {ASSISTANT_ID}")
    print(f"Message: 'next friday'\n")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(f"Response Body: {response.text}")
            return None
        
        data = response.json()
        print("--- VAPI RESPONSE ---")
        print(json.dumps(data, indent=2))
        
        # Check actual message content
        if 'message' in data and 'content' in data['message']:
             print(f"ASSISTANT REPLY: {data['message']['content']}")
             
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"Error calling Vapi Chat API: {e}")
        return None

if __name__ == "__main__":
    test_chat()

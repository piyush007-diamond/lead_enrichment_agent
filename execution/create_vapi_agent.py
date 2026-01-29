import requests
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("VAPI_PRIVATE_KEY")
BASE_URL = "https://api.vapi.ai"

if not API_KEY:
    raise ValueError("VAPI_PRIVATE_KEY not found in .env file")

def create_assistant(name, system_prompt):
    url = f"{BASE_URL}/assistant"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Default configuration payload
    payload = {
        "name": name,
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "en"
        },
        "model": {
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                }
            ]
        },
        "voice": {
            "provider": "11labs",
            "voiceId": "burt" # Default male voice
        },
        "firstMessage": "Hello! How can I help you today?"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        data = response.json()
        print(f"Success! Assistant created.")
        print(f"ID: {data.get('id')}")
        print(f"Name: {data.get('name')}")
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"Error creating assistant: {e}")
        if response.text:
            print(f"Response details: {response.text}")
        return None

if __name__ == "__main__":
    # Example usage - in a real flow, these might come from args or a config file
    agent_name = "Demo Assistant"
    prompt = "You are a helpful and polite voice assistant. Keep answers concise."
    
    create_assistant(agent_name, prompt)

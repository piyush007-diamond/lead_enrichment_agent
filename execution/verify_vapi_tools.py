import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("VAPI_PRIVATE_KEY")
BASE_URL = "https://api.vapi.ai"

def verify_tools():
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    print("Fetching tools from Vapi...")
    try:
        r = requests.get(f"{BASE_URL}/tool", headers=headers)
        r.raise_for_status()
        tools = r.json()
        
        for t in tools:
            name = t.get('function', {}).get('name', 'Unknown')
            url = t.get('server', {}).get('url', 'No URL')
            print(f"Tool: {name}")
            print(f"  ID: {t.get('id')}")
            print(f"  URL: {url}")
            print("-" * 20)
            
    except Exception as e:
        print(f"Error fetching tools: {e}")

if __name__ == "__main__":
    verify_tools()

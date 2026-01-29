"""
Automated script to:
1. Start ngrok tunnel
2. Get the public URL
3. Update Vapi tools configuration
4. Test the connection
"""
import subprocess
import time
import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("VAPI_PRIVATE_KEY")
BASE_URL = "https://api.vapi.ai"

def start_ngrok():
    """Start ngrok in background"""
    print("Starting ngrok tunnel...")
    try:
        # Kill any existing ngrok processes
        subprocess.run(["taskkill", "/F", "/IM", "ngrok.exe"], 
                      capture_output=True, check=False)
        time.sleep(2)
        
        # Start ngrok
        subprocess.Popen(["ngrok", "http", "8000"], 
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)
        time.sleep(5)  # Wait for ngrok to start
        print("✓ Ngrok started")
        return True
    except Exception as e:
        print(f"✗ Failed to start ngrok: {e}")
        return False

def get_ngrok_url():
    """Get the public URL from ngrok API"""
    print("Fetching ngrok URL...")
    try:
        r = requests.get("http://127.0.0.1:4040/api/tunnels")
        tunnels = r.json()["tunnels"]
        url = tunnels[0]["public_url"]
        print(f"✓ Got URL: {url}")
        return url
    except Exception as e:
        print(f"✗ Failed to get URL: {e}")
        return None

def update_vapi_tools(base_url):
    """Update Vapi tools with new URL"""
    print("Updating Vapi tools...")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Get existing tools
    try:
        r = requests.get(f"{BASE_URL}/tool", headers=headers)
        r.raise_for_status()
        tools = r.json()
    except Exception as e:
        print(f"✗ Failed to fetch tools: {e}")
        return False
    
    # Update each tool
    tools_config = {
        "checkAvailability": {
            "url": f"{base_url}/tools/checkAvailability",
            "function": {
                "name": "checkAvailability",
                "description": "Check for available appointment slots for a specific date.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "The date to check, e.g. 'tomorrow', 'next friday', 'Jan 28'."
                        },
                        "query_type": {
                            "type": "string",
                            "enum": ["single", "range"],
                            "description": "Whether to check a single day or a range."
                        },
                        "toolCallId": {
                            "type": "string",
                            "description": "The Vapi ID for this tool call."
                        }
                    },
                    "required": ["date"]
                }
            }
        },
        "savePatient": {
            "url": f"{base_url}/tools/savePatient",
            "function": {
                "name": "savePatient",
                "description": "Save or update patient details.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Patient's full name."},
                        "phone_number": {"type": "string", "description": "Patient's phone number."},
                        "vapi_call_id": {"type": "string", "description": "Unique call ID from Vapi."},
                        "toolCallId": {"type": "string", "description": "The Vapi ID for this tool call."}
                    },
                    "required": ["name", "phone_number"]
                }
            }
        }
    }
    
    for tool in tools:
        tool_name = tool.get('function', {}).get('name')
        if tool_name in tools_config:
            tool_id = tool['id']
            config = tools_config[tool_name]
            
            payload = {
                "function": config['function'],
                "server": {
                    "url": config['url'],
                    "headers": {
                        "ngrok-skip-browser-warning": "1",
                        "User-Agent": "Vapi/1.0"
                    }
                },
                "async": False
            }
            
            try:
                r = requests.patch(f"{BASE_URL}/tool/{tool_id}", 
                                 headers=headers, json=payload)
                if r.status_code == 200:
                    print(f"✓ Updated {tool_name}")
                else:
                    print(f"✗ Failed to update {tool_name}: {r.status_code}")
            except Exception as e:
                print(f"✗ Error updating {tool_name}: {e}")
    
    return True

def test_connection(base_url):
    """Test if the tunnel works"""
    print("Testing connection...")
    try:
        test_headers = {
            "ngrok-skip-browser-warning": "1",
            "User-Agent": "Vapi/1.0"
        }
        r = requests.post(
            f"{base_url}/tools/checkAvailability",
            json={"date": "tomorrow", "toolCallId": "test-123"},
            headers=test_headers
        )
        print(f"✓ Connection test: {r.status_code}")
        print(f"  Response: {r.text[:100]}")
        return r.status_code == 200
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        return False

def main():
    print("=" * 50)
    print("AUTOMATED TUNNEL & VAPI SETUP")
    print("=" * 50)
    
    # Step 1: Start ngrok
    if not start_ngrok():
        print("\n❌ Setup failed at ngrok start")
        return
    
    # Step 2: Get URL
    url = get_ngrok_url()
    if not url:
        print("\n❌ Setup failed at URL retrieval")
        return
    
    # Step 3: Update Vapi
    if not update_vapi_tools(url):
        print("\n❌ Setup failed at Vapi update")
        return
    
    # Step 4: Test
    if not test_connection(url):
        print("\n⚠️  Connection test failed, but Vapi is updated")
    
    print("\n" + "=" * 50)
    print("✅ SETUP COMPLETE!")
    print(f"   Tunnel URL: {url}")
    print("   Vapi tools updated")
    print("   Ready for testing!")
    print("=" * 50)

if __name__ == "__main__":
    main()

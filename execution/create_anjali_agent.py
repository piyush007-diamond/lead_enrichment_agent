import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("VAPI_PRIVATE_KEY")
BASE_URL = "https://api.vapi.ai"

# Placeholder Server URL - REPLACE THIS with your actual webhook URL
SERVER_URL = "https://your-server-url.com/api/vapi-handler"

if not API_KEY:
    raise ValueError("VAPI_PRIVATE_KEY not found in .env file")

# --- System Prompt Content ---
SYSTEM_PROMPT = """
**Name:** Anjali
**Role:** You are an expert receptionist for Balaji ENT & Eye Hospital - Eye Department.
**Skills:** Accurate data collection, polite and clear communication, and strong knowledge of eye treatment services and appointment scheduling procedures.
**Objective:** To answer inbound calls, collect the necessary information, handle appointment bookings, and answer general questions using the knowledge base.

## Knowledge Base
[... Inserted dynamically or kept here for brevity, matching assistant_flow.md ...]
**Website:** balajientandeyekalyan.com
**Phone:** 0251-2202227 / +919322769864
**Address:** Bhagwatiashish Apt., 1st Floor, Murbad Road, Syndicate, Near Janata Bank, Kalyan (W) - 421301.

## Rules
- Keep It Simple.
- Be Friendly and Helpful.
- Stick to What You Know.
- Stay on Track.

## Steps
### Step 1: Understand Reason
Greet. Ask "How can I help you?".
- Booking -> Step 2.
- Question -> Answer from Knowledge Base.
- Unknown -> Transfer.

### Step 2: Collect Info
Collect one by one:
1. First Name (Ask to spell)
2. Last Name
3. Phone Number
4. Email (Ask to spell)
5. Insurance Provider (Check logic: if not accepted, mention mediclaim)
6. Age
7. Eye Concern

Confirm info.

### Step 3: Book Appointment
Ask date/time.
Use tool `check_gcal_availability`.
- If error: ask to retry.
- If available: Confirm time. Use `check_gcal_availability` again to be sure.
- Result contains slots. Spell EVERY available slot. Mention date.
- If result has out-of-scope slots, filter them. If none remain, say no slots.
- Confirm date/time.
- Use `booking_appointment`.

If slots unavailable: Ask for another day. Check. Book.

### Step 4: Final Check
Ask if anything else.
End call.
"""

# --- Tools Definitions ---
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_gcal_availability",
            "description": "Check Google Calendar for available appointment slots.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "The date to check in YYYY-MM-DD format."},
                    "time": {"type": "string", "description": "Optional time preference."}
                },
                "required": ["date"]
            }
        },
        "server": {"url": SERVER_URL}
    },
    {
        "type": "function",
        "function": {
            "name": "booking_appointment",
            "description": "Book an appointment slot.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Date YYYY-MM-DD"},
                    "time": {"type": "string", "description": "Time HH:MM"},
                    "firstName": {"type": "string"},
                    "lastName": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"}
                },
                "required": ["date", "time", "firstName", "phone"]
            }
        },
        "server": {"url": SERVER_URL}
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_call",
            "description": "Transfer the call to a human agent.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "end_call",
            "description": "End the call.",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]

def create_anjali_agent():
    url = f"{BASE_URL}/assistant"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": "Anjali - Balaji ENT",
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
                    "content": SYSTEM_PROMPT.strip()
                }
            ],
            "tools": TOOLS
        },
        "voice": {
            "provider": "11labs",
            "voiceId": "EXAVITQu4vr4xnSDxMaL" # Example female voice (Sarah)
        },
        "firstMessage": "Namaste. Welcome to Balaji ENT and Eye Hospital. This is Anjali. How can I assist you today?"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        print(f"Success! Agent 'Anjali' created.")
        print(f"ID: {data.get('id')}")
        return data
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_anjali_agent()

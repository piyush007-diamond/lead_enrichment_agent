import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("VAPI_PRIVATE_KEY")
BASE_URL = "https://api.vapi.ai"

# Tools Config to Apply
NEW_URL_BASE = "https://mofzm567gzj3.share.zrok.io"

TOOLS_CONFIG = [
  {
    "name": "checkAvailability",
    "description": "Check for available appointment slots for a specific date or range of dates.",
     "function": { 
        "name": "checkAvailability",
        "description": "Check for available appointment slots for a specific date or range of dates.",
        "parameters": {
            "type": "object",
            "properties": {
            "date": {
                "type": "string",
                "description": "The date to check, e.g. 'tomorrow', 'next friday', 'Jan 28', 'this week'."
            },
            "query_type": {
                "type": "string",
                "enum": ["single", "range"],
                "description": "Whether to check a single day or a range of days (e.g. 'this week'). Default is single."
            },
            "toolCallId": {
                "type": "string",
                "description": "The Vapi ID for this tool call."
            }
            },
            "required": ["date"]
        }
    },
    "server": {
      "url": f"{NEW_URL_BASE}/tools/checkAvailability"
    }
  },
  {
      "name": "savePatient",
      "description": "Save or update patient details and appointment info.",
      "function": {
        "name": "savePatient",
        "description": "Save or update patient details and appointment info.",
        "parameters": {
            "type": "object",
            "properties": {
            "name": {
                "type": "string",
                "description": "Patient's full name."
            },
            "phone_number": {
                "type": "string",
                "description": "Patient's phone number."
            },
            "vapi_call_id": {
                "type": "string",
                "description": "Unique call ID from Vapi."
            },
            "toolCallId": {
                "type": "string",
                "description": "The Vapi ID for this tool call."
            },
            "date": {
                "type": "string",
                "description": "The date of the appointment (e.g. '2026-01-29' or 'tomorrow')."
            },
            "time": {
                "type": "string",
                "description": "The time of the appointment (e.g. '4:00 PM')."
            },
            "email": {
                "type": "string",
                "description": "Patient's email address."
            }
            },
            "required": ["name", "phone_number", "date", "time", "email"]
        }
      },
      "server": {
          "url": f"{NEW_URL_BASE}/tools/savePatient"
      }
  },
    {
      "name": "cancelAppointment",
       "description": "Cancel an existing appointment.",
      "function": {
        "name": "cancelAppointment",
        "description": "Cancel an existing appointment. Use this when the user asks to cancel, remove, or delete their booking.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The patient's name."
                },
                "phone_number": {
                    "type": "string",
                    "description": "The patient's phone number (needed for lookup)."
                }
            },
            "required": ["phone_number", "name"]
        }
      },
      "server": {
        "url": f"{NEW_URL_BASE}/tools/cancelAppointment"
      }
    },
    {
      "name": "lookupAppointment",
      "description": "Find an existing appointment.",
      "function": {
        "name": "lookupAppointment",
        "description": "Find an existing appointment to check details before cancelling or rescheduling.",
        "parameters": {
            "type": "object",
            "properties": {
                "phone_number": {
                    "type": "string",
                    "description": "The patient's phone number (Primary search key)."
                }
            },
            "required": ["phone_number"]
        }
      },
      "server": {
        "url": f"{NEW_URL_BASE}/tools/lookupAppointment"
      }
    }
]

def sync_tools():
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    print("--- 1. Fetching Existing Tools ---")
    try:
        r = requests.get(f"{BASE_URL}/tool", headers=headers)
        r.raise_for_status()
        existing_tools = r.json()
    except Exception as e:
        print(f"Error fetching tools: {e}")
        return

    active_tool_ids = []

    print("\n--- 2. Syncing Tools ---")
    for config in TOOLS_CONFIG:
        target_name = config["function"]["name"] # Match by function name
        match = next((t for t in existing_tools if t.get('function', {}).get('name') == target_name), None)
        
        # Common fields
        common_body = {
            "function": config['function'],
            "server": config['server'],
            "async": False
        }

        if match:
            tool_id = match['id']
            print(f"   Updating '{target_name}' (ID: {tool_id})...")
            try:
                # PATCH: Do NOT include 'type' (it causes 400 Bad Request)
                rr = requests.patch(f"{BASE_URL}/tool/{tool_id}", headers=headers, json=common_body)
                if rr.status_code == 200:
                    print(f"   [OK] Updated")
                    active_tool_ids.append(tool_id)
                else:
                    print(f"   [ERR] Update Failed: {rr.text}")
            except Exception as e:
                 print(f"   [ERR] Exception: {e}")
        else:
            print(f"   Creating '{target_name}'...")
            try:
                # POST: MUST include 'type'
                create_payload = common_body.copy()
                create_payload["type"] = "function"
                
                rr = requests.post(f"{BASE_URL}/tool", headers=headers, json=create_payload)
                if rr.status_code == 201:
                    new_tool = rr.json()
                    tool_id = new_tool['id']
                    print(f"   [OK] Created (ID: {tool_id})")
                    active_tool_ids.append(tool_id)
                else:
                    print(f"   [ERR] Creation Failed: {rr.text}")
            except Exception as e:
                print(f"   ❌ Exception: {e}")

    print(f"\nActive Tool IDs: {active_tool_ids}")

    print("\n--- 3. Linking to Assistant ---")
    # Find Assistant
    try:
        r = requests.get(f"{BASE_URL}/assistant", headers=headers)
        r.raise_for_status()
        assistants = r.json()
        # Find first one for now (or match name if possible)
        # Assuming user has one main assistant or we pick 'Anjali'
        target_assistant = next((a for a in assistants if "anjali" in a.get("name", "").lower() or "balaji" in a.get("name", "").lower()), None)
        
        if not target_assistant and assistants:
            target_assistant = assistants[0] # Fallback to first
            print(f"⚠️ 'Anjali' not found, defaulting to first assistant: {target_assistant.get('name')}")

        if target_assistant:
            ass_id = target_assistant['id']
            print(f"Using Assistant: {target_assistant.get('name')} (ID: {ass_id})")
            
            # Fetch full assistant details first to be safe
            # (The list endpoint might return summary, strict GET /assistant/id is safer)
            r_full = requests.get(f"{BASE_URL}/assistant/{ass_id}", headers=headers)
            r_full.raise_for_status()
            full_assistant = r_full.json()
            
            current_model = full_assistant.get("model", {})
            print(f"DEBUG: Current Assistant Model Tools: {current_model.get('tools')}")
            
            # Construct new tools list
            # We want to use our active_tool_ids.
            # We should probably KEEP existing tools if they aren't ours? 
            # Or just overwrite? User asked to "add them".
            # Safe strategy: Filter out old versions of OUR tools, keep others, add new ones.
            # But we don't know the IDs of others.
            # Simplest for now: Just overwrite with OUR complete set logic or 
            # append only if not present?
            # Vapi tools are ID based.
            
            # Let's just USE the active_tool_ids we just synced.
            # This ensures the assistant uses EXACTLY the tools we configured.
            # Construct new tools list
            # FIX: Vapi requires type='function' even for referenced tools by ID (based on error msg)
            new_tool_refs = [{"type": "function", "id": tid} for tid in active_tool_ids]
            
            # Construct SAFE model payload (only essential fields)
            # Sending full object often fails due to read-only fields
            safe_model = {
                "tools": new_tool_refs
            }
            
            # Carry over essential fields if they exist
            if "provider" in current_model:
                safe_model["provider"] = current_model["provider"]
            if "model" in current_model:
                safe_model["model"] = current_model["model"]
            if "temperature" in current_model:
                 safe_model["temperature"] = current_model["temperature"]
            if "systemMessage" in current_model:
                 safe_model["systemMessage"] = current_model["systemMessage"]

            print(f"   Patching with model keys: {list(safe_model.keys())}")
            
            patch_body = {
                "model": safe_model
            }
            
            rr = requests.patch(f"{BASE_URL}/assistant/{ass_id}", headers=headers, json=patch_body)
            if rr.status_code == 200:
                print("[OK] Assistant Updated with new Tools")
            else:
                print(f"[ERR] Failed to update Assistant: {rr.text}")
                
        else:
            print("❌ No assistant found to update.")

    except Exception as e:
        print(f"Error fetching/updating assistant: {e}")

if __name__ == "__main__":
    sync_tools()

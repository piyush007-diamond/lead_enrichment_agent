"""
Voice Agent Server - Stage 6 (Final Integration)
================================================
Purpose: FastAPI backend to serve as the "brain" for the Vapi Voice Agent.
         Integrates all validated modules:
         - Date Parser (Relative dates -> ISO)
         - Google Calendar (Busy events)
         - Slot Calculator (Work hours logic 9-5)
         - Supabase (Patient data)

ENDPOINTS:
1. POST /tools/checkAvailability
   - Input: { "date": "next friday" }
   - Output: { "result": "Available slots are 10am, 2pm..." }

2. POST /tools/savePatient
   - Input: { "name": "John", "phone": "123..." }
   - Output: { "success": true, "id": 123 }

3. GET /
   - Health check

RUNNING:
   uvicorn execution.server:app --reload
"""

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uvicorn
import os
import datetime
from contextlib import asynccontextmanager

# Import our validated modules
from execution.date_parser import parse_relative_date, get_week_dates_for_rolling_availability
from execution.slot_calculator import calculate_free_slots, get_rolling_availability, format_availability_for_voice
from execution.supabase_service import SupabaseService, Patient
from execution.gcal_service import GoogleCalendarService, TIMEZONE
import pytz

# Service Instances (Lazy loaded)
gcal_service = None
supabase_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    global gcal_service, supabase_service
    print("Starting Voice Agent Server...")
    
    # Initialize GCal (Validation confirmed credentials exist)
    try:
        gcal_service = GoogleCalendarService()
        print("Google Calendar Service Initialized")
    except Exception as e:
        print(f"Google Calendar Init Failed: {e}")
        print("   (Ensure credentials.json exists and python -m execution.gcal_service was run)")

    # Initialize Supabase
    try:
        supabase_service = SupabaseService()
        print("Supabase Service Initialized")
    except Exception as e:
        print(f"Supabase Init Failed: {e}")
        print("   (Check .env file for Supabase URL/Key)")
        
    yield
    print("Server shutting down...")

app = FastAPI(title="Voice Agent Brain", lifespan=lifespan)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _format_response(message: str, tool_call_id: Optional[str] = None, is_error: bool = False) -> dict:
    """
    Format response according to Vapi's required structure.
    
    Vapi requires this EXACT format:
    {
        "results": [
            {
                "toolCallId": "call_123",
                "result": "Single-line string response"
            }
        ]
    }
    
    Args:
        message: The response message (will be converted to single-line)
        tool_call_id: The toolCallId from the incoming request (must match exactly)
        is_error: If True, uses "error" field instead of "result"
    
    Returns:
        Properly formatted dict for Vapi
    """
    # Remove line breaks and extra whitespace
    clean_message = " ".join(message.split())
    
    result_obj = {
        "toolCallId": tool_call_id or "unknown"
    }
    
    if is_error:
        result_obj["error"] = clean_message
    else:
        result_obj["result"] = clean_message
    
    return {
        "results": [result_obj]
    }

# ============================================================================
# DATA MODELS
# ============================================================================

class AvailabilityRequest(BaseModel):
    model_config = {"extra": "allow"}  # Allow Vapi to send extra fields
    
    date: str = Field(..., description="Natural language date (e.g., 'tomorrow', 'next friday', 'Jan 28')")
    query_type: Optional[str] = Field("single", description="'single' or 'range'")
    toolCallId: Optional[str] = Field(None, description="Vapi Tool Call ID")

class PatientRequest(BaseModel):
    model_config = {"extra": "allow"}  # Allow Vapi to send extra fields
    
    name: str
    phone_number: str
    vapi_call_id: Optional[str] = None
    toolCallId: Optional[str] = Field(None, description="Vapi Tool Call ID")

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "services": {
            "gcal": gcal_service is not None,
            "supabase": supabase_service is not None
        }
    }

@app.post("/tools/checkAvailability")
async def check_availability(raw_request: Request):
    """
    Tool called by Vapi to check appointment slots.
    Handles Vapi's nested request format.
    """
    # Get the full Vapi request
    try:
        vapi_payload = await raw_request.json()
        print(f"DEBUG: Full Vapi Payload: {vapi_payload}")
        
        # LOG TO FILE for persistent debugging
        with open("webhook_log.txt", "a") as f:
            import json
            f.write(f"\n\n--- REQUEST AT {datetime.datetime.now()} ---\n")
            f.write(json.dumps(vapi_payload, indent=2))
        
        # Extract data from Vapi's structure
        tool_call_list = vapi_payload.get("message", {}).get("toolCallList", [])
        if not tool_call_list:
            return _format_response("Invalid request format", "unknown", is_error=True)
        
        # Get the first tool call
        tool_call = tool_call_list[0]
        tool_call_id = tool_call.get("id", "unknown")
        
        # Extract arguments - Vapi puts them inside 'function'
        function_data = tool_call.get("function", {})
        arguments = function_data.get("arguments", {})
        
        # Fallback: check if arguments are at root (some Vapi versions)
        if not arguments:
            arguments = tool_call.get("arguments", {})
        
        # Extract parameters
        date = arguments.get("date")
        query_type = arguments.get("query_type", "single")
        
        print(f"Extracted - toolCallId: {tool_call_id}, date: {date}, query_type: {query_type}")
        
    except Exception as e:
        print(f"Error parsing Vapi request: {e}")
        return _format_response("Failed to parse request", "unknown", is_error=True)

    global gcal_service
    if not gcal_service:
        return _format_response("System error: Calendar service not available.", tool_call_id)

    print(f"Checking availability for: {date}")

    # 0. Handle Missing Date
    if not date:
        return _format_response("I didn't catch the date. When would you like the appointment?", tool_call_id)

    # 1. Parse Date
    try:
        parse_result = parse_relative_date(date)
        
        if not parse_result.success:
            print(f"   Date parse error: {parse_result.error}")
            return _format_response(parse_result.error, tool_call_id)
            
        target_date_str = parse_result.date
        print(f"   Parsed date: {target_date_str}")
        
        target_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()
        
    except Exception as e:
        print(f"   Parse exception: {e}")
        return _format_response("I didn't understand that date. Could you confirm it again?", tool_call_id)

    # 1.5 Validate date is not in the past (#8)
    if target_date < datetime.date.today():
        return _format_response(
            "That date has already passed. Would you like to book for a future date?", 
            tool_call_id
        )

    # 2. Fetch Busy Events
    try:
        fetch_start = target_date
        fetch_end = target_date + datetime.timedelta(days=7)
        busy_events = gcal_service.get_busy_events(fetch_start, fetch_end)
        print(f"   Found {len(busy_events)} busy events in next 7 days")
        
    except Exception as e:
        print(f"   GCal exception: {e}")
        return _format_response("I'm having trouble checking the calendar right now.", tool_call_id)

    # 3. Calculate Slots
    try:
        tz = pytz.timezone(TIMEZONE)
        now_dt = datetime.datetime.now(tz)
        
        if query_type == "range":
            rolling_result = get_rolling_availability(
                start_date=target_date,
                busy_events_by_date=_group_busy_by_date(busy_events),
                days=7,
                now=now_dt
            )
            response_text = format_availability_for_voice(rolling_result)
            
        else:
            busy_on_day = [e for e in busy_events if e['start'].date() == target_date]
            day_result = calculate_free_slots(
                target_date=target_date,
                busy_events=busy_on_day,
                now=now_dt
            )
            
            if not day_result.slots and not day_result.is_closed:
                print("   No slots on target day. Checking rolling availability...")
                rolling_result = get_rolling_availability(
                    start_date=target_date,
                    busy_events_by_date=_group_busy_by_date(busy_events),
                    days=7,
                    now=now_dt
                )
                response_text = f"I don't have any openings on {day_result.day_name}. " + \
                                format_availability_for_voice(rolling_result)
            else:
                response_text = format_availability_for_voice(day_result.to_dict())

        print(f"   Response: {response_text[:100]}...")
        return _format_response(response_text, tool_call_id)

    except Exception as e:
        print(f"   Logic exception: {e}")
        import traceback
        traceback.print_exc()
        return _format_response("Sorry, I encountered an error calculating availability.", tool_call_id)


@app.post("/tools/savePatient")
async def save_patient(raw_request: Request):
    """
    Tool called by Vapi to save/update patient info.
    """
    # Get the full Vapi request
    try:
        vapi_payload = await raw_request.json()
        print(f"DEBUG: savePatient Payload: {vapi_payload}")

        # LOG TO FILE for persistent debugging
        with open("webhook_log.txt", "a") as f:
            import json
            f.write(f"\n\n--- savePatient REQUEST AT {datetime.datetime.now()} ---\n")
            f.write(json.dumps(vapi_payload, indent=2))

        # Extract data from Vapi's structure
        tool_call_list = vapi_payload.get("message", {}).get("toolCallList", [])
        if not tool_call_list:
             return _format_response("Invalid request format", "unknown", is_error=True)

        tool_call = tool_call_list[0]
        tool_call_id = tool_call.get("id", "unknown")
        
        # Extract arguments - Vapi puts them inside 'function'
        function_data = tool_call.get("function", {})
        arguments = function_data.get("arguments", {})
        
        # Fallback: check if arguments are at root
        if not arguments:
            arguments = tool_call.get("arguments", {})

        # Extract parameters
        name = arguments.get("name")
        phone_number = arguments.get("phone_number")
        date = arguments.get("date")
        time_str = arguments.get("time")
        email = arguments.get("email")
        vapi_call_id = arguments.get("vapi_call_id")
        
        print(f"Extracted - toolCallId: {tool_call_id}, Name: {name}, Phone: {phone_number}, Date: {date}, Time: {time_str}, Email: {email}")

    except Exception as e:
        print(f"Error parsing Vapi request: {e}")
        return _format_response("Failed to parse request", "unknown", is_error=True)

    global supabase_service, gcal_service
    if not supabase_service or not gcal_service:
        print("Services not available")
        return _format_response("System services unavailable", tool_call_id, is_error=True)

    # 1. BOOK APPOINTMENT IN GCAL
    try:
        # Parse Date
        parse_result = parse_relative_date(date)
        if not parse_result.success:
             return _format_response(f"Invalid date: {date}", tool_call_id, is_error=True)
        
        target_date_str = parse_result.date
        target_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()
        
        # Parse Time (Flexible formats: 4pm, 4:00 PM, 16:00)
        try:
            # Clean time string
            clean_time = time_str.lower().replace(" ", "").replace(".", "")
            # Simple manual parsing or dateparser? dateparser is safer for "4pm"
            import dateparser
            dt = dateparser.parse(f"{target_date_str} {time_str}")
            if not dt:
                 raise ValueError("Could not parse time")
            appt_datetime = dt
        except Exception as e:
            print(f"Time parse error: {e}")
            # FALLBACK (#3): Instead of rejecting, offer available slots
            try:
                busy_events = gcal_service.get_busy_events(target_date, target_date + datetime.timedelta(days=1))
                busy_on_day = [e for e in busy_events if e['start'].date() == target_date]
                from execution.slot_calculator import calculate_free_slots
                tz = pytz.timezone(TIMEZONE)
                now_dt = datetime.datetime.now(tz)
                day_result = calculate_free_slots(target_date=target_date, busy_events=busy_on_day, now=now_dt)
                
                if day_result.slots:
                    slots_text = ", ".join(day_result.slots[:5])  # Show first 5
                    return _format_response(
                        f"I couldn't catch the exact time. We have these slots available on {target_date}: {slots_text}. Which one works for you?",
                        tool_call_id
                    )
            except:
                pass  # If fallback also fails, use original error
                
            return _format_response(f"Invalid time format: {time_str}", tool_call_id, is_error=True)

        print(f"Booking for: {appt_datetime}")

        # Check if slot is still available (Double Booking Protection)
        if not gcal_service.is_slot_available(appt_datetime):
            return _format_response(
                "I'm sorry, but that time slot has just been taken. Please choose another time.", 
                tool_call_id
            )

        # Create Event
        # Description required by user: "appointment booked by aertz assistant"
        event = gcal_service.create_appointment(
            summary=name,
            start_time=appt_datetime,
            description="appointment booked by aertz assistant"
        )
        
        if not event:
             return _format_response("Failed to create calendar event", tool_call_id, is_error=True)
             
        print(f"   Event Created: {event.get('id')}")

    except Exception as e:
        print(f"   Booking exception: {e}")
        return _format_response("Failed to book appointment in calendar.", tool_call_id, is_error=True)


    # 2. SAVE TO SUPABASE (with rollback on failure - #1)
    print(f"Saving patient: {name}, {phone_number}")
    created_event_id = None  # Track for rollback

    try:
        # Create Patient with ALL fields
        patient = Patient(
            name=name,
            phone_number=phone_number,
            email=email,  # Extracted from request
            appointment_date=target_date_str,
            appointment_time=time_str,
            description="Booked via Voice Agent" # Standard description for DB
        )
        
        created_event_id = event.get('id')  # Save for potential rollback
        result = await supabase_service.upsert_patient(patient)
        print(f"   Saved successfully. ID: {result.get('id')}")
        
        msg = "Appointment confirmed and details saved."
        
        # 3. SEND EMAIL
        if email:
            try:
                from execution.email_service import send_confirmation_email
                email_success = send_confirmation_email(email, name, target_date_str, time_str)
                if email_success:
                    print("   Confirmation email sent.")
                else:
                    print("   Email sending failed (check server logs).")
            except Exception as e:
                print(f"   Email module error: {e}")
        
        return _format_response(msg, tool_call_id)
        
    except Exception as e:
        print(f"   Save exception: {e}")
        # ROLLBACK: Delete the calendar event we just created
        if created_event_id:
            try:
                gcal_service.delete_event(created_event_id)
                print(f"   Rolled back GCal event {created_event_id}")
            except Exception as rollback_error:
                print(f"   Rollback failed: {rollback_error}")
        return _format_response("Failed to save your appointment. Please try again.", tool_call_id, is_error=True)


@app.post("/tools/lookupAppointment")
async def lookup_appointment(raw_request: Request):
    """
    Tool to find an appointment details.
    """
    try:
        vapi_payload = await raw_request.json()
        
        # Log payload
        with open("webhook_log.txt", "a") as f:
            import json
            f.write(f"\n\n--- lookup REQUEST AT {datetime.datetime.now()} ---\n")
            f.write(json.dumps(vapi_payload, indent=2))

        # Parsing Logic
        tool_call_list = vapi_payload.get("message", {}).get("toolCallList", [])
        if not tool_call_list:
             return _format_response("Invalid request", "unknown", is_error=True)

        tool_call = tool_call_list[0]
        tool_call_id = tool_call.get("id", "unknown")
        
        args = tool_call.get("function", {}).get("arguments", {})
        if not args: args = tool_call.get("arguments", {})

        phone = args.get("phone_number")
        if not phone:
             return _format_response("I need your phone number to find the booking.", tool_call_id)

    except Exception as e:
        print(f"Parse Error: {e}")
        return _format_response("Error processing request", "unknown", is_error=True)

    global supabase_service
    
    # Check Supabase
    patient = await supabase_service.get_patient(phone)
    if not patient:
         return _format_response("I couldn't find any appointment with that phone number.", tool_call_id)
    
    # Found
    name = patient.get("name", "Unknown")
    date = patient.get("appointment_date", "Unknown Date")
    time = patient.get("appointment_time", "Unknown Time")
    
    return _format_response(
        f"I found an appointment for {name} on {date} at {time}. Would you like to cancel or reschedule this?", 
        tool_call_id
    )


@app.post("/tools/cancelAppointment")
async def cancel_appointment(raw_request: Request):
    """
    Tool to cancel an appointment.
    """
    try:
        vapi_payload = await raw_request.json()
        print(f"DEBUG: cancelPayload: {vapi_payload}")
        
        # Log payload
        with open("webhook_log.txt", "a") as f:
            import json
            f.write(f"\n\n--- cancel REQUEST AT {datetime.datetime.now()} ---\n")
            f.write(json.dumps(vapi_payload, indent=2))

        # Parsing Logic (Reuse manual parsing)
        tool_call_list = vapi_payload.get("message", {}).get("toolCallList", [])
        if not tool_call_list:
             return _format_response("Invalid request", "unknown", is_error=True)

        tool_call = tool_call_list[0]
        tool_call_id = tool_call.get("id", "unknown")
        
        args = tool_call.get("function", {}).get("arguments", {})
        if not args: args = tool_call.get("arguments", {})

        name = args.get("name")
        phone = args.get("phone_number")
        
        print(f"Cancel Request - Name: {name}, Phone: {phone}")

        if not phone:
             return _format_response("I need your phone number to find the booking.", tool_call_id)

    except Exception as e:
        print(f"Parse Error: {e}")
        return _format_response("Error processing request", "unknown", is_error=True)

    global supabase_service, gcal_service
    
    # 1. Check Supabase for record (Source of Truth)
    patient = await supabase_service.get_patient(phone)
    if not patient:
         return _format_response("I couldn't find an appointment linked to that phone number.", tool_call_id)
    
    email = patient.get("email")
    # stored_name = patient.get("name") # Use stored name for better GCal lookup?

    # 2. Delete from Supabase
    await supabase_service.delete_patient(phone)
    print(f"Deleted patient record for {phone}")

    # 3. Find and Delete GCal Event(s) - Loop to handle duplicates (#7)
    # We search by Name (as stored in Summary)
    deleted_count = 0
    while True:
        event = gcal_service.find_event(name) 
        if not event:
            # Retry with name from DB if different
            if deleted_count == 0 and patient.get("name") and patient.get("name") != name:
                 event = gcal_service.find_event(patient.get("name"))
                 if not event:
                     break
            else:
                break

        gcal_service.delete_event(event['id'])
        deleted_count += 1
        print(f"Deleted GCal event {event['id']} ({deleted_count} total)")
    
    if deleted_count == 0:
        print("Warning: GCal event not found for deletion")
    else:
        print(f"Successfully deleted {deleted_count} calendar event(s)")

    # 4. Send Cancellation Email
    if email:
        try:
            from execution.email_service import send_cancellation_email
            send_cancellation_email(email, name)
        except Exception as e:
            print(f"Email error: {e}")

    return _format_response("Your appointment has been cancelled. I've sent a confirmation to your email.", tool_call_id)


def _format_response(result_text: str, tool_call_id: Optional[str], is_error: bool = False):
    """Formats response for Vapi Tools."""
    if tool_call_id:
        # Vapi Tool Format
        return {
            "results": [
                {
                    "toolCallId": tool_call_id,
                    "result": result_text if not is_error else f"Error: {result_text}"
                }
            ]
        }
    else:
        # Backward compatibility / Simple API
        if is_error:
            return {"error": result_text}
        return {"result": result_text}


def _group_busy_by_date(busy_events: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Helper to group busy events by 'YYYY-MM-DD' key."""
    grouped = {}
    for event in busy_events:
        d = event['start'].date().strftime('%Y-%m-%d')
        if d not in grouped:
            grouped[d] = []
        grouped[d].append(event)
    return grouped

if __name__ == "__main__":
    uvicorn.run("execution.server:app", host="0.0.0.0", port=8000, reload=True)

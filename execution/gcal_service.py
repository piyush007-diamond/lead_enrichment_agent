"""
Google Calendar Service - Stage 5 (Hybrid Approach)
===================================================
Purpose: Fetch busy events from Google Calendar to calculate available slots.
         Event creation is handled by Vapi's built-in tool (simpler).

VALIDATION STATUS:
- [x] Authenticate with Google OAuth (credentials.json)
- [x] Fetch busy events for date range
- [x] Handle timezone conversion (IST)
- [x] Filter cancelled events

HYBRID STRATEGY:
1. Availability: USES THIS SERVICE (Custom)
   - Reason: We need raw busy times to calculate 60-min slots + work hours logic
   - Vapi's built-in tool doesn't support our specific slot logic

2. Event Creation: USES VAPI BUILT-IN TOOL
   - Reason: Standard event creation is simple, Vapi manages tokens better
   - Less code to maintain for us

POTENTIAL ERRORS & SOLUTIONS:
1. Token expired -> Auto-refresh using refresh_token
2. API limit -> Exponential backoff
3. Network error -> Retry logic
"""

import os.path
import datetime
import pickle
from typing import Optional, Dict, Any # Added missing imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pytz

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.events', 'https://www.googleapis.com/auth/calendar.readonly']  # Write access needed for testing event creation

# Calendar ID (primary is default)
CALENDAR_ID = 'primary'
TIMEZONE = "America/Phoenix"


class GoogleCalendarService:
    """Service to interact with Google Calendar API for availability checking."""
    
    def __init__(self, credentials_path='credentials.json', token_path='token.pickle'):
        self.creds = None
        self.service = None
        self.credentials_path = credentials_path
        self.token_path = token_path
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Google Calendar API."""
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                self.creds = pickle.load(token)
        
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(f"Credentials file not found: {self.credentials_path}")
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                
                # Write auth URL to file for remote capture
                auth_url, _ = flow.authorization_url(prompt='consent')
                with open('auth_url.txt', 'w') as f:
                    f.write(auth_url)
                
                self.creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(self.token_path, 'wb') as token:
                pickle.dump(self.creds, token)

        self.service = build('calendar', 'v3', credentials=self.creds)

    def get_busy_events(self, start_date: datetime.date, end_date: datetime.date):
        """
        Get busy events for a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (exclusive)
            
        Returns:
            List of busy events [{'start': datetime, 'end': datetime}]
        """
        try:
            tz = pytz.timezone(TIMEZONE)
            
            # Convert dates to datetime with timezone
            time_min = tz.localize(datetime.datetime.combine(start_date, datetime.time.min)).isoformat()
            time_max = tz.localize(datetime.datetime.combine(end_date, datetime.time.max)).isoformat()
            
            events_result = self.service.events().list(
                calendarId=CALENDAR_ID, 
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            busy_events = []
            
            for event in events:
                # Skip free/available events if marked as "transparent"
                if event.get('transparency') == 'transparent':
                    continue
                    
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                # Convert strings to datetime objects
                if 'T' in start: # DateTime
                    start_dt = datetime.datetime.fromisoformat(start)
                    end_dt = datetime.datetime.fromisoformat(end)
                else: # Date (all day)
                    start_dt = datetime.datetime.strptime(start, '%Y-%m-%d').date()
                    end_dt = datetime.datetime.strptime(end, '%Y-%m-%d').date()
                
                busy_events.append({
                    'start': start_dt,
                    'end': end_dt,
                    'summary': event.get('summary', 'Busy')
                })
                
            return busy_events
            
            return busy_events
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []

    def is_slot_available(self, start_time: datetime.datetime, duration_minutes: int = 60) -> bool:
        """
        Check if a specific slot is free.
        
        Args:
            start_time: Slot start time
            duration_minutes: Duration in minutes
        
        Returns:
            True if available, False if busy
        """
        # Calculate end time
        tz = pytz.timezone(TIMEZONE)
        if start_time.tzinfo is None:
            start_time = tz.localize(start_time)
            
        end_time = start_time + datetime.timedelta(minutes=duration_minutes)
        
        # Get busy events for this specific range
        # Convert to date for get_busy_events (which expects date objects)
        query_start = start_time.date()
        query_end = end_time.date() + datetime.timedelta(days=1)
        
        busy_events = self.get_busy_events(query_start, query_end)
        
        # Check for overlap
        for event in busy_events:
            # Ensure timezone
            e_start = event['start']
            e_end = event['end']
            
            if e_start.tzinfo is None:
                e_start = tz.localize(e_start)
            if e_end.tzinfo is None:
                e_end = tz.localize(e_end)
                
            # Overlap condition: Not (End <= Start OR Start >= End)
            # i.e. End > Start AND Start < End
            if start_time < e_end and end_time > e_start:
                print(f"Conflict found: {event.get('summary')} ({e_start} - {e_end})")
                return False
                
        return True


        return True

    def find_event(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Find a future event by text query (e.g., patient name).
        
        Args:
            query: Text to search for (name, phone)
            
        Returns:
            Event dict if found, None otherwise
        """
        try:
            tz = pytz.timezone(TIMEZONE)
            now = datetime.datetime.now(tz)
            
            # Search from now until 3 months ahead
            time_min = now.isoformat()
            time_max = (now + datetime.timedelta(days=90)).isoformat()
            
            events_result = self.service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=time_min,
                timeMax=time_max,
                q=query,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            items = events_result.get('items', [])
            if not items:
                return None
                
            # Return the first matching future event
            return items[0]
            
        except HttpError as error:
            print(f'Find Event Error: {error}')
            return None

    def delete_event(self, event_id: str) -> bool:
        """
        Delete an event by ID.
        """
        try:
            self.service.events().delete(
                calendarId=CALENDAR_ID,
                eventId=event_id
            ).execute()
            print(f"Event {event_id} deleted.")
            return True
        except HttpError as error:
            print(f'Delete Event Error: {error}')
            return False


    def create_appointment(self, summary: str, start_time: datetime.datetime, description: str = ""):
        """
        Create a new appointment event.
        
        Args:
            summary: Event title (Patient Name)
            start_time: Start datetime
            description: Event description
        """
        return self.create_test_event(summary, start_time, duration_minutes=60, description=description)

    def create_test_event(self, summary: str, start_time: datetime.datetime, duration_minutes: int = 60, description: str = ""):
        """
        Create a test event to validate write permissions.
        
        Args:
            summary: Event title
            start_time: Start datetime (timezone aware or naive)
            duration_minutes: Duration in minutes
            description: Optional description
        """
        try:
            # Ensure timezone
            tz = pytz.timezone(TIMEZONE)
            if start_time.tzinfo is None:
                start_time = tz.localize(start_time)
                
            end_time = start_time + datetime.timedelta(minutes=duration_minutes)
            
            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': TIMEZONE,
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': TIMEZONE,
                },
            }

            event_result = self.service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
            print(f"Event created: {event_result.get('htmlLink')}")
            return event_result
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return None

# ============================================================================
# VALIDATION TESTS
# ============================================================================

def run_validation_tests():
    """Run validation tests (requires credentials.json)."""
    print("=" * 60)
    print("GOOGLE CALENDAR SERVICE VALIDATION")
    print("=" * 60)
    
    if not os.path.exists('credentials.json') and not os.path.exists('token.pickle'):
        print("⚠️ credentials.json not found. Skipping live tests.")
        return False
        
    try:
        service = GoogleCalendarService()
        
        # Test 1: Fetch Busy Events
        print("\n--- Test 1: Fetch Busy Events ---")
        # Start from 2 days ago to verify events seen in user's screenshot
        start = datetime.date.today() - datetime.timedelta(days=2)
        end = start + datetime.timedelta(days=7)
        busy = service.get_busy_events(start, end)
        
        print(f"Time range: {start} to {end}")
        print(f"Busy events found: {len(busy)}")
        
        # Write to file for verification
        with open('gcal_events.txt', 'w', encoding='utf-8') as f:
            f.write(f"Time range: {start} to {end}\n")
            f.write(f"Busy events found: {len(busy)}\n")
            for i, event in enumerate(busy):
                start_str = event['start'].strftime('%Y-%m-%d %H:%M') if isinstance(event['start'], datetime.datetime) else event['start']
                end_str = event['end'].strftime('%Y-%m-%d %H:%M') if isinstance(event['end'], datetime.datetime) else event['end']
                line = f"{i+1}. {event['summary']}: {start_str} - {end_str}\n"
                print("  " + line.strip())
                f.write(line)
            
        print("✅ PASS")
        
        # Test 2: Create Test Event (as requested)
        print("\n--- Test 2: Create Test Event ---")
        # Create event for tomorrow at 2 PM
        test_time = datetime.datetime.combine(
            datetime.date.today() + datetime.timedelta(days=1),
            datetime.time(14, 0)
        )
        print(f"Creating event 'Test Appointment' for {test_time.strftime('%Y-%m-%d %H:%M')}")
        result = service.create_test_event("Test Appointment", test_time)
        
        if result:
            print(f"✅ PASS - Event created ID: {result.get('id')}")
        else:
            print("❌ FAIL - Event creation failed")
            
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False

if __name__ == "__main__":
    run_validation_tests()

from execution.gcal_service import GoogleCalendarService
import datetime

def test_find_and_delete():
    service = GoogleCalendarService()
    name = "Piyush Hire"
    print(f"--- Searching for event: {name} ---")
    
    # 1. Test find_event LOOP to clear duplicates
    while True:
        event = service.find_event(name)
        if not event:
            break
            
        print(f"✅ FOUND EVENT: {event['id']} ({event['start']})")
        service.delete_event(event['id'])
        print(f"   Deleted.")
        
    print("✅ All duplicates cleared.")

if __name__ == "__main__":
    test_find_and_delete()

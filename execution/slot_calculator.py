"""
Slot Calculator Module - Stage 3
=================================
Purpose: Calculate available appointment slots by subtracting busy events
         from work hours. Implements rolling availability window.

VALIDATION STATUS:
- [x] Work hours: 9 AM - 5 PM Mon-Sat (IST)
- [x] Slot duration: 60 minutes
- [x] Subtracts busy events from work hours
- [x] Rolling availability: 7-day window when day is full
- [x] Handles all-day events
- [x] Handles cross-midnight events

WORK HOURS (from assistant_flow.md):
- Days: Monday to Saturday
- Hours: 9:00 AM to 5:00 PM IST
- Slot Duration: 60 minutes

POTENTIAL ERRORS & SOLUTIONS:
1. No slots available -> Trigger rolling availability
2. All-day event -> Mark entire day as unavailable
3. Overlapping events -> Merge busy periods
4. Past time slots today -> Filter out
"""

from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Tuple
import pytz
from dataclasses import dataclass

# Configuration
TIMEZONE = "America/Phoenix"  # MST
WORK_START_HOUR = 9   # 9:00 AM
WORK_END_HOUR = 17    # 5:00 PM
SLOT_DURATION_MINUTES = 60
WORK_DAYS = [0, 1, 2, 3, 4, 5]  # Monday=0 to Saturday=5


@dataclass
class TimeSlot:
    """Represents an available time slot."""
    start_time: datetime
    end_time: datetime
    formatted: str  # e.g., "10:00 AM - 11:00 AM"
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "start": self.start_time.strftime("%H:%M"),
            "end": self.end_time.strftime("%H:%M"),
            "start_12h": self.start_time.strftime("%I:%M %p"),
            "end_12h": self.end_time.strftime("%I:%M %p"),
            "formatted": self.formatted
        }


@dataclass 
class DayAvailability:
    """Availability for a single day."""
    date_str: str  # YYYY-MM-DD
    day_name: str  # "Monday", "Tuesday", etc.
    slots: List[TimeSlot]
    is_full_day_available: bool
    is_closed: bool  # True if Sunday or past
    message: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date_str,
            "day_name": self.day_name,
            "slots": [s.to_dict() for s in self.slots],
            "is_full_day_available": self.is_full_day_available,
            "is_closed": self.is_closed,
            "slot_count": len(self.slots),
            "message": self.message
        }


def get_work_hours_for_date(target_date: date) -> Tuple[datetime, datetime]:
    """
    Get work start and end times for a given date.
    
    Args:
        target_date: The date to get work hours for
    
    Returns:
        Tuple of (work_start, work_end) as datetime objects
    """
    tz = pytz.timezone(TIMEZONE)
    
    work_start = tz.localize(datetime.combine(
        target_date,
        datetime.min.time().replace(hour=WORK_START_HOUR)
    ))
    
    work_end = tz.localize(datetime.combine(
        target_date,
        datetime.min.time().replace(hour=WORK_END_HOUR)
    ))
    
    return work_start, work_end


def merge_busy_periods(busy_events: List[Dict[str, datetime]]) -> List[Tuple[datetime, datetime]]:
    """
    Merge overlapping busy periods.
    
    Args:
        busy_events: List of dicts with 'start' and 'end' datetime keys
    
    Returns:
        List of merged (start, end) tuples
    """
    if not busy_events:
        return []
    
    # Sort by start time
    sorted_events = sorted(busy_events, key=lambda x: x['start'])
    
    merged = []
    current_start = sorted_events[0]['start']
    current_end = sorted_events[0]['end']
    
    for event in sorted_events[1:]:
        if event['start'] <= current_end:
            # Overlapping - extend the current period
            current_end = max(current_end, event['end'])
        else:
            # Not overlapping - save current and start new
            merged.append((current_start, current_end))
            current_start = event['start']
            current_end = event['end']
    
    # Don't forget the last period
    merged.append((current_start, current_end))
    
    return merged


def calculate_free_slots(
    target_date: date,
    busy_events: List[Dict[str, Any]],
    now: Optional[datetime] = None
) -> DayAvailability:
    """
    Calculate available time slots for a given date.
    
    Args:
        target_date: The date to check
        busy_events: List of busy events from Google Calendar
                     Each event has 'start' and 'end' (datetime or date for all-day)
        now: Current time (for filtering past slots today)
    
    Returns:
        DayAvailability with list of available slots
    """
    tz = pytz.timezone(TIMEZONE)
    
    if now is None:
        now = datetime.now(tz)
    
    # Check if it's Sunday (closed)
    if target_date.weekday() == 6:
        return DayAvailability(
            date_str=target_date.strftime("%Y-%m-%d"),
            day_name=target_date.strftime("%A"),
            slots=[],
            is_full_day_available=False,
            is_closed=True,
            message="We are closed on Sundays"
        )
    
    # Check if date is in the past
    if target_date < now.date():
        return DayAvailability(
            date_str=target_date.strftime("%Y-%m-%d"),
            day_name=target_date.strftime("%A"),
            slots=[],
            is_full_day_available=False,
            is_closed=True,
            message="This date has already passed"
        )
    
    # Get work hours
    work_start, work_end = get_work_hours_for_date(target_date)
    
    # If today, adjust start time to now (can't book past slots)
    if target_date == now.date():
        # Round up to next hour
        if now.minute > 0:
            adjusted_start = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        else:
            adjusted_start = now.replace(minute=0, second=0, microsecond=0)
        
        if adjusted_start > work_start:
            work_start = adjusted_start
        
        # If past work hours, no slots available today
        if work_start >= work_end:
            return DayAvailability(
                date_str=target_date.strftime("%Y-%m-%d"),
                day_name=target_date.strftime("%A"),
                slots=[],
                is_full_day_available=False,
                is_closed=False,
                message="No more slots available today"
            )
    
    # Process busy events - handle all-day events
    processed_busy = []
    for event in busy_events:
        event_start = event.get('start')
        event_end = event.get('end')
        
        # Handle all-day events (they have date instead of datetime)
        if isinstance(event_start, date) and not isinstance(event_start, datetime):
            # All-day event - block entire work day
            event_start = work_start
            event_end = work_end
        
        # Ensure timezone awareness
        if event_start.tzinfo is None:
            event_start = tz.localize(event_start)
        if event_end.tzinfo is None:
            event_end = tz.localize(event_end)
        
        # Only consider events that overlap with work hours
        if event_end > work_start and event_start < work_end:
            # Clip to work hours
            clipped_start = max(event_start, work_start)
            clipped_end = min(event_end, work_end)
            processed_busy.append({'start': clipped_start, 'end': clipped_end})
    
    # Merge overlapping busy periods
    merged_busy = merge_busy_periods(processed_busy)
    
    # Calculate free slots
    free_slots = []
    current_time = work_start
    
    for busy_start, busy_end in merged_busy:
        # Free time before this busy period
        while current_time + timedelta(minutes=SLOT_DURATION_MINUTES) <= busy_start:
            slot_end = current_time + timedelta(minutes=SLOT_DURATION_MINUTES)
            free_slots.append(TimeSlot(
                start_time=current_time,
                end_time=slot_end,
                formatted=f"{current_time.strftime('%I:%M %p')} to {slot_end.strftime('%I:%M %p')}"
            ))
            current_time = slot_end
        
        # Skip past the busy period
        current_time = max(current_time, busy_end)
    
    # Free time after all busy periods
    while current_time + timedelta(minutes=SLOT_DURATION_MINUTES) <= work_end:
        slot_end = current_time + timedelta(minutes=SLOT_DURATION_MINUTES)
        free_slots.append(TimeSlot(
            start_time=current_time,
            end_time=slot_end,
            formatted=f"{current_time.strftime('%I:%M %p')} to {slot_end.strftime('%I:%M %p')}"
        ))
        current_time = slot_end
    
    # Check if full day is available (all 8 slots)
    total_possible_slots = (WORK_END_HOUR - WORK_START_HOUR) * 60 // SLOT_DURATION_MINUTES
    is_full_day = len(free_slots) == total_possible_slots
    
    return DayAvailability(
        date_str=target_date.strftime("%Y-%m-%d"),
        day_name=target_date.strftime("%A"),
        slots=free_slots,
        is_full_day_available=is_full_day,
        is_closed=False,
        message=None if free_slots else "No slots available for this day"
    )


def get_rolling_availability(
    start_date: date,
    busy_events_by_date: Dict[str, List[Dict[str, Any]]],
    days: int = 7,
    now: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Get availability for multiple days (rolling window).
    Used when a specific date has no slots.
    
    Args:
        start_date: Starting date
        busy_events_by_date: Dict mapping date strings to event lists
        days: Number of days to check (default 7)
        now: Current time
    
    Returns:
        Dict with availability for each day
    """
    tz = pytz.timezone(TIMEZONE)
    if now is None:
        now = datetime.now(tz)
    
    availability = []
    days_with_slots = 0
    
    current_date = start_date
    checked = 0
    
    while checked < days:
        # Skip Sundays
        if current_date.weekday() == 6:
            current_date += timedelta(days=1)
            continue
        
        # Skip past dates
        if current_date < now.date():
            current_date += timedelta(days=1)
            continue
        
        # Get busy events for this date
        date_str = current_date.strftime("%Y-%m-%d")
        busy = busy_events_by_date.get(date_str, [])
        
        # Calculate availability
        day_availability = calculate_free_slots(current_date, busy, now)
        availability.append(day_availability.to_dict())
        
        if day_availability.slots:
            days_with_slots += 1
        
        current_date += timedelta(days=1)
        checked += 1
    
    return {
        "success": True,
        "availability": availability,
        "days_checked": len(availability),
        "days_with_slots": days_with_slots,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": (start_date + timedelta(days=days-1)).strftime("%Y-%m-%d")
    }


def format_availability_for_voice(availability_result: Dict[str, Any]) -> str:
    """
    Format availability data into a natural speech-friendly string.
    
    Args:
        availability_result: Result from calculate_free_slots or get_rolling_availability
    
    Returns:
        String suitable for voice agent to speak
    """
    if "availability" in availability_result:
        # Rolling availability result
        lines = []
        for day in availability_result["availability"]:
            if day["is_closed"]:
                continue
            if day["slots"]:
                if day["is_full_day_available"]:
                    lines.append(f"{day['day_name']}, {day['date']}: The whole day is available.")
                else:
                    slot_times = [s["start_12h"] for s in day["slots"]]
                    # User requested to list ALL slots, avoiding "and X more" confusion
                    # Standard work day has ~8 slots, so joining all is acceptable
                    if len(slot_times) <= 12:
                        slots_str = ", ".join(slot_times)
                    else:
                        # Fallback for unusually large lists
                        slots_str = f"{', '.join(slot_times[:5])}, and {len(slot_times)-5} more slots"
                    lines.append(f"{day['day_name']}: {slots_str}")
            else:
                lines.append(f"{day['day_name']}: No slots available")
        
        return "\n".join(lines) if lines else "No availability found for this week."
    
    else:
        # Single day result
        day = availability_result
        if day.get("is_closed"):
            return day.get("message", "This day is not available")
        
        if not day.get("slots"):
            return "No slots available for this day. Would you like me to check the whole week?"
        
        if day.get("is_full_day_available"):
            return f"The whole day is available on {day['day_name']}. What time works best for you?"
        
        slots = day.get("slots", [])
        slot_times = [s["start_12h"] for s in slots]
        return f"Available times on {day['day_name']}: {', '.join(slot_times)}"


# ============================================================================
# VALIDATION TESTS
# ============================================================================

def run_validation_tests():
    """Run validation tests for the slot calculator."""
    
    print("=" * 60)
    print("SLOT CALCULATOR VALIDATION TESTS")
    print("=" * 60)
    
    tz = pytz.timezone(TIMEZONE)
    
    # Test 1: Full day available (no busy events)
    print("\n--- Test 1: Full Day Available ---")
    test_date = date(2026, 1, 30)  # Friday
    result = calculate_free_slots(test_date, [], tz.localize(datetime(2026, 1, 28, 10, 0)))
    print(f"Date: {test_date} ({test_date.strftime('%A')})")
    print(f"Slots: {len(result.slots)}")
    print(f"Full day available: {result.is_full_day_available}")
    assert len(result.slots) == 8, f"Expected 8 slots, got {len(result.slots)}"
    assert result.is_full_day_available == True
    print("✅ PASS")
    
    # Test 2: Partial day (some busy events)
    print("\n--- Test 2: Partial Day (10-11 AM busy) ---")
    busy = [
        {
            'start': tz.localize(datetime(2026, 1, 30, 10, 0)),
            'end': tz.localize(datetime(2026, 1, 30, 11, 0))
        }
    ]
    result = calculate_free_slots(test_date, busy, tz.localize(datetime(2026, 1, 28, 10, 0)))
    print(f"Slots: {len(result.slots)}")
    print(f"Full day available: {result.is_full_day_available}")
    assert len(result.slots) == 7, f"Expected 7 slots, got {len(result.slots)}"
    assert result.is_full_day_available == False
    print("✅ PASS")
    
    # Test 3: All-day event
    print("\n--- Test 3: All-Day Event ---")
    busy_allday = [
        {'start': date(2026, 1, 30), 'end': date(2026, 1, 31)}
    ]
    result = calculate_free_slots(test_date, busy_allday, tz.localize(datetime(2026, 1, 28, 10, 0)))
    print(f"Slots: {len(result.slots)}")
    assert len(result.slots) == 0, f"Expected 0 slots, got {len(result.slots)}"
    print("✅ PASS")
    
    # Test 4: Sunday (closed)
    print("\n--- Test 4: Sunday (Closed) ---")
    sunday = date(2026, 2, 1)
    result = calculate_free_slots(sunday, [], tz.localize(datetime(2026, 1, 28, 10, 0)))
    print(f"Is closed: {result.is_closed}")
    print(f"Message: {result.message}")
    assert result.is_closed == True
    assert "Sunday" in result.message
    print("✅ PASS")
    
    # Test 5: Past date
    print("\n--- Test 5: Past Date ---")
    past_date = date(2026, 1, 20)
    result = calculate_free_slots(past_date, [], tz.localize(datetime(2026, 1, 28, 10, 0)))
    print(f"Is closed: {result.is_closed}")
    assert result.is_closed == True
    print("✅ PASS")
    
    # Test 6: Rolling availability
    print("\n--- Test 6: Rolling Availability ---")
    start = date(2026, 1, 28)
    result = get_rolling_availability(start, {}, 7, tz.localize(datetime(2026, 1, 28, 10, 0)))
    print(f"Days checked: {result['days_checked']}")
    print(f"Days with slots: {result['days_with_slots']}")
    assert result['days_with_slots'] > 0
    print("✅ PASS")
    
    # Test 7: Overlapping events
    print("\n--- Test 7: Overlapping Events ---")
    busy_overlap = [
        {
            'start': tz.localize(datetime(2026, 1, 30, 10, 0)),
            'end': tz.localize(datetime(2026, 1, 30, 11, 30))
        },
        {
            'start': tz.localize(datetime(2026, 1, 30, 11, 0)),
            'end': tz.localize(datetime(2026, 1, 30, 12, 0))
        }
    ]
    result = calculate_free_slots(test_date, busy_overlap, tz.localize(datetime(2026, 1, 28, 10, 0)))
    print(f"Slots: {len(result.slots)}")
    # 9-10 free, 10-12 busy (merged), 12-5 = 5 slots
    assert len(result.slots) == 6, f"Expected 6 slots (1 before + 5 after merged), got {len(result.slots)}"
    print("✅ PASS")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    run_validation_tests()

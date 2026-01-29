# Slot Calculation logic

## System Context (Brain)
This skill is the "Scheduler Brain". Raw calendar data is just a list of "Busy" times. This skill turns that into actionable "Available Options" for the user.
It answers the question: "When can the doctor see me?"

### Rules
1.  **Operating Hours**: Monday-Saturday, 09:00 - 17:00 (5 PM). Sunday Closed.
2.  **Slot Duration**: All appointments are fixed at 60 minutes.
3.  **Conflict Resolution**: A slot is valid ONLY if it:
    -   Starts within operating hours.
    -   Ends within operating hours.
    -   Does NOT overlap with *any* busy event.
    -   Is in the future (relative to Now).

## Tools & Scripts
-   `execution/slot_calculator.py`: The calculation engine.
    -   `calculate_available_slots(busy_events, date, work_hours)`: The core algorithm.
    -   `format_time_for_speech(dt)`: Converts `13:00` -> "1:00 PM" for Vapi speech.

## Interconnections
-   **Inputs**:
    -   `busy_events` from `CALENDAR_MANAGEMENT`.
    -   `target_date` from `DATE_TIME_PROCESSING`.
-   **Outputs**: List of string slots ("9:00 AM", "10:00 AM"...) passed to `VOICE_INTEGRATION` to be spoken.
-   **Complexity**: Handles multi-day slot generation ("What about options for this week?").

## Output Contract
-   **List of Strings**: Human-readable times.
-   **Empty List**: Means "No slots available". The AI must then handle the fallback conversation ("I'm sorry, we are fully booked...").

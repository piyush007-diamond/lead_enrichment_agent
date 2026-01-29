# Calendar Management (Google Calendar)

## System Context (Brain)
This skill manages the "Time" and "Schedule" of the hospital. It interacts with the Google Calendar API to read busy times and manage appointment events.

### Rules
1.  **Hybrid Approach**:
    -   **Availability**: Calculated by US (fetching busy events + custom logic) to support 60-min slots + operating hours.
    -   **Booking**: Handled by US (via API) to ensure metadata consistency (using standard "Patient Name - Phone" format).
2.  **Timezone**: Strictly `America/Phoenix` (as configured). All inputs/outputs must be converted to this zone.
3.  **Duplicate Protection**: Before booking, we check if the slot is still free (`is_slot_available`).

## Tools & Scripts
-   `execution/gcal_service.py`: The service class.
    -   `get_busy_events(start, end)`: Returns raw busy blocks.
    -   `is_slot_available(time)`: Returns True/False.
    -   `find_event(name)`: Searches for existing bookings.
    -   `delete_event(id)`: Removes booking.
-   `credentials.json` & `token.pickle`: Auth artifacts.

## Interconnections
-   **Dependencies**: `DATE_TIME_PROCESSING` (for timezone aware datetime objects).
-   **Called By**: `SLOT_CALCULATION` (to get busy times), `VOICE_INTEGRATION` (server.py - to delete events).
-   **Affects**: The real-world doctor's schedule.

## Output Contract
-   **Availability**: Returns list of `{start, end, summary}` logic blocks.
-   **Actions**: Physically creates/deletes events on the `primary` calendar.
-   **Safety**: Validates that a slot isn't double-booked before confirming.

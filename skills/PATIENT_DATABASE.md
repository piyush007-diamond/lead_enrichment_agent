# Patient Database (Supabase)

## System Context (Brain)
This skill manages the "Memory" of the hospital. It persists patient details and appointment meta-data.
Crucially, it acts as the **Source of Truth** for cancellations and reschedules. The Calendar is just a display; the Database is the record.

### Rules
1.  **Unique Identifier**: The `phone_number` is the primary key for looking up patients.
2.  **Safety First**: All queries use `params` injection to prevent URL encoding errors (Cloudflare blocking).
3.  **Upsert Logic**: When booking, if a patient exists, we Update. If not, we Create. This prevents duplicates.

## Tools & Scripts
-   `execution/supabase_service.py`: The core service class.
    -   `get_patient(phone)`: Robust fuzzy search (matches last 10 digits).
    -   `upsert_patient(patient)`: Smart create/update logic.
    -   `delete_patient(phone)`: Removes record (for cancellations).
-   `debug_supabase.py`: Utility to manually verify DB state.

## Interconnections
-   **Dependencies**: Requires `httpx` and Supabase credentials (`.env`).
-   **Called By**: `VOICE_INTEGRATION` (server.py).
-   **Related To**: `CALENDAR_MANAGEMENT`. When we save a patient here, we usually also book a slot in the Calendar. They must stay in sync.

## Output Contract
-   **Data Structure**: Returns Patient Dict: `{'name': ..., 'phone_number': ..., 'appointment_date': ..., 'appointment_time': ...}`.
-   **Reliability**: Includes retry logic and robust searching (handles formatting differences in phone numbers).

# Date & Time Processing

## System Context (Brain)
This skill is the "Translator" for time. Humans speak in relative terms ("Next Friday", "Tomorrow afternoon"). Computers need ISO-8601 timestamps.
This skill bridges that gap.

### Rules
1.  **Reference Time**: Everything is relative to "Now" in `America/Phoenix` timezone.
2.  **Parsing Logic**:
    -   Handles explicit dates ("January 25th").
    -   Handles relative days ("this Friday", "next Tuesday").
    -   Handles times ("at 3 pm", "morning slots").
3.  **Fallback**: If parsing fails, it defaults to sensible guesses or returns `None` (prompting the AI to ask again).

## Tools & Scripts
-   `execution/date_parser.py`: The parsing engine.
    -   `parse_date(text)`: Returns `datetime.date`.
    -   `parse_time(text)`: Returns `datetime.time`.
    -   `get_next_date_for_day(day_name)`: Logic for "Next Friday".

## Interconnections
-   **Called By**: `VOICE_INTEGRATION` (server.py) when extracting arguments from user speech.
-   **Feeds Into**: `CALENDAR_MANAGEMENT` (to query range) and `SLOT_CALCULATION` (to filter specific days).

## Output Contract
-   **ISO Format**: `YYYY-MM-DD` and `HH:MM`.
-   **Timezone Aware**: All outputs are strict about timezone to prevent off-by-one errors in scheduling.

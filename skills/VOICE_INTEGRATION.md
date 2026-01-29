# Voice Integration (Vapi Interface)

## System Context (Brain)
This skill acts as the "Ears and Mouth" interface between the Vapi Cloud AI (Anjali) and our local backend logic.
Vapi handles the Speech-to-Text and Text-to-Speech. This skill handles the **Thinking** and **Doing**.

### Roles
-   **Webhook Receiver**: Listens for `/chat/completions` (LLM logic) or tool calls.
-   **Tool Dispatcher**: Routes requests like `checkAvailability` or `savePatient` to the correct internal service.
-   **Prompt Enforcer**: The `assistant_flow.md` defines the personality, but this skill enforces the *capabilities*.

## Tools & Scripts
-   `execution/server.py`: FastAPI application defining endpoints (`/tools/...`).
-   `execution/vapi_update_tools.py`: Script to sync tool definitions (JSON) to Vapi API.
-   `vapi_tools_config.json` (Internal): Defines the schemas (inputs/outputs) for each tool.
-   `assistant_flow.md`: The System Prompt (Personality & Rules).

## Interconnections
-   **Inbound**: Receives calls from `SYSTEM_LIFECYCLE` (via Zrok Tunnel).
-   **Outbound Dispatch**:
    -   `checkAvailability` -> calls `CALENDAR_MANAGEMENT` & `SLOT_CALCULATION`.
    -   `savePatient` / `reschedule` -> calls `SLOT_CALCULATION` (to verify) then `PATIENT_DATABASE` (to save) then `CALENDAR_MANAGEMENT` (to book).
    -   `lookupAppointment` -> calls `PATIENT_DATABASE`.
    -   `cancelAppointment` -> calls `PATIENT_DATABASE` (verify) -> `CALENDAR_MANAGEMENT` (delete) -> `PATIENT_DATABASE` (delete).

## Output Contract
-   **API Responses**: Must return strict JSON format expected by Vapi.
    -   `result`: The text/data the AI should see.
    -   `toolCallId`: To link the result to the request.
-   **Error Handling**: If a tool fails, it returns a polite error message ("I couldn't access the calendar...") rather than crashing, allowing the AI to recover conversationally.

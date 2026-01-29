# Intent Recognition

## System Context (Brain)
This skill is the "Classifier". It determines WHAT the user wants to do based on their text.
*Note: In production, Vapi's LLM usually determines intent by selecting the appropriate tool. This skill serves as a local fallback and logic validator.*

### Rules
1.  **Keyword Analysis**: Scans input for trigger words (`book`, `schedule`, `cancel`, `remove`).
2.  **Confidence Check**: Simple partial matching.
3.  **Scope**: Currently limited to:
    -   `book_appointment`
    -   `check_availability`
    -   `cancel_appointment`

## Tools & Scripts
-   `execution/intent_classifier.py`: The local classification engine.
    -   `classify_intent(text)`: Returns the string intent.

## Interconnections
-   **Called By**: `VOICE_INTEGRATION` (server.py) can use this to validate vague requests or for local testing (`manual_ngrok_test.py`).
-   **Obsoleted By**: Vapi's Tool Selection (which is smarter). This skill remains as a foundational backup.

## Output Contract
-   **Intent String**: e.g., `"book_appointment"`.
-   **None**: If no intent is clear.

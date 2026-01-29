# Communication Service (Email)

## System Context (Brain)
This skill is the "Voice" beyond the call. It sends physical confirmation (Emails) to the user.
This builds trust. A voice confirmation is good; a written receipt is better.

### Rules
1.  **Trigger**: Sent ONLY after a successful database transaction (Booking or Cancellation).
2.  **Protocol**: Uses Standard SMTP (Gmail).
3.  **Formatting**: HTML templates for professional appearance ("Balaji ENT & Eye Hospital").

## Tools & Scripts
-   `execution/email_service.py`: The mailer.
    -   `send_booking_confirmation(email, name, date, time)`
    -   `send_cancellation_email(email, name)`
-   `.env`: Contains `GMAIL_SENDER` and `GMAIL_PASSWORD`.

## Interconnections
-   **Called By**: `VOICE_INTEGRATION` (server.py) at the *very end* of the `savePatient` or `cancelAppointment` flow.
-   **Dependencies**: Requires valid network access to `smtp.gmail.com:587`.

## Output Contract
-   **Success**: Returns `True` (Email sent).
-   **Failure**: Returns `False` (Logs error, but does NOT fail the booking). *We don't block patient care just because email failed.*

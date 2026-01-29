"""
Email Service Module - Stage 8
==============================
Purpose: Send confirmation emails to patients after appointment booking.

VALIDATION STATUS:
- [ ] Send email via SMTP (Gmail)
- [ ] Handle connection errors
- [ ] Format email body

REQUIREMENTS:
- EMAIL_SENDER in .env
- EMAIL_PASSWORD in .env (App Password)
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

EMAIL_SENDER = os.getenv("GMAIL_SENDER")
# Remove spaces from app password if present
EMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD", "").replace(" ", "")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

def send_confirmation_email(to_email: str, name: str, date: str, time: str) -> bool:
    """
    Send an appointment confirmation email.
    
    Args:
        to_email: Recipient email address
        name: Patient name
        date: Appointment date (YYYY-MM-DD)
        time: Appointment time (e.g. 4:00 PM)
        
    Returns:
        True if successful, False otherwise
    """
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("❌ Email credentials missing in .env")
        return False

    try:
        # Create message
        msg = MIMEMultipart()
        msg["From"] = EMAIL_SENDER
        msg["To"] = to_email
        msg["Subject"] = "Appointment Confirmation - Balaji ENT & Eye Hospital"

        body = f"""
        <html>
          <body>
            <h2>Appointment Confirmed</h2>
            <p>Dear {name},</p>
            <p>Your appointment at <b>Balaji ENT & Eye Hospital</b> has been confirmed.</p>
            <ul>
                <li><b>Date:</b> {date}</li>
                <li><b>Time:</b> {time}</li>
            </ul>
            <p>Please arrive 10 minutes eary. Bring any previous reports.</p>
            <br>
            <p>Regards,<br>Balaji ENT Voice Agent</p>
          </body>
        </html>
        """
        msg.attach(MIMEText(body, "html"))

        # Send email
        print(f"Sending email to {to_email}...")
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
            
        print("✅ Email sent successfully")
        return True

    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

def send_cancellation_email(to_email: str, name: str) -> bool:
    """Send cancellation confirmation."""
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_SENDER
        msg["To"] = to_email
        msg["Subject"] = "Appointment Cancelled - Balaji ENT & Eye Hospital"

        body = f"""
        <html>
          <body>
            <h2>Appointment Cancelled</h2>
            <p>Dear {name},</p>
            <p>As per your request, your appointment at <b>Balaji ENT & Eye Hospital</b> has been cancelled.</p>
            <p>If you would like to reschedule, please call us again.</p>
            <br>
            <p>Regards,<br>Balaji ENT Voice Agent</p>
          </body>
        </html>
        """
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
            
        print("✅ Cancellation email sent")
        return True

    except Exception as e:
        print(f"❌ Failed to send cancellation email: {e}")
        return False

# Validation Test
if __name__ == "__main__":
    # Test if credentials exist
    if EMAIL_SENDER:
        print(f"Testing email from {EMAIL_SENDER}...")
        # send_confirmation_email(EMAIL_SENDER, "Test User", "2026-01-01", "10:00 AM")
    else:
        print("Please set EMAIL_SENDER and EMAIL_PASSWORD in .env")

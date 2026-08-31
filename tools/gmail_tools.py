import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from core.config import TOKEN_FILE, OAUTH_SCOPES
from core.db import record_event


def get_gmail_service():
    """Get authenticated Gmail API service instance."""
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError(
            f"OAuth token not found at {TOKEN_FILE}. Run google_auth.py first."
        )
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, OAUTH_SCOPES)
    return build("gmail", "v1", credentials=creds)


def send_email(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: str = ""
) -> Dict[str, Any]:
    """Send an email via Gmail API after human approval."""
    service = get_gmail_service()
    
    msg = MIMEMultipart("alternative")
    msg["To"] = to_email
    msg["Subject"] = subject
    
    # Text part
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    
    # HTML part if provided
    if body_html:
        msg.attach(MIMEText(body_html, "html", "utf-8"))
    else:
        # Generate basic HTML wrapper
        html_formatted = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; padding: 24px;">
                <h2 style="color: #1a73e8; margin-top: 0;">Agentic Learning Coach Nudge</h2>
                <div style="white-space: pre-line;">{body_text}</div>
                <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />
                <p style="font-size: 12px; color: #777;">Sent proactively by your Agentic Learning Coach with human oversight.</p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_formatted, "html", "utf-8"))

    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    sent = service.users().messages().send(
        userId="me",
        body={"raw": raw_message}
    ).execute()
    
    message_id = sent.get("id")
    record_event("email_sent", {
        "messageId": message_id,
        "to": to_email,
        "subject": subject
    })
    
    return {
        "status": "sent",
        "messageId": message_id,
        "threadId": sent.get("threadId"),
        "to": to_email,
        "subject": subject
    }

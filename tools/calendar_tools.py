import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from core.config import TOKEN_FILE, OAUTH_SCOPES
from core.db import record_event


def get_calendar_service():
    """Get authenticated Google Calendar API service instance."""
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError(
            f"OAuth token not found at {TOKEN_FILE}. Run google_auth.py first."
        )
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, OAUTH_SCOPES)
    return build("calendar", "v3", credentials=creds)


def create_revision_event(
    title: str,
    start_iso: str,
    duration_minutes: int = 45,
    description: str = "",
    calendar_id: str = "primary"
) -> Dict[str, Any]:
    """Create a revision block event in the user's primary Google Calendar."""
    service = get_calendar_service()
    
    # Parse start time
    start_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    event_body = {
        "summary": title,
        "description": description,
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 15},
                {"method": "email", "minutes": 60},
            ],
        },
        "colorId": "11", # Bold Red/Flamingo for high priority revision
    }

    created_event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
    event_id = created_event.get("id")
    event_link = created_event.get("htmlLink")

    # Audit log event
    record_event("calendar_event_created", {
        "eventId": event_id,
        "title": title,
        "start": start_iso,
        "duration": duration_minutes
    })

    return {
        "id": event_id,
        "htmlLink": event_link,
        "summary": title,
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "status": "confirmed"
    }


def list_upcoming_events(max_results: int = 10) -> List[Dict[str, Any]]:
    """List upcoming revision events from the user's primary Google Calendar."""
    service = get_calendar_service()
    now_iso = datetime.now(timezone.utc).isoformat()
    events_result = service.events().list(
        calendarId="primary",
        timeMin=now_iso,
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    return events_result.get("items", [])

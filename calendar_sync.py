"""
Google Calendar sync — auto-creates deadline events with reminders.

Uses a free Google Cloud service account (no billing needed for Calendar API
at this volume). The service account can't own a personal calendar, so you
share one of YOUR calendars with the service account's email address instead
(see README section 4). Fully free either way.
"""

import json
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]

GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
GOOGLE_CALENDAR_ID = os.environ.get("GOOGLE_CALENDAR_ID")


def get_service():
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        return None
    info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds)


def add_deadline_event(service, title, deadline_date, url):
    """deadline_date: a datetime.date object."""
    if service is None or not GOOGLE_CALENDAR_ID:
        print(f"[calendar] skipped (no credentials configured): {title} -> {deadline_date}")
        return

    event = {
        "summary": f"⏰ Deadline: {title}",
        "description": url,
        "start": {"date": deadline_date.isoformat()},
        "end": {"date": deadline_date.isoformat()},
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 3 * 24 * 60},  # 3 days before
                {"method": "popup", "minutes": 1 * 24 * 60},  # 1 day before
                {"method": "popup", "minutes": 2 * 60},       # 2 hours before
            ],
        },
    }
    try:
        service.events().insert(calendarId=GOOGLE_CALENDAR_ID, body=event).execute()
        print(f"[calendar] added: {title} -> {deadline_date}")
    except Exception as e:
        print(f"[calendar] failed to add '{title}': {e}")

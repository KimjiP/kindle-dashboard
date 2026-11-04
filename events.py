"""Today's events from a Google Calendar secret iCal address.

The address is a secret: anyone who has it can read the calendar. It comes from
the CALENDAR_URL environment variable (a GitHub secret later, .env on the Mac).
"""

import os
from datetime import datetime

import icalendar
import recurring_ical_events
import requests


def fetch(now):
    url = os.environ.get("CALENDAR_URL")
    if not url:
        print("No CALENDAR_URL set, so the calendar is empty.")
        return []
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
    except requests.RequestException as e:
        # Don't pass the error on: its text contains the secret URL, and logs can be public.
        reason = e.response.status_code if e.response is not None else type(e).__name__
        raise RuntimeError(f"could not download the calendar ({reason})") from None
    return parse(r.content, now)


def parse(ics, now):
    """Events today that are not over yet: all-day ones first (start=None), then by start time."""
    calendar = icalendar.Calendar.from_ical(ics)
    events = []
    for e in recurring_ical_events.of(calendar).at(now.date()):  # also expands repeating events
        if e.get("STATUS") == "CANCELLED":
            continue
        start, end = e.start, e.end
        if isinstance(start, datetime):
            start, end = local(start, now.tzinfo), local(end, now.tzinfo)
            if end <= now:
                continue  # already over
            if start.date() < now.date():
                start = None  # began before today: show it like an all-day event
        else:
            start = None  # all-day event
        events.append({"start": start, "title": str(e.get("SUMMARY", "(No title)"))})
    return sorted(events, key=lambda e: (e["start"] is not None, e["start"] or now))


def local(dt, tz):
    """Time in Oslo. A time with no time zone is taken as Oslo time."""
    return dt.replace(tzinfo=tz) if dt.tzinfo is None else dt.astimezone(tz)

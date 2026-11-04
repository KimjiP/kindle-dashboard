"""Next departures from your stop, from Entur's Journey Planner API (free, no key).

Entur wants an ET-Client-Name header in the form "<company>-<application>".
The stops and lines come from STOPS and ROUTES (in .env, and as GitHub secrets), so where
you live stays out of this public repo.
"""

import os
from datetime import datetime

import requests

URL = "https://api.entur.io/journey-planner/v3/graphql"
HEADERS = {"ET-Client-Name": "kimjip-kindle-dashboard"}

QUERY = """
query ($ids: [String]!) {
  stopPlaces(ids: $ids) {
    estimatedCalls(numberOfDepartures: 50, numberOfDeparturesPerLineAndDestinationDisplay: 3,
                   timeRange: 21600, arrivalDeparture: departures) {
      expectedDepartureTime
      cancellation
      destinationDisplay { frontText }
      serviceJourney { id line { publicCode transportMode } }
    }
  }
}
"""


def settings():
    """STOPS: stop place IDs, comma-separated, like "NSR:StopPlace:12345,NSR:StopPlace:67890".
    ROUTES: the rows on the dashboard, top to bottom, as "line destination" (the destination on the
    front of the train or bus), comma-separated, like "1 Frognerseteren, 31 Snarøya"."""
    stops, routes = os.environ.get("STOPS", ""), os.environ.get("ROUTES", "")
    if not stops or not routes:
        raise RuntimeError("STOPS and ROUTES are not set (see the README)")
    return [s.strip() for s in stops.split(",")], [r.strip().split(" ", 1) for r in routes.split(",")]


def fetch(now):
    """One row per route, with its next 3 departure times."""
    stops, routes = settings()
    r = requests.post(URL, json={"query": QUERY, "variables": {"ids": stops}}, headers=HEADERS, timeout=20)
    r.raise_for_status()
    body = r.json()
    if "errors" in body:
        raise RuntimeError(body["errors"])

    calls = [c for stop in body["data"]["stopPlaces"] for c in stop["estimatedCalls"] if not c["cancellation"]]
    for c in calls:
        c["time"] = datetime.fromisoformat(c["expectedDepartureTime"]).astimezone(now.tzinfo)
    calls.sort(key=lambda c: c["time"])

    rows = []
    for line, destination in routes:
        matches, seen = [], set()
        for c in calls:
            trip = c["serviceJourney"]
            if trip["line"]["publicCode"] == line and c["destinationDisplay"]["frontText"] == destination:
                if trip["id"] not in seen:  # some buses stop at both stops: count them once
                    seen.add(trip["id"])
                    matches.append(c)
        rows.append({
            "line": line,
            "mode": matches[0]["serviceJourney"]["line"]["transportMode"] if matches else "bus",
            "destination": destination,
            "times": [c["time"] for c in matches[:3]],
        })
    return rows

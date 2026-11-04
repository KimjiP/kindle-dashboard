"""Made-up data, for working on the layout offline:  python3 render.py --fake"""

from datetime import timedelta


def data(now):
    """Fake data in the same shape the real sources return."""

    def at(minutes):
        return now + timedelta(minutes=minutes)

    next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    hourly = [
        ("lightrain", 4),
        ("rain", 4),
        ("cloudy", 3),
        ("partlycloudy_night", 2),
        ("fair_night", 1),
        ("clearsky_night", -1),
    ]
    return {
        "now": now,
        "weather": {
            "symbol": "lightrain",
            "text": "Light rain",
            "temp": 4,
            "high": 7,
            "low": -1,
            "rain_chance": 60,
            "rain_mm": 1.2,
            "hours": [
                {"time": next_hour + timedelta(hours=i), "symbol": s, "temp": t}
                for i, (s, t) in enumerate(hourly)
            ],
        },
        "sun": {"rise": now.replace(hour=7, minute=45), "set": now.replace(hour=16, minute=13)},
        "departures": [
            {"line": "5", "mode": "metro", "destination": "Sognsvann", "times": [at(6), at(14), at(21)]},
            {"line": "5", "mode": "metro", "destination": "Vestli", "times": [at(3), at(11), at(18)]},
            {"line": "31", "mode": "bus", "destination": "Snarøya", "times": [at(4), at(19), at(34)]},
            {"line": "20", "mode": "bus", "destination": "Skøyen", "times": [at(9), at(23), at(38)]},
        ],
        "calendar": [
            {"start": None, "title": "Bin day"},  # None = all-day event
            {"start": now.replace(hour=9, minute=0), "title": "Team standup"},
            {"start": now.replace(hour=18, minute=30), "title": "Climbing with Ola"},
        ],
        "todo": ["Finish Kindle dashboard step 1"],
    }

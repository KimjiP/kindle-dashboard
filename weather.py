"""Weather for Oslo from MET Norway (api.met.no), the data behind Yr.

MET's terms: send a User-Agent that names the app, and use at most 4 decimals
in the coordinates. https://api.met.no/doc/TermsOfService
"""

import re
from datetime import datetime, timedelta

import requests

LAT, LON = 59.913, 10.739  # Oslo city centre: the weather is about the same across the city
URL = "https://api.met.no/weatherapi/locationforecast/2.0/complete"
COMPACT_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"  # a backup, with no chance of rain
SUN_URL = "https://api.met.no/weatherapi/sunrise/3.0/sun"
HEADERS = {"User-Agent": "kindle-dashboard github.com/KimjiP/kindle-dashboard"}


def describe(symbol):
    """MET symbol code to words: 'lightrainshowers_day' -> 'Light rain showers'."""
    words = re.findall(r"heavy|light|clear|sky|fair|partly|cloudy|fog|rain|sleet|snow|showers|and|thunder", symbol)
    return " ".join(words).capitalize()


def sun(now):
    """Today's sunrise and sunset in Oslo."""
    offset = now.strftime("%z")  # "+0100" in winter, "+0200" in summer
    params = {"lat": LAT, "lon": LON, "date": f"{now:%Y-%m-%d}", "offset": f"{offset[:3]}:{offset[3:]}"}
    r = requests.get(SUN_URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    p = r.json()["properties"]
    return {"rise": datetime.fromisoformat(p["sunrise"]["time"]), "set": datetime.fromisoformat(p["sunset"]["time"])}


def forecast(url):
    r = requests.get(url, params={"lat": LAT, "lon": LON}, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()["properties"]["timeseries"]  # one entry per hour at first


def fetch(now):
    """Weather now, high and low for the next 24 hours, and the next 6 hours."""
    try:
        series = forecast(URL)
    except requests.RequestException as e:
        # MET sometimes sends a cut-off forecast and keeps it in its cache for up to half an
        # hour, so trying again doesn't help. The compact forecast is a separate download,
        # with everything except the chance of rain.
        print(f"weather: the full forecast failed ({e!r}), using the compact one")
        series = forecast(COMPACT_URL)

    for entry in series:
        entry["time"] = datetime.fromisoformat(entry["time"]).astimezone(now.tzinfo)
    series = [e for e in series if e["time"] > now - timedelta(hours=1)]  # from the current hour on

    def temp(entry):
        return entry["data"]["instant"]["details"]["air_temperature"]

    def symbol(entry):
        return entry["data"]["next_1_hours"]["summary"]["symbol_code"]

    current = series[0]
    next_day = [temp(e) for e in series[:24]]
    rain = current["data"]["next_6_hours"]["details"]
    chance = rain.get("probability_of_precipitation")  # only in the full forecast
    return {
        "symbol": symbol(current),
        "text": describe(symbol(current)),
        "temp": temp(current),
        "high": max(next_day),
        "low": min(next_day),
        "rain_chance": None if chance is None else round(chance),
        "rain_mm": rain["precipitation_amount"],
        "hours": [{"time": e["time"], "symbol": symbol(e), "temp": temp(e)} for e in series[1:7]],
    }

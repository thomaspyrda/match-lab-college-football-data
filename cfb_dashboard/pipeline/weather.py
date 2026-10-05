"""Weather helpers for the CFB Dashboard.

Weather is intentionally conservative: forecasts are shown only when a venue has
been explicitly classified as outdoor. Indoor/retractable/unknown venues never
receive a guessed forecast.
"""
from __future__ import annotations
import json
import urllib.request
from datetime import datetime

INDOOR_ROOFS={"dome","closed","indoor","retractable","retractable roof"}
OUTDOOR_ROOFS={"outdoors","outdoor","open air"}

def weather_applicable(venue: dict, neutral_site: bool=False) -> bool:
    roof=str((venue or {}).get("roof") or "").strip().lower()
    return not neutral_site and roof in OUTDOOR_ROOFS

def _json(url: str) -> dict:
    req=urllib.request.Request(url,headers={
      "User-Agent":"BetWise-CFB-Dashboard/0.1 (https://parlaycalculator.bet)",
      "Accept":"application/geo+json",
    })
    with urllib.request.urlopen(req,timeout=20) as response:return json.load(response)

def outdoor_forecast(venue: dict,kickoff: datetime) -> str:
    lat=(venue or {}).get("latitude"); lon=(venue or {}).get("longitude")
    if lat is None or lon is None:return "Outdoor · forecast location unavailable"
    try:
        meta=_json(f"https://api.weather.gov/points/{lat},{lon}")
        periods=_json(meta["properties"]["forecastHourly"])["properties"]["periods"]
        period=next((x for x in periods if datetime.fromisoformat(x["startTime"])<=kickoff<datetime.fromisoformat(x["endTime"])),None)
        if not period:return "Outdoor · forecast not yet available"
        pop=(period.get("probabilityOfPrecipitation") or {}).get("value")
        rain=f" · {pop}% precipitation" if pop is not None else ""
        return f"Outdoor · {period['temperature']}°{period['temperatureUnit']} · Wind {period['windSpeed']} · {period['shortForecast']}{rain}"
    except (KeyError,StopIteration,OSError,ValueError,TimeoutError):
        return "Outdoor · forecast temporarily unavailable"

def game_weather(venue: dict,kickoff: datetime,neutral_site: bool=False) -> str:
    roof=str((venue or {}).get("roof") or "").strip().lower()
    if roof in INDOOR_ROOFS:return "Indoor/retractable roof · weather not applicable"
    if not weather_applicable(venue,neutral_site):return "Venue weather unavailable"
    return outdoor_forecast(venue,kickoff)

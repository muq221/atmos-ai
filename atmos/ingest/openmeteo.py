"""Open-Meteo client (free, no API key).

* forecast_hourly()  -> next N days from the live Forecast API
* history_hourly()   -> past data from the Historical Forecast API
                        (same variables as the live feed, incl. visibility & CAPE)

Every call returns the raw JSON exactly as the API sends it; the bronze
layer stores it untouched and the silver layer does the cleaning.
"""
from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

import requests

from atmos import config

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HISTORY_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"

HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "pressure_msl",
    "cloud_cover",
    "cloud_cover_low",
    "visibility",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "precipitation",
    "cape",
    "weather_code",
]


class OpenMeteoError(RuntimeError):
    pass


def _get(url: str, params: dict, retries: int = 3, backoff: float = 2.0) -> dict:
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 429:  # rate limited - wait and retry
                time.sleep(backoff * attempt * 5)
                continue
            r.raise_for_status()
            payload = r.json()
            if payload.get("error"):
                raise OpenMeteoError(payload.get("reason", "unknown error"))
            return payload
        except (requests.ConnectionError, requests.Timeout) as exc:
            if attempt == retries:
                raise OpenMeteoError(f"Open-Meteo unreachable: {exc}") from exc
            time.sleep(backoff * attempt)
    raise OpenMeteoError("Open-Meteo rate limit not cleared after retries")


def _params(airport: config.Airport) -> dict:
    return {
        "latitude": airport.lat,
        "longitude": airport.lon,
        "hourly": ",".join(HOURLY_VARS),
        "wind_speed_unit": "ms",
        "timezone": config.TIMEZONE,
    }


def forecast_hourly(airport: config.Airport, days: int = 2) -> dict:
    params = _params(airport) | {"forecast_days": days, "past_days": 1}
    return _get(FORECAST_URL, params)


def history_hourly(airport: config.Airport, start: date, end: date) -> dict:
    params = _params(airport) | {"start_date": start.isoformat(), "end_date": end.isoformat()}
    return _get(HISTORY_URL, params)


def save_bronze(payload: dict, icao: str, tag: str, bronze_dir: Path = config.BRONZE) -> Path:
    """Write the untouched API response to the bronze layer."""
    out = bronze_dir / icao / f"{tag}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload))
    return out

"""Serving layer: loads the trained models once and turns a weather feed into
current conditions, 3-hour-ahead predictions, advisories and text briefings.

Sample mode  -> the feed is read from the silver table around ATMOS_DEMO_NOW
Live mode    -> the feed is pulled from the Open-Meteo forecast API each hour
"""
from __future__ import annotations

import json
import time
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd

from atmos import config
from atmos.aviation.rules import CATEGORIES, MS_TO_KT, advisory, density_altitude_ft
from atmos.ingest import openmeteo
from atmos.pipeline.layers import add_features, bronze_to_frame, clean

CACHE_SECONDS = 3600
_feed_cache: dict[str, tuple[float, pd.DataFrame]] = {}


@lru_cache(maxsize=1)
def models() -> dict:
    return joblib.load(config.MODEL_DIR / "atmos_models.joblib")


@lru_cache(maxsize=1)
def model_metrics() -> dict:
    return json.loads((config.MODEL_DIR / "metrics.json").read_text())


@lru_cache(maxsize=1)
def _silver() -> pd.DataFrame:
    return pd.read_parquet(config.SILVER / "observations.parquet")


def now() -> pd.Timestamp:
    if config.DATA_SOURCE == "sample":
        return pd.Timestamp(config.DEMO_NOW)
    return pd.Timestamp.now(tz=config.TIMEZONE).floor("h").tz_localize(None)


def feed(icao: str) -> pd.DataFrame:
    """Hourly rows for one airport: 24 h of history (for lag features) + up to 30 h ahead."""
    hit = _feed_cache.get(icao)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    t = now()
    if config.DATA_SOURCE == "sample":
        s = _silver()
        rows = s[(s.icao == icao) & (s.time >= t - pd.Timedelta(hours=24)) & (s.time <= t + pd.Timedelta(hours=30))]
    else:
        payload = openmeteo.forecast_hourly(config.AIRPORTS[icao], days=2)
        rows, _ = clean(bronze_to_frame(payload, icao))
    df = add_features(rows.copy())
    feats = models()["features"]
    X = df[feats].ffill().bfill()
    m = models()
    proba = m["category"].predict_proba(X)
    classes = list(m["category"].classes_)
    df["pred_category"] = np.array(classes)[proba.argmax(1)]
    for c in CATEGORIES:
        df[f"p_{c}"] = proba[:, classes.index(c)] if c in classes else 0.0
    df["pred_visibility_m"] = np.round(10 ** m["visibility"].predict(X), -1)
    df["thunder_prob"] = m["thunder"].predict_proba(X)[:, 1]
    _feed_cache[icao] = (time.time(), df)
    return df


def _row_at(df: pd.DataFrame, t: pd.Timestamp) -> pd.Series:
    past = df[df.time <= t]
    return (past if len(past) else df).iloc[-1]


def current(icao: str) -> dict:
    ap = config.AIRPORTS[icao]
    r = _row_at(feed(icao), now())
    return {
        "icao": icao,
        "time": r.time.isoformat(),
        "flight_category": r.flight_category,
        "temperature_c": round(float(r.temperature_c), 1),
        "dewpoint_c": round(float(r.dewpoint_c), 1),
        "humidity_pct": int(r.humidity_pct),
        "qnh_hpa": round(float(r.pressure_msl_hpa)),
        "visibility_m": int(r.visibility_m),
        "ceiling_ft": None if r.ceiling_ft >= 99999 else int(r.ceiling_ft),
        "cloud_cover_pct": int(r.cloud_cover_pct),
        "wind_direction_deg": int(r.wind_direction_deg),
        "wind_speed_kt": round(float(r.wind_speed_ms) * MS_TO_KT),
        "wind_gust_kt": round(float(r.wind_gust_ms) * MS_TO_KT),
        "precip_mm": float(r.precip_mm),
        "cape_jkg": int(r.cape_jkg),
        "weather_code": int(r.weather_code),
        "density_altitude_ft": density_altitude_ft(ap.elevation_m, float(r.temperature_c), float(r.pressure_msl_hpa)),
    }


def forecast(icao: str, hours: int = 24) -> list[dict]:
    df = feed(icao)
    t = now()
    rows = df[(df.time >= t) & (df.time <= t + pd.Timedelta(hours=hours))]
    out = []
    for r in rows.itertuples():
        out.append({
            "issued_from": r.time.isoformat(),
            "valid_time": (r.time + pd.Timedelta(hours=config.FORECAST_HORIZON_H)).isoformat(),
            "predicted_category": r.pred_category,
            "probabilities": {c: round(float(getattr(r, f"p_{c}")), 3) for c in CATEGORIES},
            "predicted_visibility_m": int(r.pred_visibility_m),
            "thunderstorm_probability": round(float(r.thunder_prob), 3),
            "wind_speed_kt": round(float(r.wind_speed_ms) * MS_TO_KT),
            "wind_gust_kt": round(float(r.wind_gust_ms) * MS_TO_KT),
            "wind_direction_deg": int(r.wind_direction_deg),
            "temperature_c": round(float(r.temperature_c), 1),
            "observed_category": r.flight_category,
            "visibility_m": int(r.visibility_m),
        })
    return out


def get_advisory(icao: str) -> dict:
    ap = config.AIRPORTS[icao]
    r = _row_at(feed(icao), now())
    adv = advisory(r.to_dict(), r.pred_category, float(r.thunder_prob), ap)
    return {"icao": icao, "valid_for_hours": config.FORECAST_HORIZON_H, "predicted_category": r.pred_category,
            "confidence": round(float(r[f"p_{r.pred_category}"]), 3), **adv.to_dict()}


WX_TEXT = {45: "fog", 48: "freezing fog", 61: "light rain", 63: "moderate rain", 65: "heavy rain", 95: "thunderstorm"}


def briefing(icao: str) -> dict:
    ap = config.AIRPORTS[icao]
    c = current(icao)
    a = get_advisory(icao)
    wx = WX_TEXT.get(c["weather_code"], "no significant weather")
    ceiling = "no ceiling" if c["ceiling_ft"] is None else f"ceiling {c['ceiling_ft']} ft"
    vis = f"{c['visibility_m'] / 1000:.1f} km" if c["visibility_m"] >= 1000 else f"{c['visibility_m']} m"
    lines = [
        f"{icao} {ap.city} - {pd.Timestamp(c['time']):%d %b %H:%M} IST",
        f"Now: {c['flight_category']}, visibility {vis} ({wx}), {ceiling}, wind {c['wind_direction_deg']:03d}/{c['wind_speed_kt']:02d} kt, "
        f"temp {c['temperature_c']:.0f}/{c['dewpoint_c']:.0f} C, QNH {c['qnh_hpa']}.",
        f"Next {config.FORECAST_HORIZON_H} h: {a['predicted_category']} expected ({a['confidence']:.0%} confidence). "
        f"Best runway {a['runway']['best']['runway']} - headwind {a['runway']['best']['headwind_kt']:.0f} kt, crosswind {a['runway']['best']['crosswind_kt']:.0f} kt.",
        f"Advisory: {a['level']} (score {a['score']}/100) - " + "; ".join(a["reasons"]) + ".",
    ]
    if a["predicted_category"] in ("IFR", "LIFR") or c["flight_category"] in ("IFR", "LIFR"):
        lines.append("Action: low-visibility procedures likely; brief alternates and carry extra holding fuel.")
    elif a["level"] == "CAUTION":
        lines.append("Action: monitor the next update; expect possible delays.")
    return {"icao": icao, "text": "\n".join(lines), "advisory_level": a["level"]}


def network() -> list[dict]:
    out = []
    for icao, ap in config.AIRPORTS.items():
        c, a = current(icao), get_advisory(icao)
        out.append({"icao": icao, "iata": ap.iata, "city": ap.city, "lat": ap.lat, "lon": ap.lon,
                    "flight_category": c["flight_category"], "predicted_category": a["predicted_category"],
                    "advisory_level": a["level"], "score": a["score"], "visibility_m": c["visibility_m"],
                    "wind_speed_kt": c["wind_speed_kt"], "temperature_c": c["temperature_c"]})
    return out

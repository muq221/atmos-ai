"""Aviation weather rules: flight categories, runway wind components,
density altitude and the operational advisory score.

Flight category thresholds follow the FAA/ICAO convention used on
aviation weather charts:
    VFR   ceiling > 3000 ft  and visibility > 5 SM (8 km)
    MVFR  ceiling 1000-3000 ft or visibility 3-5 SM
    IFR   ceiling  500-999 ft  or visibility 1-<3 SM
    LIFR  ceiling < 500 ft     or visibility < 1 SM (1.6 km)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict

import numpy as np

from atmos import config

CATEGORIES = ["VFR", "MVFR", "IFR", "LIFR"]
CATEGORY_COLOR = {"VFR": "#3ddc84", "MVFR": "#4aa3ff", "IFR": "#ff5c5c", "LIFR": "#d36cff"}

SM_TO_M = 1609.34
MS_TO_KT = 1.943844
UNLIMITED_CEILING_FT = 99999


def flight_category(visibility_m: float, ceiling_ft: float) -> str:
    """Return VFR / MVFR / IFR / LIFR for one observation."""
    vis_sm = visibility_m / SM_TO_M
    if ceiling_ft < 500 or vis_sm < 1:
        return "LIFR"
    if ceiling_ft < 1000 or vis_sm < 3:
        return "IFR"
    if ceiling_ft <= 3000 or vis_sm <= 5:
        return "MVFR"
    return "VFR"


def flight_category_vec(visibility_m, ceiling_ft) -> np.ndarray:
    """Vectorised version used by the pipeline."""
    vis_sm = np.asarray(visibility_m, dtype=float) / SM_TO_M
    ceil = np.asarray(ceiling_ft, dtype=float)
    out = np.full(vis_sm.shape, "VFR", dtype=object)
    out[(ceil <= 3000) | (vis_sm <= 5)] = "MVFR"
    out[(ceil < 1000) | (vis_sm < 3)] = "IFR"
    out[(ceil < 500) | (vis_sm < 1)] = "LIFR"
    return out


def wind_components(wind_dir_deg: float, wind_speed_kt: float, runway_heading_deg: float) -> tuple[float, float]:
    """Headwind (+) / tailwind (-) and crosswind (absolute) for a runway."""
    angle = math.radians(wind_dir_deg - runway_heading_deg)
    headwind = wind_speed_kt * math.cos(angle)
    crosswind = abs(wind_speed_kt * math.sin(angle))
    return round(headwind, 1), round(crosswind, 1)


def best_runway(wind_dir_deg: float, wind_speed_kt: float, runways: tuple[int, ...]) -> dict:
    """Pick the runway direction with the most headwind (least tailwind)."""
    rows = []
    for rwy in runways:
        hw, xw = wind_components(wind_dir_deg, wind_speed_kt, rwy)
        rows.append({"runway": f"{round(rwy / 10):02d}", "heading": rwy, "headwind_kt": hw, "crosswind_kt": xw})
    rows.sort(key=lambda r: (-r["headwind_kt"], r["crosswind_kt"]))
    return {"best": rows[0], "all": rows}


def density_altitude_ft(elevation_m: float, temp_c: float, qnh_hpa: float) -> float:
    """Approximate density altitude (ft) - matters for hot & high airports."""
    pressure_alt_ft = elevation_m * 3.28084 + (1013.25 - qnh_hpa) * 30
    isa_temp_c = 15 - 1.98 * (elevation_m * 3.28084 / 1000)
    return round(pressure_alt_ft + 118.8 * (temp_c - isa_temp_c))


@dataclass
class Advisory:
    level: str          # NORMAL / CAUTION / ADVERSE
    score: int          # 0-100
    reasons: list[str]
    runway: dict
    density_altitude_ft: float

    def to_dict(self) -> dict:
        return asdict(self)


CATEGORY_POINTS = {"VFR": 0, "MVFR": 15, "IFR": 40, "LIFR": 70}


def advisory(obs: dict, predicted_category: str, ts_probability: float, airport: config.Airport) -> Advisory:
    """Combine current conditions, the 3-hour forecast and runway winds into one advisory.
    The worse of 'now' and 'in 3 h' drives the visibility/ceiling part of the score."""
    score = 0
    reasons: list[str] = []

    current_category = obs.get("flight_category", "VFR")
    now_pts, next_pts = CATEGORY_POINTS[current_category], CATEGORY_POINTS[predicted_category]
    score += max(now_pts, next_pts)
    if now_pts:
        vis = obs["visibility_m"]
        reasons.append(f"Currently {current_category} - visibility {vis / 1000:.1f} km" if vis >= 1000
                       else f"Currently {current_category} - visibility {vis:.0f} m")
    if next_pts:
        reasons.append(f"{predicted_category} expected within {config.FORECAST_HORIZON_H} h")
    elif now_pts:
        reasons.append(f"Improving to {predicted_category} within {config.FORECAST_HORIZON_H} h")

    wind_kt = obs["wind_speed_ms"] * MS_TO_KT
    gust_kt = obs["wind_gust_ms"] * MS_TO_KT
    rwy = best_runway(obs["wind_direction_deg"], wind_kt, airport.runways)
    xw = rwy["best"]["crosswind_kt"]
    if xw >= config.CROSSWIND_ADVERSE_KT:
        score += 35
        reasons.append(f"Crosswind {xw:.0f} kt on RWY {rwy['best']['runway']}")
    elif xw >= config.CROSSWIND_CAUTION_KT:
        score += 15
        reasons.append(f"Crosswind {xw:.0f} kt on RWY {rwy['best']['runway']}")
    if gust_kt >= config.GUST_CAUTION_KT:
        score += 15
        reasons.append(f"Gusts up to {gust_kt:.0f} kt")

    if ts_probability >= config.TS_PROB_ADVERSE:
        score += 40
        reasons.append(f"Thunderstorm risk {ts_probability:.0%}")
    elif ts_probability >= config.TS_PROB_CAUTION:
        score += 20
        reasons.append(f"Thunderstorm risk {ts_probability:.0%}")

    da = density_altitude_ft(airport.elevation_m, obs["temperature_c"], obs["pressure_msl_hpa"])
    if da > 5000:
        score += 10
        reasons.append(f"High density altitude {da:,.0f} ft - check take-off performance")

    score = int(min(score, 100))
    level = "ADVERSE" if score >= 65 else "CAUTION" if score >= 30 else "NORMAL"
    if not reasons:
        reasons.append("No significant weather expected")
    return Advisory(level, score, reasons, rwy, da)

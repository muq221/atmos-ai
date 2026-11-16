"""Offline sample-data generator.

Produces hourly weather in exactly the same JSON shape as the Open-Meteo
API, so the rest of the pipeline cannot tell the difference. Values are
driven by monthly climate normals for each airport plus random weather
"systems" (multi-day anomalies, rain spells, fog nights, thunderstorms).

Used for development, tests and demos when the API is not reachable.
It is NOT observed data - switch ATMOS_SOURCE=openmeteo for real data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.signal import lfilter

from atmos import config

# Monthly normals (Jan..Dec). T = mean temp C, RH = mean %, DTR = day-night range C,
# RAIN = share of hours with rain, CLOUD = mean cover %, WDIR/WSPD = prevailing wind,
# FOG/HAZE/TS = seasonal propensity 0-1, MSLP = mean sea-level pressure hPa
CLIMATE = {
    "VOHS": dict(
        T=[22.0, 25.0, 28.5, 31.5, 33.0, 29.0, 26.5, 26.0, 26.5, 25.5, 23.0, 21.5],
        RH=[55, 45, 38, 37, 38, 62, 73, 76, 74, 66, 60, 58],
        DTR=[14, 15, 15, 14, 13, 9, 7, 7, 8, 9, 11, 13],
        RAIN=[0.003, 0.004, 0.008, 0.012, 0.02, 0.07, 0.10, 0.10, 0.09, 0.05, 0.015, 0.004],
        CLOUD=[20, 15, 20, 25, 30, 70, 85, 85, 75, 55, 35, 25],
        WDIR=[90, 110, 140, 200, 250, 260, 270, 270, 250, 90, 80, 80],
        WSPD=[2.5, 2.6, 2.8, 3.2, 4.2, 5.5, 6.0, 5.5, 4.0, 2.8, 2.6, 2.4],
        FOG=[0.25, 0.10, 0, 0, 0, 0, 0, 0, 0, 0.05, 0.15, 0.30],
        HAZE=[0.30, 0.25, 0.20, 0.15, 0.10, 0, 0, 0, 0, 0.10, 0.20, 0.30],
        TS=[0.05, 0.10, 0.25, 0.40, 0.50, 0.40, 0.30, 0.30, 0.40, 0.30, 0.10, 0.03],
        MSLP=[1015, 1013, 1010, 1007, 1004, 1002, 1002, 1003, 1006, 1010, 1013, 1015],
    ),
    "VIDP": dict(
        T=[14.0, 17.5, 23.0, 29.5, 33.5, 33.5, 31.0, 30.0, 29.5, 26.0, 20.5, 15.5],
        RH=[78, 68, 55, 36, 36, 52, 75, 80, 72, 60, 65, 75],
        DTR=[12, 13, 14, 15, 14, 11, 8, 7, 9, 13, 14, 13],
        RAIN=[0.010, 0.012, 0.010, 0.008, 0.015, 0.04, 0.11, 0.11, 0.06, 0.010, 0.004, 0.006],
        CLOUD=[30, 30, 25, 20, 25, 45, 75, 80, 55, 20, 15, 25],
        WDIR=[300, 300, 300, 290, 280, 110, 110, 110, 110, 300, 300, 300],
        WSPD=[2.0, 2.6, 3.0, 3.5, 3.8, 3.6, 3.0, 2.6, 2.5, 1.8, 1.6, 1.7],
        FOG=[1.00, 0.45, 0.05, 0, 0, 0, 0, 0, 0, 0.05, 0.45, 0.95],
        HAZE=[0.70, 0.50, 0.35, 0.30, 0.35, 0.30, 0.05, 0.05, 0.10, 0.50, 0.80, 0.80],
        TS=[0.05, 0.08, 0.15, 0.30, 0.45, 0.50, 0.35, 0.30, 0.20, 0.05, 0.02, 0.03],
        MSLP=[1018, 1016, 1012, 1007, 1002, 998, 998, 1000, 1005, 1011, 1016, 1018],
    ),
    "VABB": dict(
        T=[24.0, 25.0, 27.0, 28.8, 30.3, 29.4, 27.7, 27.4, 27.9, 28.9, 28.0, 26.0],
        RH=[60, 61, 64, 68, 70, 80, 87, 87, 84, 75, 64, 62],
        DTR=[10, 10, 9, 7, 6, 5, 4, 4, 5, 7, 9, 10],
        RAIN=[0.001, 0.001, 0.001, 0.002, 0.010, 0.20, 0.33, 0.28, 0.17, 0.03, 0.008, 0.002],
        CLOUD=[15, 15, 15, 20, 35, 85, 95, 92, 80, 40, 20, 15],
        WDIR=[340, 330, 300, 290, 270, 250, 250, 260, 270, 320, 340, 350],
        WSPD=[3.0, 3.4, 3.8, 4.0, 4.4, 5.5, 6.5, 6.0, 4.2, 3.0, 2.8, 2.8],
        FOG=[0.05, 0.03, 0, 0, 0, 0, 0, 0, 0, 0, 0.02, 0.05],
        HAZE=[0.50, 0.45, 0.30, 0.15, 0.10, 0, 0, 0, 0, 0.15, 0.40, 0.50],
        TS=[0.01, 0.01, 0.02, 0.05, 0.15, 0.40, 0.25, 0.20, 0.40, 0.35, 0.08, 0.02],
        MSLP=[1013, 1012, 1010, 1008, 1006, 1003, 1003, 1004, 1007, 1009, 1011, 1012],
    ),
    "VOBL": dict(
        T=[21.0, 23.5, 26.0, 28.0, 27.5, 24.5, 23.5, 23.5, 23.5, 23.5, 22.0, 21.0],
        RH=[62, 55, 50, 55, 65, 75, 80, 80, 78, 77, 72, 68],
        DTR=[12, 13, 13, 12, 11, 8, 7, 7, 8, 8, 9, 11],
        RAIN=[0.002, 0.004, 0.008, 0.025, 0.05, 0.05, 0.06, 0.07, 0.08, 0.07, 0.03, 0.008],
        CLOUD=[25, 20, 25, 40, 55, 80, 90, 88, 75, 65, 50, 35],
        WDIR=[90, 100, 110, 200, 250, 260, 270, 270, 260, 110, 90, 90],
        WSPD=[3.2, 3.0, 3.0, 3.2, 4.0, 6.0, 6.5, 6.0, 4.5, 3.2, 3.4, 3.5],
        FOG=[0.45, 0.30, 0.05, 0, 0, 0, 0, 0, 0.02, 0.05, 0.20, 0.40],
        HAZE=[0.30, 0.25, 0.20, 0.10, 0.05, 0, 0, 0, 0, 0.05, 0.20, 0.30],
        TS=[0.02, 0.05, 0.15, 0.40, 0.50, 0.30, 0.25, 0.30, 0.45, 0.40, 0.15, 0.03],
        MSLP=[1014, 1013, 1011, 1009, 1008, 1007, 1007, 1007, 1009, 1011, 1012, 1013],
    ),
    "VOMM": dict(
        T=[25.0, 26.5, 28.5, 31.0, 33.0, 32.5, 31.0, 30.0, 29.5, 28.0, 26.0, 25.0],
        RH=[72, 70, 70, 70, 64, 58, 62, 66, 70, 78, 80, 76],
        DTR=[8, 9, 9, 8, 9, 10, 9, 9, 8, 7, 6, 7],
        RAIN=[0.010, 0.003, 0.003, 0.005, 0.010, 0.03, 0.05, 0.06, 0.06, 0.13, 0.17, 0.09],
        CLOUD=[35, 25, 25, 30, 35, 55, 65, 65, 65, 75, 80, 60],
        WDIR=[50, 70, 120, 150, 180, 220, 240, 240, 230, 60, 40, 40],
        WSPD=[3.8, 3.8, 4.2, 4.8, 4.8, 5.0, 5.0, 4.8, 4.2, 3.5, 4.0, 4.2],
        FOG=[0.10, 0.08, 0.02, 0, 0, 0, 0, 0, 0, 0, 0.05, 0.08],
        HAZE=[0.30, 0.25, 0.20, 0.15, 0.10, 0.05, 0.05, 0.05, 0.05, 0.10, 0.20, 0.30],
        TS=[0.02, 0.02, 0.03, 0.10, 0.25, 0.30, 0.35, 0.40, 0.45, 0.45, 0.25, 0.08],
        MSLP=[1013, 1012, 1010, 1008, 1005, 1004, 1004, 1005, 1007, 1009, 1010, 1012],
    ),
    "VECC": dict(
        T=[19.5, 23.0, 28.0, 30.5, 31.0, 30.5, 29.5, 29.5, 29.5, 28.0, 24.0, 20.0],
        RH=[70, 63, 62, 70, 74, 82, 86, 86, 84, 78, 70, 70],
        DTR=[12, 12, 12, 10, 9, 7, 6, 6, 6, 8, 11, 12],
        RAIN=[0.004, 0.008, 0.012, 0.025, 0.05, 0.12, 0.17, 0.16, 0.13, 0.05, 0.008, 0.002],
        CLOUD=[20, 20, 25, 35, 50, 80, 90, 90, 80, 50, 25, 20],
        WDIR=[340, 320, 220, 190, 180, 170, 150, 150, 140, 20, 350, 340],
        WSPD=[1.8, 2.2, 2.8, 3.8, 4.0, 3.6, 3.4, 3.0, 2.6, 2.0, 1.8, 1.7],
        FOG=[0.80, 0.40, 0.05, 0, 0, 0, 0, 0, 0, 0.05, 0.35, 0.75],
        HAZE=[0.70, 0.50, 0.30, 0.15, 0.10, 0, 0, 0, 0, 0.20, 0.60, 0.70],
        TS=[0.03, 0.08, 0.25, 0.55, 0.60, 0.45, 0.35, 0.35, 0.40, 0.25, 0.05, 0.02],
        MSLP=[1016, 1014, 1010, 1006, 1003, 1000, 999, 1000, 1004, 1010, 1014, 1016],
    ),
}

MID_MONTH_DOY = np.array([15, 46, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349])


def _seasonal(values, doy: np.ndarray, circular: bool = False) -> np.ndarray:
    """Periodic interpolation of 12 monthly values to every day of year."""
    v = np.asarray(values, dtype=float)
    x = np.concatenate([MID_MONTH_DOY - 365, MID_MONTH_DOY, MID_MONTH_DOY + 365])
    if circular:  # wind direction - interpolate on unit vectors
        s = np.interp(doy, x, np.tile(np.sin(np.radians(v)), 3))
        c = np.interp(doy, x, np.tile(np.cos(np.radians(v)), 3))
        return np.degrees(np.arctan2(s, c)) % 360
    return np.interp(doy, x, np.tile(v, 3))


def _ar1(n: int, hours_memory: float, sigma: float, rng: np.random.Generator) -> np.ndarray:
    """Red-noise process: slowly varying 'weather systems'."""
    phi = np.exp(-1.0 / hours_memory)
    noise = rng.normal(0, sigma * np.sqrt(1 - phi**2), n)
    return lfilter([1.0], [1.0, -phi], noise)


def _dewpoint(t, rh):
    a, b = 17.625, 243.04
    g = np.log(np.clip(rh, 1, 100) / 100) + a * t / (b + t)
    return b * g / (a - g)


def _rh(t, td):
    a, b = 17.625, 243.04
    return 100 * np.exp(a * td / (b + td) - a * t / (b + t))


def generate(icao: str, start: str = "2024-01-01", end: str = "2026-01-31 23:00", seed: int | None = None) -> dict:
    """Return an Open-Meteo-shaped payload for one airport."""
    c = CLIMATE[icao]
    ap = config.AIRPORTS[icao]
    rng = np.random.default_rng(seed if seed is not None else sum(map(ord, icao)) * 7)
    idx = pd.date_range(start, end, freq="h")
    n = len(idx)
    doy = idx.dayofyear.values.astype(float)
    hour = idx.hour.values.astype(float)

    t_mean = _seasonal(c["T"], doy)
    rh_mean = _seasonal(c["RH"], doy)
    dtr = _seasonal(c["DTR"], doy)
    rain_p = _seasonal(c["RAIN"], doy)
    cloud_m = _seasonal(c["CLOUD"], doy)
    wdir_m = _seasonal(c["WDIR"], doy, circular=True)
    wspd_m = _seasonal(c["WSPD"], doy)
    fog_p = _seasonal(c["FOG"], doy)
    haze_p = _seasonal(c["HAZE"], doy)
    ts_p = _seasonal(c["TS"], doy)
    mslp_m = _seasonal(c["MSLP"], doy)

    # slow "weather system" anomalies
    t_anom = _ar1(n, 60, 1.6, rng)
    q_anom = _ar1(n, 48, 1.4, rng)
    p_anom = _ar1(n, 72, 2.2, rng)
    w_anom = _ar1(n, 24, 0.30, rng)
    d_anom = _ar1(n, 18, 30.0, rng)
    c_anom = _ar1(n, 30, 18.0, rng)

    diurnal = np.cos(2 * np.pi * (hour - 15) / 24)          # +1 at 15h, -1 at 03h
    morning = np.exp(-0.5 * ((hour - 6) / 2.0) ** 2)         # peaks ~06h
    afternoon = np.exp(-0.5 * ((hour - 16) / 2.5) ** 2)      # peaks ~16h

    # --- rain spells: 2-state Markov chain whose stationary rate = rain_p
    stay = 0.70
    rain_mod = np.clip(rain_p * np.exp(q_anom / 2.5) * (0.7 + 0.6 * afternoon), 0, 0.6)
    start_p = rain_mod * (1 - stay) / (1 - rain_mod)
    u = rng.random(n)
    raining = np.zeros(n, dtype=bool)
    for i in range(1, n):
        raining[i] = u[i] < (stay if raining[i - 1] else start_p[i])
    monsoonish = rain_p > 0.08
    precip = np.where(raining, rng.gamma(0.9, np.where(monsoonish, 3.0, 1.8)), 0.0)

    # --- cloud
    cloud = np.clip(cloud_m + c_anom + 35 * raining, 0, 100)
    low_share = np.clip(0.35 + 0.4 * (rh_mean / 100 - 0.5) + 0.35 * raining + rng.normal(0, 0.08, n), 0.05, 1)
    cloud_low = np.clip(cloud * low_share, 0, 100)

    # --- temperature & moisture
    heating = dtr / 2 * diurnal * (1 - 0.45 * cloud / 100 * (diurnal > 0))
    temp = t_mean + t_anom + heating - 2.0 * raining
    td_mean = _dewpoint(t_mean, rh_mean)
    td = td_mean + q_anom + 0.4 * diurnal + 1.2 * raining
    min_spread = np.abs(rng.normal(0, 0.6, n)) + 0.1
    td = np.minimum(td, temp - min_spread)
    td = np.where(raining, np.maximum(td, temp - 1.5), td)
    rh = _rh(temp, td)

    pressure = mslp_m + p_anom + 1.1 * np.cos(2 * np.pi * (hour - 10) / 12)

    # --- wind
    wspd = np.clip(wspd_m * (1 + 0.45 * diurnal) * np.exp(w_anom) + rng.normal(0, 0.4, n), 0, None)
    wdir = (wdir_m + d_anom + (35 * afternoon if ap.coastal else 0)) % 360
    gust = wspd * rng.uniform(1.35, 1.7, n)

    # --- convection / thunderstorms
    cape = np.clip(((td - 16) * 210 + (temp - 27) * 140) * (0.4 + 0.6 * np.clip(diurnal + 0.4, 0, 1.4)), 0, None)
    cape = cape * (0.6 + ts_p) + rng.normal(0, 80, n)
    cape = np.clip(cape, 0, 5000)
    ts_trigger = ts_p * 0.055 * (0.3 + afternoon) / (1 + np.exp(-(cape - 1300) / 350))
    ts_start = rng.random(n) < ts_trigger
    thunder = ts_start.copy()
    for lag in (1, 2):  # storms last ~1-3 hours
        thunder[lag:] |= ts_start[:-lag] & (rng.random(n - lag) < 0.6)
    precip = np.where(thunder, np.maximum(precip, rng.gamma(2.0, 4.0, n)), precip)
    gust = np.where(thunder, gust + rng.uniform(6, 16, n), gust)
    wspd = np.where(thunder, wspd + rng.uniform(2, 6, n), wspd)
    wdir = np.where(thunder, (wdir + rng.normal(0, 60, n)) % 360, wdir)
    temp = np.where(thunder, temp - rng.uniform(2, 6, n), temp)
    td = np.minimum(td, temp - 0.2)
    rh = _rh(temp, td)
    cloud = np.where(thunder, np.maximum(cloud, 90), cloud)
    cloud_low = np.where(thunder, np.maximum(cloud_low, 75), cloud_low)
    raining = raining | thunder

    # --- visibility: humidity + haze + mist + rain + fog
    spread = temp - td
    vis = 30000 * np.exp(-0.018 * np.clip(rh - 30, 0, None)) * rng.lognormal(0, 0.12, n)
    haze_factor = 1 - haze_p * 0.75 * (0.5 + 0.5 * morning) * np.exp(-wspd / 5)
    vis = vis * np.clip(haze_factor, 0.15, 1)
    mist_index = np.clip((3.5 - spread) / 3.5, 0, 1) * np.clip(0.3 + morning, 0, 1) * np.clip(fog_p + haze_p + 0.2, 0, 1)
    vis = np.where(mist_index > 0.35, np.minimum(vis, 1500 + 9000 * (1 - mist_index) * rng.lognormal(0, 0.2, n)), vis)
    rain_vis = 12000 / (1 + 0.9 * precip)
    vis = np.where(raining, np.minimum(vis, rain_vis * rng.lognormal(0, 0.2, n)), vis)

    # fog forms on calm, near-saturated nights and persists until the morning burn-off
    fog_index = fog_p * np.clip((2.2 - spread) / 2.2, 0, 1) * np.clip((3.5 - wspd) / 3.5, 0, 1) * (0.25 + morning) * np.exp(q_anom / 2)
    fog_thr = 0.42 + 0.22 * _ar1(n, 36, 1.0, rng)
    daytime = (hour >= 10) & (hour <= 17)
    fog = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if raining[i] or daytime[i]:
            continue
        fog[i] = fog_index[i] > (fog_thr[i] * 0.45 if fog[i - 1] else fog_thr[i])
    fog_strength = pd.Series(fog_index).rolling(3, min_periods=1, center=True).mean().to_numpy()
    fog_vis = np.clip(1800 * np.exp(-3.2 * fog_strength) * rng.lognormal(0, 0.25, n), 50, 1500)
    vis = np.where(fog, np.minimum(vis, fog_vis), vis)
    vis = np.clip(vis, 50, 24140)
    cloud_low = np.where(fog, 100, cloud_low)
    cloud = np.maximum(cloud, cloud_low)

    # --- WMO weather code
    code = np.select([cloud < 20, cloud < 50, cloud < 80], [0, 1, 2], 3)
    code = np.where(fog, 45, code)
    code = np.where(raining & (precip < 1), 61, code)
    code = np.where(raining & (precip >= 1) & (precip < 4), 63, code)
    code = np.where(raining & (precip >= 4), 65, code)
    code = np.where(thunder, 95, code)

    hourly = {
        "time": idx.strftime("%Y-%m-%dT%H:%M").tolist(),
        "temperature_2m": np.round(temp, 1),
        "relative_humidity_2m": np.round(np.clip(rh, 1, 100)).astype(int),
        "dew_point_2m": np.round(td, 1),
        "pressure_msl": np.round(pressure, 1),
        "cloud_cover": np.round(cloud).astype(int),
        "cloud_cover_low": np.round(cloud_low).astype(int),
        "visibility": np.round(vis, -1),
        "wind_speed_10m": np.round(wspd, 2),
        "wind_direction_10m": np.round(wdir).astype(int),
        "wind_gusts_10m": np.round(gust, 2),
        "precipitation": np.round(precip, 1),
        "cape": np.round(cape, -1),
        "weather_code": code.astype(int),
    }

    # simulated sensor faults so the quality checks have something to catch
    fault_rng = np.random.default_rng(rng.integers(1e9))
    hourly = {k: (v.astype(float) if k != "time" else v) for k, v in hourly.items()}
    for key in ["temperature_2m", "dew_point_2m", "pressure_msl", "wind_speed_10m", "visibility"]:
        miss = fault_rng.random(n) < 0.003
        hourly[key][miss] = np.nan
    spikes = fault_rng.choice(n, size=12, replace=False)
    hourly["temperature_2m"][spikes[:6]] = 99.9
    hourly["relative_humidity_2m"][spikes[6:]] = -1

    out = {k: (v if k == "time" else [None if np.isnan(x) else float(x) for x in v]) for k, v in hourly.items()}
    dup = int(fault_rng.integers(min(100, n // 4), max(n - 100, n // 2)))  # one duplicated timestamp
    for k in out:
        out[k].insert(dup, out[k][dup])

    return {
        "latitude": ap.lat,
        "longitude": ap.lon,
        "elevation": ap.elevation_m,
        "timezone": config.TIMEZONE,
        "generator": "atmos.ingest.sample (offline climatology-driven sample data)",
        "hourly_units": {
            "temperature_2m": "°C", "relative_humidity_2m": "%", "dew_point_2m": "°C",
            "pressure_msl": "hPa", "cloud_cover": "%", "cloud_cover_low": "%", "visibility": "m",
            "wind_speed_10m": "m/s", "wind_direction_10m": "°", "wind_gusts_10m": "m/s",
            "precipitation": "mm", "cape": "J/kg", "weather_code": "wmo code",
        },
        "hourly": out,
    }

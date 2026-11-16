"""Medallion data pipeline: bronze (raw JSON) -> silver (clean) -> gold (features).

bronze  untouched API responses, one JSON file per airport per pull
silver  one tidy hourly table, validated, gaps filled, aviation fields derived
gold    model-ready feature table with lag/trend features and 3-hour-ahead targets
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from atmos import config
from atmos.aviation.rules import CATEGORIES, flight_category_vec

RENAME = {
    "temperature_2m": "temperature_c",
    "relative_humidity_2m": "humidity_pct",
    "dew_point_2m": "dewpoint_c",
    "pressure_msl": "pressure_msl_hpa",
    "cloud_cover": "cloud_cover_pct",
    "cloud_cover_low": "cloud_low_pct",
    "visibility": "visibility_m",
    "wind_speed_10m": "wind_speed_ms",
    "wind_direction_10m": "wind_direction_deg",
    "wind_gusts_10m": "wind_gust_ms",
    "precipitation": "precip_mm",
    "cape": "cape_jkg",
    "weather_code": "weather_code",
}

# physically plausible ranges for Indian airports; anything outside is a sensor/feed fault
VALID_RANGE = {
    "temperature_c": (-10, 52),
    "dewpoint_c": (-30, 35),
    "humidity_pct": (0, 100),
    "pressure_msl_hpa": (950, 1050),
    "cloud_cover_pct": (0, 100),
    "cloud_low_pct": (0, 100),
    "visibility_m": (0, 50000),
    "wind_speed_ms": (0, 60),
    "wind_direction_deg": (0, 360),
    "wind_gust_ms": (0, 80),
    "precip_mm": (0, 300),
    "cape_jkg": (0, 8000),
}
MAX_GAP_FILL_H = 3


# ---------------------------------------------------------------- silver
def bronze_to_frame(payload: dict, icao: str) -> pd.DataFrame:
    df = pd.DataFrame(payload["hourly"]).rename(columns=RENAME)
    df["time"] = pd.to_datetime(df["time"])
    df.insert(0, "icao", icao)
    return df


def estimate_ceiling_ft(df: pd.DataFrame) -> np.ndarray:
    """Cloud-base estimate: 600 ft + ~410 ft per C of temperature/dew-point spread
    (lifting-condensation-level rule). A ceiling exists only with broken/overcast
    low cloud (>= 60 %); otherwise it is reported as unlimited (99999 ft)."""
    spread = (df["temperature_c"] - df["dewpoint_c"]).clip(lower=0).to_numpy()
    lcl = 600 + 410 * spread
    low = df["cloud_low_pct"].to_numpy()
    total = df["cloud_cover_pct"].to_numpy()
    rain = df["precip_mm"].to_numpy() > 0
    heavy = df["precip_mm"].to_numpy() >= 4
    vis = df["visibility_m"].to_numpy()

    ceiling = np.full(len(df), 99999.0)
    mid = total >= 75                       # overcast but the cloud is high
    ceiling[mid] = np.maximum(lcl[mid], 3500) + 3000
    bkn = low >= 60                         # broken / overcast low cloud
    ceiling[bkn] = np.clip(lcl[bkn], 200, 6500)
    ceiling[bkn & rain] = np.maximum(ceiling[bkn & rain] * 0.85, 400)
    ceiling[bkn & heavy] = np.minimum(ceiling[bkn & heavy], 900)
    fog = (vis < 1000) & (low >= 90)        # in fog the ceiling is the vertical visibility
    ceiling[fog] = np.minimum(ceiling[fog], np.clip(vis[fog] * 0.35, 100, 400))
    return np.where(ceiling >= 99999, 99999, np.round(ceiling, -1))


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Validate one airport's hourly table and return it with a QC summary."""
    report = {"rows_in": int(len(df))}
    df = df.sort_values("time")
    dup = df.duplicated("time", keep="first")
    report["duplicates_removed"] = int(dup.sum())
    df = df[~dup].set_index("time")

    report["missing_in"] = int(df[list(VALID_RANGE)].isna().sum().sum())
    out_of_range = 0
    for col, (lo, hi) in VALID_RANGE.items():
        bad = (df[col] < lo) | (df[col] > hi)
        out_of_range += int(bad.sum())
        df.loc[bad, col] = np.nan
    bad_td = df["dewpoint_c"] > df["temperature_c"] + 0.5   # dew point can never exceed temperature
    out_of_range += int(bad_td.sum())
    df.loc[bad_td, "dewpoint_c"] = np.nan
    report["out_of_range_flagged"] = out_of_range

    # reindex to a complete hourly clock, then fill short gaps only
    full = pd.date_range(df.index.min(), df.index.max(), freq="h")
    report["hours_missing_from_feed"] = int(len(full) - len(df))
    df = df.reindex(full)
    df["icao"] = df["icao"].ffill().bfill()
    num = [c for c in VALID_RANGE if c != "wind_direction_deg"]
    before = int(df[num].isna().sum().sum())
    df[num] = df[num].interpolate(method="time", limit=MAX_GAP_FILL_H, limit_area="inside")
    df["wind_direction_deg"] = df["wind_direction_deg"].ffill(limit=MAX_GAP_FILL_H)
    df["weather_code"] = df["weather_code"].ffill(limit=MAX_GAP_FILL_H)
    a, b = 17.625, 243.04   # Magnus formula: recompute humidity where it was rejected
    rh_calc = 100 * np.exp(a * df["dewpoint_c"] / (b + df["dewpoint_c"]) - a * df["temperature_c"] / (b + df["temperature_c"]))
    df["humidity_pct"] = df["humidity_pct"].fillna(rh_calc.round())
    report["values_filled"] = before - int(df[num].isna().sum().sum())
    df = df.dropna(subset=["temperature_c", "dewpoint_c", "visibility_m", "wind_speed_ms", "pressure_msl_hpa"])
    report["rows_out"] = int(len(df))

    df["ceiling_ft"] = estimate_ceiling_ft(df)
    df["flight_category"] = flight_category_vec(df["visibility_m"], df["ceiling_ft"])
    df["thunder"] = df["weather_code"].isin([95, 96, 99]).astype(int)
    df.index.name = "time"
    return df.reset_index(), report


def build_silver(bronze_dir: Path = config.BRONZE, silver_dir: Path = config.SILVER) -> tuple[pd.DataFrame, dict]:
    frames, qc = [], {}
    for icao in config.AIRPORTS:
        files = sorted((bronze_dir / icao).glob("*.json"))
        if not files:
            continue
        raw = pd.concat([bronze_to_frame(json.loads(f.read_text()), icao) for f in files], ignore_index=True)
        clean_df, qc[icao] = clean(raw)
        frames.append(clean_df)
    silver = pd.concat(frames, ignore_index=True)
    silver_dir.mkdir(parents=True, exist_ok=True)
    silver.to_parquet(silver_dir / "observations.parquet", index=False)
    (silver_dir / "quality_report.json").write_text(json.dumps(qc, indent=2))
    return silver, qc


# ---------------------------------------------------------------- gold
def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Feature engineering for one airport (time-sorted)."""
    df = df.sort_values("time").copy()
    df["spread_c"] = df["temperature_c"] - df["dewpoint_c"]                 # small spread -> fog / low cloud
    df["log_vis"] = np.log10(df["visibility_m"].clip(lower=10))
    df["log_ceiling"] = np.log10(df["ceiling_ft"].clip(lower=10))
    rad = np.radians(df["wind_direction_deg"])
    df["wind_u"] = -df["wind_speed_ms"] * np.sin(rad)                         # east-west wind component
    df["wind_v"] = -df["wind_speed_ms"] * np.cos(rad)                         # north-south wind component
    df["gust_excess"] = df["wind_gust_ms"] - df["wind_speed_ms"]
    for lag in (1, 3, 6):                                                     # how fast things are changing
        for col in ("temperature_c", "dewpoint_c", "pressure_msl_hpa", "log_vis", "spread_c", "cloud_low_pct"):
            df[f"{col}_d{lag}h"] = df[col] - df[col].shift(lag)
    df["precip_6h"] = df["precip_mm"].rolling(6, min_periods=1).sum()
    df["cape_max_6h"] = df["cape_jkg"].rolling(6, min_periods=1).max()
    df["thunder_6h"] = df["thunder"].rolling(6, min_periods=1).max()
    df["cat_now"] = df["flight_category"].map({c: i for i, c in enumerate(CATEGORIES)})
    hour = df["time"].dt.hour
    doy = df["time"].dt.dayofyear
    df["hour_sin"], df["hour_cos"] = np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24)
    df["doy_sin"], df["doy_cos"] = np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)
    ap = config.AIRPORTS[df["icao"].iloc[0]]
    df["elevation_m"] = ap.elevation_m
    df["coastal"] = int(ap.coastal)
    df["lat"] = ap.lat
    return df


def add_targets(df: pd.DataFrame, horizon: int = config.FORECAST_HORIZON_H) -> pd.DataFrame:
    df = df.copy()
    future_ok = df["time"].shift(-horizon) == df["time"] + pd.Timedelta(hours=horizon)
    df["y_category"] = df["flight_category"].shift(-horizon).where(future_ok)
    df["y_visibility_m"] = df["visibility_m"].shift(-horizon).where(future_ok)
    nxt = pd.concat([df["thunder"].shift(-k) for k in range(1, horizon + 1)], axis=1)
    df["y_thunder"] = nxt.max(axis=1).where(future_ok)
    return df


def feature_columns(df: pd.DataFrame) -> list[str]:
    skip = {"time", "icao", "flight_category", "weather_code", "thunder"}
    return [c for c in df.columns if c not in skip and not c.startswith("y_")]


def build_gold(silver: pd.DataFrame, gold_dir: Path = config.GOLD) -> pd.DataFrame:
    parts = [add_targets(add_features(g)) for _, g in silver.groupby("icao")]
    gold = pd.concat(parts, ignore_index=True)
    feats = feature_columns(gold)
    gold = gold.dropna(subset=feats)
    gold_dir.mkdir(parents=True, exist_ok=True)
    gold.to_parquet(gold_dir / "features.parquet", index=False)
    (gold_dir / "feature_list.json").write_text(json.dumps(feats, indent=2))
    return gold

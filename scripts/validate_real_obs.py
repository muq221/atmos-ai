"""Check the modelling approach on REAL airport observations.

The NREL TMY3 file for Greensboro Piedmont Triad International Airport (KGSO)
ships inside the `pvlib` package. It holds 8,760 hourly observations including
measured visibility and cloud ceiling - exactly what flight categories need.

We rebuild the same kind of features, label flight categories from the measured
visibility/ceiling, and score the 3-hour-ahead classifier with leave-one-month-out
cross-validation against the persistence baseline.

    python scripts/validate_real_obs.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pvlib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score

from atmos.aviation.rules import flight_category_vec

OUT = Path(__file__).resolve().parent.parent / "models" / "real_obs_validation.json"


def load_kgso() -> pd.DataFrame:
    path = os.path.join(os.path.dirname(pvlib.__file__), "data", "723170TYA.CSV")
    raw, meta = pvlib.iotools.read_tmy3(path, map_variables=False)
    df = pd.DataFrame({
        "temperature_c": raw["Dry-bulb (C)"].values,
        "dewpoint_c": raw["Dew-point (C)"].values,
        "humidity_pct": raw["RHum (%)"].values,
        "pressure_hpa": raw["Pressure (mbar)"].values,
        "wind_dir": raw["Wdir (degrees)"].values,
        "wind_speed_ms": raw["Wspd (m/s)"].values,
        "visibility_m": raw["Hvis (m)"].values,
        "ceiling_m": raw["CeilHgt (m)"].values,
        "cloud_tenths": raw["TotCld (tenths)"].values,
        "opaque_tenths": raw["OpqCld (tenths)"].values,
        "precip_mm": raw["Lprecip depth (mm)"].values,
    })
    df["month"] = raw.index.month
    df["hour"] = raw.index.hour
    df["ceiling_ft"] = np.where(df["ceiling_m"] >= 77777, 99999, df["ceiling_m"] * 3.28084)
    df["category"] = flight_category_vec(df["visibility_m"], df["ceiling_ft"])
    return df, meta


def features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["spread"] = df["temperature_c"] - df["dewpoint_c"]
    df["log_vis"] = np.log10(df["visibility_m"].clip(lower=10))
    df["log_ceil"] = np.log10(df["ceiling_ft"].clip(lower=10))
    for lag in (1, 3, 6):
        for c in ("temperature_c", "dewpoint_c", "pressure_hpa", "log_vis", "spread", "log_ceil"):
            df[f"{c}_d{lag}"] = df.groupby("month")[c].diff(lag)
    df["hour_sin"], df["hour_cos"] = np.sin(2 * np.pi * df.hour / 24), np.cos(2 * np.pi * df.hour / 24)
    df["y"] = df.groupby("month")["category"].shift(-3)
    return df.dropna()


def main() -> None:
    raw, meta = load_kgso()
    df = features(raw)
    feats = [c for c in df.columns if c not in {"category", "y", "month", "ceiling_m"}]
    preds, truth, persist = [], [], []
    for m in range(1, 13):  # leave-one-month-out
        tr, te = df[df.month != m], df[df.month == m]
        model = RandomForestClassifier(n_estimators=250, min_samples_leaf=4, class_weight="balanced_subsample",
                                       n_jobs=-1, random_state=42).fit(tr[feats], tr["y"])
        preds += list(model.predict(te[feats]))
        truth += list(te["y"])
        persist += list(te["category"])
    res = {
        "station": meta["Name"].strip('"'),
        "source": "NREL TMY3 723170 (bundled with pvlib)",
        "hours": len(df),
        "class_share": raw["category"].value_counts(normalize=True).round(3).to_dict(),
        "model_accuracy": round(accuracy_score(truth, preds), 4),
        "model_macro_f1": round(f1_score(truth, preds, average="macro"), 4),
        "persistence_accuracy": round(accuracy_score(truth, persist), 4),
        "persistence_macro_f1": round(f1_score(truth, persist, average="macro"), 4),
    }
    OUT.write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()

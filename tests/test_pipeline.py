import numpy as np

from atmos.ingest.sample import generate
from atmos.pipeline.layers import VALID_RANGE, add_features, add_targets, bronze_to_frame, clean


def _silver():
    payload = generate("VOHS", "2025-01-01", "2025-01-10 23:00", seed=1)
    return clean(bronze_to_frame(payload, "VOHS"))


def test_sample_has_open_meteo_shape():
    payload = generate("VIDP", "2025-01-01", "2025-01-02 23:00", seed=1)
    assert {"time", "temperature_2m", "visibility", "wind_speed_10m"} <= set(payload["hourly"])


def test_clean_removes_duplicates_and_bad_values():
    df, qc = _silver()
    assert df["time"].is_unique
    assert qc["duplicates_removed"] >= 1
    for col, (lo, hi) in VALID_RANGE.items():
        s = df[col].dropna()
        assert s.between(lo, hi).all(), col
    assert (df["dewpoint_c"] <= df["temperature_c"] + 0.5).all()


def test_targets_are_three_hours_ahead():
    df, _ = _silver()
    g = add_targets(add_features(df))
    i = 50
    assert g["y_category"].iloc[i] == g["flight_category"].iloc[i + 3]
    assert np.isfinite(g["spread_c"]).all()

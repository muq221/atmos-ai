"""Central configuration for Atmos AI.

Airports, runway headings and paths live here so every layer
(ingestion, pipeline, models, API) reads the same values.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("ATMOS_DATA_DIR", ROOT / "data"))
BRONZE = DATA_DIR / "bronze"
SILVER = DATA_DIR / "silver"
GOLD = DATA_DIR / "gold"
MODEL_DIR = Path(os.getenv("ATMOS_MODEL_DIR", ROOT / "models"))

# "openmeteo" pulls live/archive data, "sample" uses the offline generator
DATA_SOURCE = os.getenv("ATMOS_SOURCE", "sample")

# Demo clock: in sample mode the API treats this instant as "now" (IST)
DEMO_NOW = os.getenv("ATMOS_DEMO_NOW", "2025-12-11 06:00")
TIMEZONE = "Asia/Kolkata"

TRAIN_START = "2024-01-01"
TRAIN_END = "2025-08-31 23:00"
TEST_START = "2025-09-01"
TEST_END = "2025-12-31 23:00"

FORECAST_HORIZON_H = 3  # models predict conditions 3 hours ahead


@dataclass(frozen=True)
class Airport:
    icao: str
    iata: str
    name: str
    city: str
    lat: float
    lon: float
    elevation_m: int
    runways: tuple[int, ...] = field(default_factory=tuple)  # magnetic headings, one per runway direction pair
    coastal: bool = False


AIRPORTS: dict[str, Airport] = {
    a.icao: a
    for a in [
        Airport("VOHS", "HYD", "Rajiv Gandhi International", "Hyderabad", 17.2403, 78.4294, 617, (90, 270)),
        Airport("VIDP", "DEL", "Indira Gandhi International", "Delhi", 28.5562, 77.1000, 237, (100, 280, 110, 290)),
        Airport("VABB", "BOM", "Chhatrapati Shivaji Maharaj International", "Mumbai", 19.0896, 72.8656, 11, (90, 270, 140, 320), True),
        Airport("VOBL", "BLR", "Kempegowda International", "Bengaluru", 13.1986, 77.7066, 915, (90, 270)),
        Airport("VOMM", "MAA", "Chennai International", "Chennai", 12.9941, 80.1709, 16, (70, 250, 120, 300), True),
        Airport("VECC", "CCU", "Netaji Subhas Chandra Bose International", "Kolkata", 22.6547, 88.4467, 5, (10, 190), True),
    ]
}

# Advisory thresholds (decision support only - not a replacement for IMD METAR/TAF)
CROSSWIND_CAUTION_KT = 15
CROSSWIND_ADVERSE_KT = 25
GUST_CAUTION_KT = 25
TS_PROB_CAUTION = 0.30
TS_PROB_ADVERSE = 0.60

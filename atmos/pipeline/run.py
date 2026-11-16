"""Pipeline entry point.

    python -m atmos.pipeline.run                 # source from ATMOS_SOURCE (default: sample)
    python -m atmos.pipeline.run --source openmeteo --start 2024-01-01 --end 2025-12-31
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import date, timedelta

from atmos import config
from atmos.ingest import openmeteo, sample
from atmos.pipeline.layers import build_gold, build_silver


def ingest(source: str, start: date, end: date) -> None:
    for icao, ap in config.AIRPORTS.items():
        if source == "sample":
            payload = sample.generate(icao, start.isoformat(), f"{end.isoformat()} 23:00")
            openmeteo.save_bronze(payload, icao, f"sample_{start}_{end}")
        else:
            # pull in 3-month chunks to stay well inside the API limits
            cur = start
            while cur <= end:
                chunk_end = min(cur + timedelta(days=90), end)
                payload = openmeteo.history_hourly(ap, cur, chunk_end)
                openmeteo.save_bronze(payload, icao, f"history_{cur}_{chunk_end}")
                cur = chunk_end + timedelta(days=1)
                time.sleep(1)
        print(f"  bronze  {icao}  ok")


def main() -> None:
    p = argparse.ArgumentParser(description="Atmos AI data pipeline")
    p.add_argument("--source", default=config.DATA_SOURCE, choices=["sample", "openmeteo"])
    p.add_argument("--start", default="2024-01-01")
    p.add_argument("--end", default="2026-01-31")
    p.add_argument("--skip-ingest", action="store_true")
    a = p.parse_args()

    t0 = time.time()
    print(f"[1/3] ingest  source={a.source}  {a.start} -> {a.end}")
    if not a.skip_ingest:
        ingest(a.source, date.fromisoformat(a.start), date.fromisoformat(a.end))
    print("[2/3] silver  validating and cleaning")
    silver, qc = build_silver()
    for icao, r in qc.items():
        print(f"  silver  {icao}  rows={r['rows_out']:>6}  dup={r['duplicates_removed']}  "
              f"bad={r['out_of_range_flagged']:>3}  filled={r['values_filled']:>3}")
    print("[3/3] gold    feature engineering")
    gold = build_gold(silver)
    print(f"  gold    {len(gold):,} rows x {len(json.loads((config.GOLD / 'feature_list.json').read_text()))} features")
    print(f"done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()

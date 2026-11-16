from atmos import config
from atmos.aviation.rules import advisory, best_runway, flight_category, wind_components


def test_flight_category_thresholds():
    assert flight_category(10000, 99999) == "VFR"
    assert flight_category(6000, 99999) == "MVFR"   # 3-5 statute miles
    assert flight_category(10000, 2500) == "MVFR"   # ceiling 1000-3000 ft
    assert flight_category(3000, 99999) == "IFR"
    assert flight_category(10000, 800) == "IFR"
    assert flight_category(400, 99999) == "LIFR"    # dense fog
    assert flight_category(10000, 300) == "LIFR"


def test_wind_components():
    hw, xw = wind_components(270, 20, 270)   # straight down the runway
    assert hw == 20 and xw == 0
    hw, xw = wind_components(360, 20, 270)   # pure crosswind
    assert abs(hw) < 0.1 and xw == 20
    hw, _ = wind_components(90, 10, 270)     # tailwind
    assert hw == -10


def test_best_runway_picks_headwind():
    r = best_runway(280, 15, (100, 280))
    assert r["best"]["runway"] == "28"


def test_advisory_levels():
    ap = config.AIRPORTS["VIDP"]
    calm = {"flight_category": "VFR", "visibility_m": 10000, "wind_speed_ms": 2, "wind_gust_ms": 3,
            "wind_direction_deg": 280, "temperature_c": 25, "pressure_msl_hpa": 1012}
    assert advisory(calm, "VFR", 0.0, ap).level == "NORMAL"
    fog = calm | {"flight_category": "LIFR", "visibility_m": 300}
    assert advisory(fog, "LIFR", 0.0, ap).level == "ADVERSE"
    storm = calm | {"wind_speed_ms": 15, "wind_gust_ms": 22, "wind_direction_deg": 10}
    assert advisory(storm, "MVFR", 0.7, ap).level == "ADVERSE"

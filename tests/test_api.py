import pytest
from fastapi.testclient import TestClient

from atmos import config

pytestmark = pytest.mark.skipif(not (config.MODEL_DIR / "atmos_models.joblib").exists(),
                                reason="run the pipeline and training first")


@pytest.fixture(scope="module")
def client():
    from atmos.api.app import app
    return TestClient(app)


def test_health(client):
    assert client.get("/api/v1/health").json()["status"] == "ok"


def test_unknown_airport_is_404(client):
    assert client.get("/api/v1/airports/XXXX/current").status_code == 404


@pytest.mark.parametrize("icao", list(config.AIRPORTS))
def test_airport_endpoints(client, icao):
    cur = client.get(f"/api/v1/airports/{icao}/current").json()
    assert cur["flight_category"] in {"VFR", "MVFR", "IFR", "LIFR"}
    adv = client.get(f"/api/v1/airports/{icao}/advisory").json()
    assert adv["level"] in {"NORMAL", "CAUTION", "ADVERSE"}
    fc = client.get(f"/api/v1/airports/{icao}/forecast?hours=6").json()
    assert len(fc) == 7 and abs(sum(fc[0]["probabilities"].values()) - 1) < 0.01


def test_network_lists_all_airports(client):
    assert len(client.get("/api/v1/network").json()) == len(config.AIRPORTS)

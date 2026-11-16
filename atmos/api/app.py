"""Atmos AI REST API + dashboard.

    uvicorn atmos.api.app:app --reload
    open http://127.0.0.1:8000        (dashboard)
    open http://127.0.0.1:8000/docs   (interactive API docs)
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from atmos import config
from atmos.api import service

STATIC = Path(__file__).resolve().parent.parent / "dashboard" / "static"

app = FastAPI(
    title="Atmos AI - Weather Intelligence for Aviation",
    version="1.0.0",
    description="Atmospheric conditions, 3-hour ML forecasts and operational advisories for Indian airports.",
    docs_url=None,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def _airport(icao: str) -> str:
    icao = icao.upper()
    if icao not in config.AIRPORTS:
        raise HTTPException(status_code=404, detail=f"Unknown airport {icao}. Try one of {sorted(config.AIRPORTS)}")
    return icao


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(STATIC / "index.html")


@app.get("/docs", include_in_schema=False)
def docs():
    return get_swagger_ui_html(openapi_url=app.openapi_url, title="Atmos AI - API docs",
                               swagger_js_url="/static/vendor/swagger-ui-bundle.js",
                               swagger_css_url="/static/vendor/swagger-ui.css")


@app.get("/api/v1/health", tags=["system"])
def health():
    m = service.model_metrics()
    return {"status": "ok", "data_source": config.DATA_SOURCE, "now": service.now().isoformat(),
            "model_trained_at": m["trained_at"], "airports": len(config.AIRPORTS)}


@app.get("/api/v1/airports", tags=["airports"])
def airports():
    return [{"icao": a.icao, "iata": a.iata, "name": a.name, "city": a.city, "lat": a.lat, "lon": a.lon,
             "elevation_m": a.elevation_m, "runways": [f"{round(h / 10):02d}" for h in a.runways]}
            for a in config.AIRPORTS.values()]


@app.get("/api/v1/airports/{icao}/current", tags=["weather"])
def current(icao: str):
    """Latest observed atmospheric conditions and flight category."""
    return service.current(_airport(icao))


@app.get("/api/v1/airports/{icao}/forecast", tags=["weather"])
def forecast(icao: str, hours: int = Query(24, ge=1, le=30)):
    """ML predictions issued every hour, each valid 3 hours ahead."""
    return service.forecast(_airport(icao), hours)


@app.get("/api/v1/airports/{icao}/advisory", tags=["aviation"])
def advisory(icao: str):
    """NORMAL / CAUTION / ADVERSE operational advisory with reasons and runway winds."""
    return service.get_advisory(_airport(icao))


@app.get("/api/v1/airports/{icao}/briefing", tags=["aviation"])
def briefing(icao: str):
    """Plain-language briefing for dispatchers and flight crew."""
    return service.briefing(_airport(icao))


@app.get("/api/v1/network", tags=["aviation"])
def network():
    """One-line status for every airport - used by the dashboard overview."""
    return service.network()


@app.get("/api/v1/models", tags=["system"])
def models():
    """Training metadata and test-set metrics of the deployed models."""
    return service.model_metrics()

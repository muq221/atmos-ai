"""Build the GitHub Pages demo into docs/.

It calls every API endpoint once (sample-data mode), saves the JSON responses,
and copies the dashboard so it reads those files instead of a live server.

    python scripts/build_static_demo.py
Then push, and enable GitHub Pages: Settings -> Pages -> main branch, /docs folder.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # run from anywhere

from fastapi.testclient import TestClient  # noqa: E402

from atmos import config  # noqa: E402
from atmos.api.app import app  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
STATIC = ROOT / "atmos" / "dashboard" / "static"


def save(client: TestClient, path: str, out: Path) -> None:
    r = client.get("/api/v1" + path)
    r.raise_for_status()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(r.json(), indent=1))


def main() -> None:
    client = TestClient(app)
    data = DOCS / "data"
    if data.exists():
        shutil.rmtree(data)
    for p in ["/health", "/models", "/airports", "/network"]:
        save(client, p, data / f"{p.strip('/')}.json")
    for icao in config.AIRPORTS:
        for part in ["current", "advisory", "briefing"]:
            save(client, f"/airports/{icao}/{part}", data / "airports" / icao / f"{part}.json")
        save(client, f"/airports/{icao}/forecast?hours=24", data / "airports" / icao / "forecast.json")

    # dashboard files with relative paths + static flag
    if (DOCS / "static").exists():
        shutil.rmtree(DOCS / "static")
    shutil.copytree(STATIC, DOCS / "static", ignore=shutil.ignore_patterns("index.html"))
    html = (STATIC / "index.html").read_text().replace('href="/static/', 'href="static/').replace('src="/static/', 'src="static/')
    html = html.replace("<head>", "<head>\n  <script>window.ATMOS_STATIC = true;</script>", 1)
    (DOCS / "index.html").write_text(html)

    # read-only API documentation page
    (DOCS / "openapi.json").write_text(json.dumps(app.openapi(), indent=1))
    (DOCS / "api.html").write_text("""<!doctype html>
<html><head><meta charset="utf-8"><title>Atmos AI - API docs</title>
<link rel="stylesheet" href="static/vendor/swagger-ui.css"></head>
<body><div id="ui"></div><script src="static/vendor/swagger-ui-bundle.js"></script>
<script>SwaggerUIBundle({ url: "openapi.json", dom_id: "#ui", supportedSubmitMethods: [] });</script>
</body></html>""")
    (DOCS / ".nojekyll").write_text("")
    print("static demo written to", DOCS)


if __name__ == "__main__":
    main()

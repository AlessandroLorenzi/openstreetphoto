# Server web mappa foto — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CLI `osp-serve` che serve mappa Leaflet full-screen con i nodi foto; click → modale con la foto.

**Architecture:** `src/openstreetphoto/serve.py` (ThreadingHTTPServer stdlib, 3 route) + `src/openstreetphoto/web/index.html` (pagina unica, Leaflet+markercluster da CDN). Filtro Mapillary-only client-side.

**Tech Stack:** stdlib http.server + importlib.resources; Leaflet 1.9.4, Leaflet.markercluster 1.5.3 (unpkg); font Fraunces + IBM Plex Mono (Google Fonts).

## Global Constraints

- Nessuna dipendenza Python nuova.
- Route: `/` → index.html; `/photo-nodes.geojson` → file da CLI; altro → 404.
- Chiavi embeddabili, in priorità: `image`, `wikimedia_commons` (`File:X` → `https://commons.wikimedia.org/wiki/Special:FilePath/<enc(X)>?width=1024`), `panoramax` (→ `https://api.panoramax.xyz/api/pictures/<id>/sd.jpg`).
- Spec: `docs/superpowers/specs/2026-07-03-photo-map-server-design.md`

---

### Task 1: `serve.py` + test

**Files:**
- Create: `src/openstreetphoto/serve.py`, `src/openstreetphoto/web/index.html` (placeholder minimo, sostituito in Task 2)
- Modify: `pyproject.toml` (`osp-serve = "openstreetphoto.serve:main"`)
- Test: `tests/test_serve.py`

**Interfaces:**
- Produces: `make_server(geojson: Path, port: int) -> ThreadingHTTPServer` (porta 0 = effimera, leggere `server.server_address[1]`); `main(argv) -> int`.

- [ ] **Step 1: Test falliti**

`tests/test_serve.py`:

```python
import json
import threading
from pathlib import Path

import pytest
import requests

from openstreetphoto.serve import main, make_server

GEOJSON = {"type": "FeatureCollection", "features": []}


@pytest.fixture()
def server_url(tmp_path):
    geojson = tmp_path / "photo-nodes.geojson"
    geojson.write_text(json.dumps(GEOJSON))
    server = make_server(geojson, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_root_serves_html(server_url):
    resp = requests.get(f"{server_url}/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["Content-Type"]
    assert "leaflet" in resp.text.lower()


def test_geojson_route(server_url):
    resp = requests.get(f"{server_url}/photo-nodes.geojson")
    assert resp.status_code == 200
    assert resp.json()["type"] == "FeatureCollection"


def test_unknown_route_404(server_url):
    assert requests.get(f"{server_url}/altro").status_code == 404


def test_main_missing_geojson_returns_1(tmp_path, capsys):
    rc = main(["--geojson", str(tmp_path / "missing.geojson")])
    assert rc == 1
    assert "errore" in capsys.readouterr().err.lower()
```

- [ ] **Step 2: Run, expect ImportError** — `.venv/bin/pytest tests/test_serve.py -q`

- [ ] **Step 3: Implementa `serve.py` + placeholder html**

`src/openstreetphoto/web/index.html` (placeholder, Task 2 lo sostituisce ma il test su "leaflet" deve già passare):

```html
<!doctype html><html><head><title>openstreetphoto</title></head>
<body>leaflet placeholder</body></html>
```

`src/openstreetphoto/serve.py`:

```python
from __future__ import annotations

import argparse
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path


def _index_html() -> bytes:
    return (resources.files("openstreetphoto") / "web" / "index.html").read_bytes()


def make_server(geojson: Path, port: int) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path in ("/", "/index.html"):
                self._send(200, "text/html; charset=utf-8", _index_html())
            elif self.path == "/photo-nodes.geojson":
                self._send(200, "application/geo+json", geojson.read_bytes())
            else:
                self._send(404, "text/plain; charset=utf-8", b"not found")

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:  # silenzia stderr
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mappa web dei nodi OSM con foto")
    parser.add_argument(
        "--geojson", type=Path, default=Path("data/photo-nodes.geojson")
    )
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    if not args.geojson.exists():
        print(
            f"errore: {args.geojson} non esiste (lancia prima osp-extract)",
            file=sys.stderr,
        )
        return 1
    server = make_server(args.geojson, args.port)
    print(f"in ascolto su http://localhost:{server.server_address[1]}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0
```

`pyproject.toml`: `osp-serve = "openstreetphoto.serve:main"`.

- [ ] **Step 4: Reinstalla, run** — `.venv/bin/pip install -q -e ".[test]" && .venv/bin/pytest -q` → tutti PASS

- [ ] **Step 5: Commit** — `feat: server web osp-serve con route statiche`

---

### Task 2: frontend `index.html`

**Files:**
- Modify: `src/openstreetphoto/web/index.html` (sostituzione completa)

**Interfaces:**
- Consumes: route `/photo-nodes.geojson` (Task 1)
- Produces: pagina completa; nessuna API per altri task.

- [ ] **Step 1: Scrivi il file completo**

Contenuto integrale in `src/openstreetphoto/web/index.html` — mappa full-screen, filtro embeddabili, cluster monocromi, modale-stampa con Fraunces/IBM Plex Mono, palette carta/inchiostro/ocra, Esc/overlay/✕ per chiudere, `onerror` sull'immagine, contatore in alto a destra, focus visibile, `prefers-reduced-motion`. (Il file è il deliverable: vedere il codice nel commit; ~200 righe.)

- [ ] **Step 2: Test suite ancora verde** — `.venv/bin/pytest -q` (il test su "leaflet" ora matcha la pagina vera)

- [ ] **Step 3: Commit** — `feat: frontend mappa con modale foto`

- [ ] **Step 4: Verifica end-to-end nel browser headless (skill verify)** — avvia `osp-serve` sul GeoJSON reale, Playwright: screenshot mappa, click su un marker, screenshot modale, probe (Esc, immagine rotta, 404).

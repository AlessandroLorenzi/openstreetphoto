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

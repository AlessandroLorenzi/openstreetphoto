# Estrazione nodi con foto in GeoJSON — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CLI `osp-extract` che legge il PBF e scrive un GeoJSON con i nodi che hanno tag foto.

**Architecture:** Nuovo modulo `src/openstreetphoto/extract.py`: funzione pura `photo_keys` per il filtro, handler pyosmium (`SimpleHandler`) che accumula Feature, `main()` argparse. Entry point `osp-extract`.

**Tech Stack:** pyosmium 4.3.1 (già installato nel venv), stdlib json/argparse; test pytest con mini file `.osm` XML.

## Global Constraints

- Tag foto: `image`, `panoramax`, `mapillary`, `flickr` (qualunque valore); `wikimedia_commons` solo se il valore inizia per `File:`
- Aggiungere `osmium` alle `dependencies` in `pyproject.toml`
- Output: FeatureCollection, properties = `osm_id`, `photo_keys`, `tags`
- Errori I/O → stderr + exit 1
- Spec: `docs/superpowers/specs/2026-07-03-photo-nodes-extract-design.md`

---

### Task 1: Filtro `photo_keys`

**Files:**
- Create: `src/openstreetphoto/extract.py`
- Test: `tests/test_extract.py`
- Modify: `pyproject.toml` (dependencies += "osmium")

**Interfaces:**
- Produces: `photo_keys(tags: dict[str, str]) -> list[str]` — chiavi foto presenti, in ordine stabile (ordine del set PHOTO_TAGS); lista vuota se nessuna. `PHOTO_TAGS: tuple[str, ...]`.

- [ ] **Step 1: Test falliti**

`tests/test_extract.py`:

```python
from openstreetphoto.extract import photo_keys


def test_photo_keys_matches_each_photo_tag():
    for key in ("image", "panoramax", "mapillary", "flickr"):
        assert photo_keys({key: "qualcosa"}) == [key]


def test_photo_keys_wikimedia_commons_file_only():
    assert photo_keys({"wikimedia_commons": "File:Duomo.jpg"}) == ["wikimedia_commons"]
    assert photo_keys({"wikimedia_commons": "Category:Duomo"}) == []


def test_photo_keys_empty_without_photo_tags():
    assert photo_keys({"amenity": "cafe", "name": "Bar Sport"}) == []


def test_photo_keys_multiple():
    tags = {"image": "http://x/1.jpg", "wikimedia_commons": "File:x.jpg", "name": "x"}
    assert photo_keys(tags) == ["image", "wikimedia_commons"]
```

- [ ] **Step 2: Run, expect ImportError**

Run: `.venv/bin/pytest tests/test_extract.py -q` → FAIL/ERROR ImportError

- [ ] **Step 3: Implementa**

`src/openstreetphoto/extract.py`:

```python
from __future__ import annotations

PHOTO_TAGS = ("image", "panoramax", "mapillary", "flickr", "wikimedia_commons")


def photo_keys(tags: dict[str, str]) -> list[str]:
    keys = []
    for key in PHOTO_TAGS:
        value = tags.get(key)
        if value is None:
            continue
        if key == "wikimedia_commons" and not value.startswith("File:"):
            continue
        keys.append(key)
    return keys
```

In `pyproject.toml`: `dependencies = ["requests", "tqdm", "osmium"]`.

- [ ] **Step 4: Run, expect 4 PASS** → `.venv/bin/pytest tests/test_extract.py -q`

- [ ] **Step 5: Commit** — `git add ... && git commit -m "feat: filtro photo_keys per tag foto OSM"`

---

### Task 2: Estrazione pyosmium + CLI `osp-extract`

**Files:**
- Modify: `src/openstreetphoto/extract.py`, `pyproject.toml` (scripts += osp-extract)
- Test: `tests/test_extract.py`

**Interfaces:**
- Consumes: `photo_keys` (Task 1)
- Produces:
  - `extract_features(pbf: Path) -> list[dict]` — lista di Feature GeoJSON
  - `main(argv: list[str] | None = None) -> int`
  - entry point `osp-extract = "openstreetphoto.extract:main"`

- [ ] **Step 1: Test falliti (integrazione su mini .osm XML)**

Aggiungi a `tests/test_extract.py`:

```python
import json
from pathlib import Path

from openstreetphoto.extract import extract_features, main

MINI_OSM = """<?xml version='1.0' encoding='UTF-8'?>
<osm version="0.6" generator="test">
  <node id="1" version="1" lat="45.464" lon="9.190">
    <tag k="amenity" v="cafe"/>
    <tag k="image" v="https://example.org/duomo.jpg"/>
  </node>
  <node id="2" version="1" lat="45.465" lon="9.191">
    <tag k="amenity" v="bar"/>
  </node>
  <node id="3" version="1" lat="45.466" lon="9.192">
    <tag k="wikimedia_commons" v="Category:Milano"/>
  </node>
</osm>
"""


def _write_mini_osm(tmp_path: Path) -> Path:
    src = tmp_path / "mini.osm"
    src.write_text(MINI_OSM)
    return src


def test_extract_features_filters_photo_nodes(tmp_path):
    src = _write_mini_osm(tmp_path)
    features = extract_features(src)
    assert len(features) == 1
    feat = features[0]
    assert feat["geometry"] == {"type": "Point", "coordinates": [9.190, 45.464]}
    assert feat["properties"]["osm_id"] == 1
    assert feat["properties"]["photo_keys"] == ["image"]
    assert feat["properties"]["tags"]["amenity"] == "cafe"


def test_main_writes_geojson(tmp_path, capsys):
    src = _write_mini_osm(tmp_path)
    out = tmp_path / "photo.geojson"
    rc = main(["--pbf", str(src), "--out", str(out)])
    assert rc == 0
    doc = json.loads(out.read_text())
    assert doc["type"] == "FeatureCollection"
    assert len(doc["features"]) == 1
    assert "1" in capsys.readouterr().out


def test_main_missing_pbf_returns_1(tmp_path, capsys):
    rc = main(["--pbf", str(tmp_path / "missing.pbf"), "--out", str(tmp_path / "o.geojson")])
    assert rc == 1
    assert "errore" in capsys.readouterr().err.lower()
```

- [ ] **Step 2: Run, expect ImportError** — `.venv/bin/pytest tests/test_extract.py -q`

- [ ] **Step 3: Implementa**

Aggiungi in `extract.py`:

```python
import argparse
import json
import sys
from pathlib import Path

import osmium


class _PhotoNodeHandler(osmium.SimpleHandler):
    def __init__(self) -> None:
        super().__init__()
        self.features: list[dict] = []

    def node(self, n: "osmium.osm.Node") -> None:
        tags = {tag.k: tag.v for tag in n.tags}
        keys = photo_keys(tags)
        if not keys:
            return
        self.features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [n.location.lon, n.location.lat],
                },
                "properties": {"osm_id": n.id, "photo_keys": keys, "tags": tags},
            }
        )


def extract_features(pbf: Path) -> list[dict]:
    handler = _PhotoNodeHandler()
    handler.apply_file(str(pbf))
    return handler.features


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Estrae in GeoJSON i nodi OSM con tag foto"
    )
    parser.add_argument(
        "--pbf", type=Path, default=Path("data/lombardia-latest.osm.pbf")
    )
    parser.add_argument("--out", type=Path, default=Path("data/photo-nodes.geojson"))
    args = parser.parse_args(argv)
    try:
        features = extract_features(args.pbf)
    except (OSError, RuntimeError) as exc:
        print(f"errore di estrazione: {exc}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps({"type": "FeatureCollection", "features": features})
    )
    print(f"{len(features)} nodi con foto -> {args.out}")
    return 0
```

In `pyproject.toml` sotto `[project.scripts]`: `osp-extract = "openstreetphoto.extract:main"`.

Nota: pyosmium solleva `RuntimeError` per file mancanti/corrotti — l'except deve coprire sia `OSError` sia `RuntimeError`. Verificare il tipo effettivo nel test 3; se diverso, adeguare l'except al tipo reale osservato.

- [ ] **Step 4: Reinstalla e run** — `.venv/bin/pip install -q -e ".[test]" && .venv/bin/pytest -q` → tutti PASS (14 download + 7 extract)

- [ ] **Step 5: Commit** — `git commit -m "feat: CLI osp-extract, nodi con foto in GeoJSON"`

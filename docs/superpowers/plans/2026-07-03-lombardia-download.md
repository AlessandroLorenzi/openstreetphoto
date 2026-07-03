# Downloader estratto OSM Lombardia — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CLI Python `osp-download` che scarica `lombardia-latest.osm.pbf` da OSM France con skip-se-aggiornato, download atomico e ripresa via `Range`.

**Architecture:** Un solo modulo `src/openstreetphoto/download.py` con funzioni pure e testabili (`fetch_remote_info`, `is_up_to_date`, `download`) più `main()` argparse. Metadati dell'ultimo download in `<file>.meta.json` accanto al PBF; download su `<file>.part` rinominato atomicamente.

**Tech Stack:** Python ≥ 3.11 (locale: 3.14), `requests`, `tqdm`; test con `pytest` + `responses`. Nessun uv disponibile: venv + pip.

## Global Constraints

- URL default: `http://download.openstreetmap.fr/extracts/europe/italy/lombardia-latest.osm.pbf`
- `requires-python = ">=3.11"`
- Dipendenze runtime SOLO `requests` e `tqdm`; test: `pytest`, `responses`
- Nessun retry automatico; errori di rete → stderr + exit code 1
- Un PBF valido non viene mai sostituito da uno troncato (scrittura su `.part` + `Path.replace`)
- Spec di riferimento: `docs/superpowers/specs/2026-07-03-lombardia-download-design.md`

---

### Task 1: Scaffolding + logica skip-se-aggiornato

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/openstreetphoto/__init__.py`
- Create: `src/openstreetphoto/download.py`
- Test: `tests/test_download.py`

**Interfaces:**
- Consumes: —
- Produces:
  - `RemoteInfo` dataclass: campi `last_modified: str | None`, `content_length: int | None`
  - `fetch_remote_info(url: str, session: requests.Session) -> RemoteInfo` (HEAD, `raise_for_status`)
  - `meta_path_for(dest: Path) -> Path` → `<dest>.meta.json`
  - `is_up_to_date(dest: Path, remote: RemoteInfo) -> bool`
  - Costante `DEFAULT_URL`

- [ ] **Step 1: Crea scaffolding del progetto**

`pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "openstreetphoto"
version = "0.1.0"
description = "Downloader dell'estratto OpenStreetMap della Lombardia"
requires-python = ">=3.11"
dependencies = ["requests", "tqdm"]

[project.optional-dependencies]
test = ["pytest", "responses"]

[project.scripts]
osp-download = "openstreetphoto.download:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`.gitignore`:

```
.venv/
__pycache__/
*.egg-info/
data/
```

`src/openstreetphoto/__init__.py`: file vuoto.

- [ ] **Step 2: Crea venv e installa in editable**

Run: `python3 -m venv .venv && .venv/bin/pip install -e ".[test]"`
Expected: installazione senza errori (crea anche `src/openstreetphoto/download.py` vuoto prima, altrimenti l'entry point è rotto ma l'install passa comunque — va bene).

- [ ] **Step 3: Scrivi i test falliti per skip logic**

`tests/test_download.py`:

```python
import json
from pathlib import Path

import responses

from openstreetphoto.download import (
    RemoteInfo,
    fetch_remote_info,
    is_up_to_date,
    meta_path_for,
)

URL = "http://example.org/lombardia-latest.osm.pbf"


@responses.activate
def test_fetch_remote_info_reads_headers():
    responses.head(
        URL,
        headers={"Last-Modified": "Fri, 03 Jul 2026 01:40:35 GMT", "Content-Length": "347"},
    )
    import requests

    info = fetch_remote_info(URL, requests.Session())
    assert info == RemoteInfo(
        last_modified="Fri, 03 Jul 2026 01:40:35 GMT", content_length=347
    )


def _write_meta(dest: Path, last_modified: str, content_length: int) -> None:
    meta_path_for(dest).write_text(
        json.dumps({"last_modified": last_modified, "content_length": content_length})
    )


def test_up_to_date_when_meta_matches(tmp_path):
    dest = tmp_path / "lombardia-latest.osm.pbf"
    dest.write_bytes(b"pbf")
    _write_meta(dest, "Fri, 03 Jul 2026 01:40:35 GMT", 347)
    remote = RemoteInfo("Fri, 03 Jul 2026 01:40:35 GMT", 347)
    assert is_up_to_date(dest, remote) is True


def test_not_up_to_date_when_last_modified_differs(tmp_path):
    dest = tmp_path / "lombardia-latest.osm.pbf"
    dest.write_bytes(b"pbf")
    _write_meta(dest, "Thu, 02 Jul 2026 01:40:35 GMT", 347)
    remote = RemoteInfo("Fri, 03 Jul 2026 01:40:35 GMT", 347)
    assert is_up_to_date(dest, remote) is False


def test_not_up_to_date_when_file_missing(tmp_path):
    dest = tmp_path / "lombardia-latest.osm.pbf"
    _write_meta(dest, "Fri, 03 Jul 2026 01:40:35 GMT", 347)
    remote = RemoteInfo("Fri, 03 Jul 2026 01:40:35 GMT", 347)
    assert is_up_to_date(dest, remote) is False


def test_not_up_to_date_when_meta_missing(tmp_path):
    dest = tmp_path / "lombardia-latest.osm.pbf"
    dest.write_bytes(b"pbf")
    remote = RemoteInfo("Fri, 03 Jul 2026 01:40:35 GMT", 347)
    assert is_up_to_date(dest, remote) is False
```

- [ ] **Step 4: Verifica che falliscano**

Run: `.venv/bin/pytest tests/test_download.py -v`
Expected: FAIL/ERROR con `ImportError` (nomi non definiti in `download.py`)

- [ ] **Step 5: Implementa il minimo in `src/openstreetphoto/download.py`**

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import requests

DEFAULT_URL = (
    "http://download.openstreetmap.fr/extracts/europe/italy/lombardia-latest.osm.pbf"
)


@dataclass
class RemoteInfo:
    last_modified: str | None
    content_length: int | None


def fetch_remote_info(url: str, session: requests.Session) -> RemoteInfo:
    resp = session.head(url, allow_redirects=True, timeout=30)
    resp.raise_for_status()
    length = resp.headers.get("Content-Length")
    return RemoteInfo(
        last_modified=resp.headers.get("Last-Modified"),
        content_length=int(length) if length is not None else None,
    )


def meta_path_for(dest: Path) -> Path:
    return dest.with_name(dest.name + ".meta.json")


def is_up_to_date(dest: Path, remote: RemoteInfo) -> bool:
    meta_file = meta_path_for(dest)
    if not dest.exists() or not meta_file.exists():
        return False
    meta = json.loads(meta_file.read_text())
    return (
        remote.last_modified is not None
        and meta.get("last_modified") == remote.last_modified
        and meta.get("content_length") == remote.content_length
    )
```

- [ ] **Step 6: Verifica che passino**

Run: `.venv/bin/pytest tests/test_download.py -v`
Expected: 5 PASS

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .gitignore src tests
git commit -m "feat: scaffolding progetto e logica skip-se-aggiornato"
```

---

### Task 2: Download atomico con progress bar

**Files:**
- Modify: `src/openstreetphoto/download.py`
- Test: `tests/test_download.py`

**Interfaces:**
- Consumes: `RemoteInfo`, `fetch_remote_info`, `is_up_to_date`, `meta_path_for` (Task 1)
- Produces: `download(url: str, dest_dir: Path, *, force: bool = False, session: requests.Session | None = None, progress: bool = True) -> Path` — ritorna il path del PBF; salta il download se aggiornato e non `force`; scrive `.meta.json` a fine download.

- [ ] **Step 1: Scrivi i test falliti**

Aggiungi in `tests/test_download.py`:

```python
import requests

from openstreetphoto.download import download

BODY = b"x" * 1000


def _mock_head(last_modified="Fri, 03 Jul 2026 01:40:35 GMT", length=len(BODY)):
    responses.head(
        URL,
        headers={"Last-Modified": last_modified, "Content-Length": str(length)},
    )


@responses.activate
def test_download_writes_file_and_meta(tmp_path):
    _mock_head()
    responses.get(URL, body=BODY)
    dest = download(URL, tmp_path, progress=False)
    assert dest == tmp_path / "lombardia-latest.osm.pbf"
    assert dest.read_bytes() == BODY
    assert not (tmp_path / "lombardia-latest.osm.pbf.part").exists()
    meta = json.loads(meta_path_for(dest).read_text())
    assert meta["last_modified"] == "Fri, 03 Jul 2026 01:40:35 GMT"
    assert meta["content_length"] == len(BODY)


@responses.activate
def test_download_skips_when_up_to_date(tmp_path):
    _mock_head()
    dest = tmp_path / "lombardia-latest.osm.pbf"
    dest.write_bytes(b"old-but-current")
    _write_meta(dest, "Fri, 03 Jul 2026 01:40:35 GMT", len(BODY))
    result = download(URL, tmp_path, progress=False)
    assert result == dest
    assert dest.read_bytes() == b"old-but-current"  # nessuna GET registrata: se la facesse, responses alzerebbe ConnectionError


@responses.activate
def test_download_force_ignores_meta(tmp_path):
    _mock_head()
    responses.get(URL, body=BODY)
    dest = tmp_path / "lombardia-latest.osm.pbf"
    dest.write_bytes(b"old")
    _write_meta(dest, "Fri, 03 Jul 2026 01:40:35 GMT", len(BODY))
    result = download(URL, tmp_path, force=True, progress=False)
    assert result.read_bytes() == BODY


@responses.activate
def test_download_http_error_keeps_existing_file(tmp_path):
    _mock_head()
    responses.get(URL, status=503)
    dest = tmp_path / "lombardia-latest.osm.pbf"
    dest.write_bytes(b"good")
    import pytest

    with pytest.raises(requests.HTTPError):
        download(URL, tmp_path, force=True, progress=False)
    assert dest.read_bytes() == b"good"
```

- [ ] **Step 2: Verifica che falliscano**

Run: `.venv/bin/pytest tests/test_download.py -v`
Expected: i 4 nuovi test FAIL con `ImportError: cannot import name 'download'`; i 5 di Task 1 PASS

- [ ] **Step 3: Implementa `download`**

Aggiungi in `src/openstreetphoto/download.py` (import in testa: `from tqdm import tqdm`):

```python
CHUNK_SIZE = 64 * 1024


def download(
    url: str,
    dest_dir: Path,
    *,
    force: bool = False,
    session: requests.Session | None = None,
    progress: bool = True,
) -> Path:
    session = session or requests.Session()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / url.rsplit("/", 1)[-1]

    remote = fetch_remote_info(url, session)
    if not force and is_up_to_date(dest, remote):
        print(f"{dest.name}: già aggiornato, download saltato")
        return dest

    part = dest.with_name(dest.name + ".part")
    resp = session.get(url, stream=True, timeout=30)
    resp.raise_for_status()
    with open(part, "wb") as fh, tqdm(
        total=remote.content_length,
        unit="B",
        unit_scale=True,
        desc=dest.name,
        disable=not progress,
    ) as bar:
        for chunk in resp.iter_content(CHUNK_SIZE):
            fh.write(chunk)
            bar.update(len(chunk))

    part.replace(dest)
    meta_path_for(dest).write_text(
        json.dumps(
            {
                "url": url,
                "last_modified": remote.last_modified,
                "content_length": remote.content_length,
            }
        )
    )
    return dest
```

- [ ] **Step 4: Verifica che passino**

Run: `.venv/bin/pytest tests/test_download.py -v`
Expected: 9 PASS

- [ ] **Step 5: Commit**

```bash
git add src tests
git commit -m "feat: download atomico con progress bar e scrittura meta"
```

---

### Task 3: Ripresa del download con Range

**Files:**
- Modify: `src/openstreetphoto/download.py` (funzione `download`)
- Test: `tests/test_download.py`

**Interfaces:**
- Consumes: `download` (Task 2)
- Produces: stessa firma di `download`; nuovo comportamento: se esiste `<dest>.part` invia `Range: bytes=<size>-`; su 206 appende, su 200 riparte da zero.

- [ ] **Step 1: Scrivi i test falliti**

Aggiungi in `tests/test_download.py`:

```python
@responses.activate
def test_download_resumes_partial_with_206(tmp_path):
    _mock_head()
    part = tmp_path / "lombardia-latest.osm.pbf.part"
    part.write_bytes(BODY[:400])
    responses.get(
        URL,
        body=BODY[400:],
        status=206,
        match=[responses.matchers.header_matcher({"Range": "bytes=400-"})],
    )
    dest = download(URL, tmp_path, progress=False)
    assert dest.read_bytes() == BODY
    assert not part.exists()


@responses.activate
def test_download_restarts_when_server_ignores_range(tmp_path):
    _mock_head()
    part = tmp_path / "lombardia-latest.osm.pbf.part"
    part.write_bytes(b"stale")
    responses.get(URL, body=BODY, status=200)
    dest = download(URL, tmp_path, progress=False)
    assert dest.read_bytes() == BODY
```

- [ ] **Step 2: Verifica che falliscano**

Run: `.venv/bin/pytest tests/test_download.py -v -k resume or ignores_range`
Nota: usa `.venv/bin/pytest tests/test_download.py -v` e guarda i 2 nuovi test.
Expected: `test_download_resumes_partial_with_206` FAIL (ConnectionError: la GET mockata richiede l'header Range che il codice non manda); `test_download_restarts_when_server_ignores_range` FAIL su contenuto (`b"stale" + BODY`? no: il codice attuale scrive in "wb", quindi potrebbe già passare — se passa, va bene, è il comportamento voluto e lo si tiene come regression test)

- [ ] **Step 3: Implementa la ripresa**

In `download`, sostituisci il blocco dalla riga `part = ...` fino a `resp.raise_for_status()` con:

```python
    part = dest.with_name(dest.name + ".part")
    offset = part.stat().st_size if part.exists() else 0
    headers = {"Range": f"bytes={offset}-"} if offset else {}
    resp = session.get(url, headers=headers, stream=True, timeout=30)
    resp.raise_for_status()
    if offset and resp.status_code != 206:
        offset = 0  # il server ha ignorato Range: si riparte da zero
    mode = "ab" if offset else "wb"
```

e cambia `open(part, "wb")` in `open(part, mode)` e `tqdm(total=..., ...)` aggiungendo `initial=offset`.

Blocco finale risultante:

```python
    with open(part, mode) as fh, tqdm(
        total=remote.content_length,
        initial=offset,
        unit="B",
        unit_scale=True,
        desc=dest.name,
        disable=not progress,
    ) as bar:
        for chunk in resp.iter_content(CHUNK_SIZE):
            fh.write(chunk)
            bar.update(len(chunk))
```

- [ ] **Step 4: Verifica che passino tutti**

Run: `.venv/bin/pytest tests/test_download.py -v`
Expected: 11 PASS

- [ ] **Step 5: Commit**

```bash
git add src tests
git commit -m "feat: ripresa download parziale via header Range"
```

---

### Task 4: CLI `osp-download`

**Files:**
- Modify: `src/openstreetphoto/download.py`
- Test: `tests/test_download.py`

**Interfaces:**
- Consumes: `download`, `DEFAULT_URL`
- Produces: `main(argv: list[str] | None = None) -> int`; entry point `osp-download` già dichiarato in `pyproject.toml` (Task 1).

- [ ] **Step 1: Scrivi i test falliti**

Aggiungi in `tests/test_download.py`:

```python
from openstreetphoto.download import main


@responses.activate
def test_main_downloads_to_dest(tmp_path, capsys):
    _mock_head()
    responses.get(URL, body=BODY)
    rc = main(["--url", URL, "--dest", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / "lombardia-latest.osm.pbf").read_bytes() == BODY


@responses.activate
def test_main_network_error_returns_1(tmp_path, capsys):
    responses.head(URL, body=requests.ConnectionError("rete giù"))
    rc = main(["--url", URL, "--dest", str(tmp_path)])
    assert rc == 1
    assert "errore" in capsys.readouterr().err.lower()
```

- [ ] **Step 2: Verifica che falliscano**

Run: `.venv/bin/pytest tests/test_download.py -v`
Expected: 2 nuovi FAIL con `ImportError: cannot import name 'main'`

- [ ] **Step 3: Implementa `main`**

Aggiungi in `src/openstreetphoto/download.py` (import in testa: `import argparse`, `import sys`):

```python
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scarica un estratto OpenStreetMap (default: Lombardia)"
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="URL dell'estratto .osm.pbf")
    parser.add_argument(
        "--dest", type=Path, default=Path("data"), help="directory di destinazione"
    )
    parser.add_argument(
        "--force", action="store_true", help="scarica anche se già aggiornato"
    )
    args = parser.parse_args(argv)
    try:
        dest = download(args.url, args.dest, force=args.force)
    except requests.RequestException as exc:
        print(f"errore di download: {exc}", file=sys.stderr)
        return 1
    print(dest)
    return 0
```

- [ ] **Step 4: Verifica che passino tutti + smoke test CLI**

Run: `.venv/bin/pytest tests/test_download.py -v`
Expected: 13 PASS

Run: `.venv/bin/osp-download --help`
Expected: usage con `--url`, `--dest`, `--force`

- [ ] **Step 5: Commit**

```bash
git add src tests
git commit -m "feat: CLI osp-download con exit code e messaggi di errore"
```

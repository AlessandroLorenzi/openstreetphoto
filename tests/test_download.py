import json
from pathlib import Path

import pytest
import requests
import responses

from openstreetphoto.download import (
    RemoteInfo,
    download,
    fetch_remote_info,
    main,
    is_up_to_date,
    meta_path_for,
)

URL = "http://example.org/italy.osm.pbf"
BODY = b"x" * 1000


def _mock_head(last_modified="Fri, 03 Jul 2026 01:40:35 GMT", length=len(BODY)):
    responses.head(
        URL,
        headers={"Last-Modified": last_modified, "Content-Length": str(length)},
    )


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
    dest = tmp_path / "italy.osm.pbf"
    dest.write_bytes(b"pbf")
    _write_meta(dest, "Fri, 03 Jul 2026 01:40:35 GMT", 347)
    remote = RemoteInfo("Fri, 03 Jul 2026 01:40:35 GMT", 347)
    assert is_up_to_date(dest, remote) is True


def test_not_up_to_date_when_last_modified_differs(tmp_path):
    dest = tmp_path / "italy.osm.pbf"
    dest.write_bytes(b"pbf")
    _write_meta(dest, "Thu, 02 Jul 2026 01:40:35 GMT", 347)
    remote = RemoteInfo("Fri, 03 Jul 2026 01:40:35 GMT", 347)
    assert is_up_to_date(dest, remote) is False


def test_not_up_to_date_when_file_missing(tmp_path):
    dest = tmp_path / "italy.osm.pbf"
    _write_meta(dest, "Fri, 03 Jul 2026 01:40:35 GMT", 347)
    remote = RemoteInfo("Fri, 03 Jul 2026 01:40:35 GMT", 347)
    assert is_up_to_date(dest, remote) is False


def test_not_up_to_date_when_meta_missing(tmp_path):
    dest = tmp_path / "italy.osm.pbf"
    dest.write_bytes(b"pbf")
    remote = RemoteInfo("Fri, 03 Jul 2026 01:40:35 GMT", 347)
    assert is_up_to_date(dest, remote) is False


@responses.activate
def test_download_writes_file_and_meta(tmp_path):
    _mock_head()
    responses.get(URL, body=BODY)
    dest = download(URL, tmp_path, progress=False)
    assert dest == tmp_path / "italy.osm.pbf"
    assert dest.read_bytes() == BODY
    assert not (tmp_path / "italy.osm.pbf.part").exists()
    meta = json.loads(meta_path_for(dest).read_text())
    assert meta["last_modified"] == "Fri, 03 Jul 2026 01:40:35 GMT"
    assert meta["content_length"] == len(BODY)


@responses.activate
def test_download_skips_when_up_to_date(tmp_path):
    _mock_head()
    dest = tmp_path / "italy.osm.pbf"
    dest.write_bytes(b"old-but-current")
    _write_meta(dest, "Fri, 03 Jul 2026 01:40:35 GMT", len(BODY))
    result = download(URL, tmp_path, progress=False)
    assert result == dest
    # nessuna GET registrata: se la facesse, responses alzerebbe ConnectionError
    assert dest.read_bytes() == b"old-but-current"


@responses.activate
def test_download_force_ignores_meta(tmp_path):
    _mock_head()
    responses.get(URL, body=BODY)
    dest = tmp_path / "italy.osm.pbf"
    dest.write_bytes(b"old")
    _write_meta(dest, "Fri, 03 Jul 2026 01:40:35 GMT", len(BODY))
    result = download(URL, tmp_path, force=True, progress=False)
    assert result.read_bytes() == BODY


@responses.activate
def test_download_http_error_keeps_existing_file(tmp_path):
    _mock_head()
    responses.get(URL, status=503)
    dest = tmp_path / "italy.osm.pbf"
    dest.write_bytes(b"good")
    with pytest.raises(requests.HTTPError):
        download(URL, tmp_path, force=True, progress=False)
    assert dest.read_bytes() == b"good"


@responses.activate
def test_download_resumes_partial_with_206(tmp_path):
    _mock_head()
    part = tmp_path / "italy.osm.pbf.part"
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
    part = tmp_path / "italy.osm.pbf.part"
    part.write_bytes(b"stale")
    responses.get(URL, body=BODY, status=200)
    dest = download(URL, tmp_path, progress=False)
    assert dest.read_bytes() == BODY


@responses.activate
def test_main_downloads_to_dest(tmp_path, capsys):
    _mock_head()
    responses.get(URL, body=BODY)
    rc = main(["--url", URL, "--dest", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / "italy.osm.pbf").read_bytes() == BODY


@responses.activate
def test_main_network_error_returns_1(tmp_path, capsys):
    responses.head(URL, body=requests.ConnectionError("rete giù"))
    rc = main(["--url", URL, "--dest", str(tmp_path)])
    assert rc == 1
    assert "errore" in capsys.readouterr().err.lower()


def test_main_keyboard_interrupt_no_traceback(tmp_path, capsys, monkeypatch):
    import openstreetphoto.download as dl

    def _interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(dl, "download", _interrupt)
    rc = main(["--url", URL, "--dest", str(tmp_path)])
    assert rc == 130
    assert "interrotto" in capsys.readouterr().err.lower()

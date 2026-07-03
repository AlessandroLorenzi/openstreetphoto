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

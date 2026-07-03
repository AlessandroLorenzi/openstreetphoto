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

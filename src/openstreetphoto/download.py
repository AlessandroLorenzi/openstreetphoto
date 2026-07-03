from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import requests
from tqdm import tqdm

DEFAULT_URL = (
    "http://download.openstreetmap.fr/extracts/europe/italy/lombardia-latest.osm.pbf"
)
CHUNK_SIZE = 64 * 1024


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

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import requests
from tqdm import tqdm

DEFAULT_URL = "http://download.openstreetmap.fr/extracts/europe/italy.osm.pbf"
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
    offset = part.stat().st_size if part.exists() else 0
    headers = {"Range": f"bytes={offset}-"} if offset else {}
    resp = session.get(url, headers=headers, stream=True, timeout=30)
    resp.raise_for_status()
    if offset and resp.status_code != 206:
        offset = 0  # il server ha ignorato Range: si riparte da zero
    mode = "ab" if offset else "wb"
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scarica un estratto OpenStreetMap (default: Italia)"
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
    except KeyboardInterrupt:
        print("interrotto: il download riprenderà dal punto raggiunto", file=sys.stderr)
        return 130
    print(dest)
    return 0

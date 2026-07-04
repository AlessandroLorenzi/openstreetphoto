"""Pipeline completa: download dell'estratto e generazione del GeoJSON."""

from __future__ import annotations

from openstreetphoto.download import main as download_main
from openstreetphoto.extract import main as extract_main


def main(argv: list[str] | None = None) -> int:
    rc = download_main([])
    if rc != 0:
        return rc
    return extract_main([])

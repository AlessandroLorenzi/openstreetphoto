from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import osmium

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


class _PhotoNodeHandler(osmium.SimpleHandler):
    def __init__(self) -> None:
        super().__init__()
        self.features: list[dict] = []

    def node(self, n: osmium.osm.Node) -> None:
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

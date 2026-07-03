import json
from pathlib import Path

from openstreetphoto.extract import extract_features, main, photo_keys


def test_photo_keys_matches_each_photo_tag():
    for key in ("image", "panoramax", "mapillary", "flickr"):
        assert photo_keys({key: "qualcosa"}) == [key]


def test_photo_keys_wikimedia_commons_file_only():
    assert photo_keys({"wikimedia_commons": "File:Duomo.jpg"}) == ["wikimedia_commons"]
    assert photo_keys({"wikimedia_commons": "Category:Milano"}) == []


def test_photo_keys_empty_without_photo_tags():
    assert photo_keys({"amenity": "cafe", "name": "Bar Sport"}) == []


def test_photo_keys_multiple():
    tags = {"image": "http://x/1.jpg", "wikimedia_commons": "File:x.jpg", "name": "x"}
    assert photo_keys(tags) == ["image", "wikimedia_commons"]


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

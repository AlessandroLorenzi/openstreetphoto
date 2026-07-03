from openstreetphoto.extract import photo_keys


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

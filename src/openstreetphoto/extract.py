from __future__ import annotations

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

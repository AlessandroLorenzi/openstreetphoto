import json

import pytest

from test_web_image_url import run_js  # tests/ non e' un package: pytest mette la dir in sys.path


def type_title(tags: dict) -> str | None:
    out = run_js(f"JSON.stringify(typeTitle({json.dumps(tags)}))", "typeTitle")
    return json.loads(out)


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        # il caso della richiesta: underscore -> spazi, prima lettera maiuscola
        ({"amenity": "drinking_water"}, "Drinking water"),
        # priorita': amenity vince su tourism
        ({"amenity": "fountain", "tourism": "artwork"}, "Fountain"),
        # tag successivi nella catena
        ({"tourism": "artwork"}, "Artwork"),
        ({"historic": "wayside_cross"}, "Wayside cross"),
        ({"man_made": "water_tap"}, "Water tap"),
        ({"leisure": "playground"}, "Playground"),
        # "yes" scartato con fallback al tag successivo
        ({"shop": "yes", "tourism": "artwork"}, "Artwork"),
        # solo "yes": nessun titolo
        ({"man_made": "yes"}, None),
        # nessun tag tipo
        ({"name": "Bar Sport"}, None),
        ({}, None),
    ],
)
def test_type_title(tags, expected):
    assert type_title(tags) == expected

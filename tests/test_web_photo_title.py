import json

import pytest

from test_web_image_url import run_js  # tests/ non e' un package: pytest mette la dir in sys.path


def photo_title(tags: dict) -> str | None:
    out = run_js(
        f"JSON.stringify(photoTitle({json.dumps(tags)}))",
        "parseWikiImage",
        "humanTitle",
        "photoTitle",
    )
    return json.loads(out)


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        # wikimedia_commons: underscore -> spazi, via l'estensione
        ({"wikimedia_commons": "File:Chiesa_di_San_Rocco.jpg"}, "Chiesa di San Rocco"),
        # image= pagina File: su Commons, filename URL-encoded
        (
            {"image": "https://commons.wikimedia.org/wiki/File:Cascina_%22La_Torretta%22.JPG"},
            'Cascina "La Torretta"',
        ),
        # image= valore nudo File:
        ({"image": "File:Lavatoio di Brunate.png"}, "Lavatoio di Brunate"),
        # wikimedia_commons ha priorita' su image
        (
            {"wikimedia_commons": "File:Duomo_di_Como.jpg", "image": "File:Altro.jpg"},
            "Duomo di Como",
        ),
        # nome macchina -> None
        ({"wikimedia_commons": "File:IMG_20230512_101530.jpg"}, None),
        ({"wikimedia_commons": "File:DSC00123.jpg"}, None),
        ({"wikimedia_commons": "File:P1010001.jpg"}, None),
        ({"image": "File:20230512 101530.jpg"}, None),
        # ma wikimedia_commons macchina + image umano -> usa image
        (
            {"wikimedia_commons": "File:IMG_1234.jpg", "image": "File:Fontana vecchia.jpg"},
            "Fontana vecchia",
        ),
        # URL image= non Wikimedia: nessuna derivazione
        ({"image": "https://example.com/foto.jpg"}, None),
        # panoramax da solo: nessuna derivazione
        ({"panoramax": "a1b2c3d4-0000-0000-0000-000000000000"}, None),
        # wikimedia_commons Category: ignorato
        ({"wikimedia_commons": "Category:Brunate"}, None),
        # percent literale nel valore raw: decodeURIComponent fallirebbe, non deve rompere
        ({"wikimedia_commons": "File:100%_cotone.jpg"}, "100%_cotone"),
    ],
)
def test_photo_title(tags, expected):
    assert photo_title(tags) == expected

import json
import subprocess
from pathlib import Path

import pytest

HTML = Path(__file__).parent.parent / "src" / "openstreetphoto" / "web" / "index.html"


def extract_function(source: str, name: str) -> str:
    start = source.index(f"function {name}")
    depth = 0
    for i in range(source.index("{", start), len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start : i + 1]
    raise ValueError(f"funzione {name} non trovata")


def run_js(expr: str, *functions: str) -> str:
    source = HTML.read_text()
    script = "\n".join(extract_function(source, f) for f in functions)
    script += f"\nconsole.log({expr});"
    out = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


def normalize(url: str) -> str:
    return run_js(
        f"normalizeImageUrl({json.dumps(url)})",
        "parseWikiImage",
        "normalizeImageUrl",
    )


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        # pagina File: su Commons (caso node/714813531)
        (
            "https://commons.wikimedia.org/wiki/File:Sutermeister_(2).JPG",
            "https://commons.wikimedia.org/wiki/Special:FilePath/Sutermeister_(2).JPG?width=1024",
        ),
        # pagina File: su una Wikipedia locale: Special:FilePath dello stesso host
        (
            "https://it.wikipedia.org/wiki/File:Duomo_di_Milano.jpg",
            "https://it.wikipedia.org/wiki/Special:FilePath/Duomo_di_Milano.jpg?width=1024",
        ),
        # valore nudo File:... (stile ammesso dalla wiki OSM per image=)
        (
            "File:Foo bar.jpg",
            "https://commons.wikimedia.org/wiki/Special:FilePath/Foo%20bar.jpg?width=1024",
        ),
        # vecchio thumb morto: comportamento esistente
        (
            "https://upload.wikimedia.org/wikipedia/commons/thumb/9/95/Sutermeister_(2).JPG/800px-Sutermeister_(2).JPG",
            "https://commons.wikimedia.org/wiki/Special:FilePath/Sutermeister_(2).JPG?width=1024",
        ),
        # URL diretto upload: invariato
        (
            "https://upload.wikimedia.org/wikipedia/commons/9/95/Sutermeister_%282%29.JPG",
            "https://upload.wikimedia.org/wikipedia/commons/9/95/Sutermeister_%282%29.JPG",
        ),
        # URL non Wikimedia: invariato
        (
            "https://example.com/foto.jpg",
            "https://example.com/foto.jpg",
        ),
    ],
)
def test_normalize_image_url(url, expected):
    assert normalize(url) == expected

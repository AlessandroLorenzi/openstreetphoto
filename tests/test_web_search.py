import json
import subprocess
from pathlib import Path

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


def test_build_search_url_encodes_query_and_viewbox():
    url = run_js(
        'buildSearchUrl("via Verdi, Milano", 9.1, 45.4, 9.3, 45.5)',
        "buildSearchUrl",
    )
    assert url.startswith("https://nominatim.openstreetmap.org/search?")
    assert "format=json" in url
    assert "limit=5" in url
    assert "bounded=1" in url
    assert "q=via%20Verdi%2C%20Milano" in url
    assert "viewbox=9.1%2C45.4%2C9.3%2C45.5" in url


def test_result_to_bounds_maps_nominatim_boundingbox():
    # Nominatim: boundingbox = [south, north, west, east] come stringhe
    out = run_js(
        'JSON.stringify(resultToBounds('
        '{"boundingbox": ["45.40", "45.50", "9.10", "9.30"]}))',
        "resultToBounds",
    )
    assert json.loads(out) == [[45.40, 9.10], [45.50, 9.30]]

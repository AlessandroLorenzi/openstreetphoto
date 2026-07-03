from __future__ import annotations

import argparse
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path


def _web_file(name: str) -> bytes:
    return (resources.files("openstreetphoto") / "web" / name).read_bytes()


def make_server(geojson: Path, port: int) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]  # /?data=italia deve matchare /
            italia = geojson.with_name("photo-nodes-italia.geojson")
            if path in ("/", "/index.html"):
                self._send(200, "text/html; charset=utf-8", _web_file("index.html"))
            elif path == "/italy.html":
                self._send(200, "text/html; charset=utf-8", _web_file("italy.html"))
            elif path == "/photo-nodes.geojson":
                self._send(200, "application/geo+json", geojson.read_bytes())
            elif path == "/photo-nodes-italia.geojson" and italia.exists():
                self._send(200, "application/geo+json", italia.read_bytes())
            else:
                self._send(404, "text/plain; charset=utf-8", b"not found")

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:  # silenzia stderr
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mappa web dei nodi OSM con foto")
    parser.add_argument(
        "--geojson", type=Path, default=Path("data/photo-nodes.geojson")
    )
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    if not args.geojson.exists():
        print(
            f"errore: {args.geojson} non esiste (lancia prima osp-extract)",
            file=sys.stderr,
        )
        return 1
    server = make_server(args.geojson, args.port)
    print(f"in ascolto su http://localhost:{server.server_address[1]}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0

# Design: server web mappa foto (`osp-serve`)

Data: 2026-07-03
Stato: approvato

## Obiettivo

CLI `osp-serve` che serve una pagina web con mappa OSM a schermo intero e i
nodi con foto estratti da `osp-extract`; al click su un punto si apre una
modale con la foto.

## Scelte confermate

- Server: stdlib `http.server` (ThreadingHTTPServer), nessuna dipendenza nuova.
- Frontend: Leaflet 1.9 + Leaflet.markercluster da CDN, un solo file HTML.
- I punti solo-Mapillary sono esclusi (foto non embeddabile senza token API):
  il filtro avviene client-side, `osp-extract` non cambia.

## CLI

`osp-serve [--geojson data/photo-nodes.geojson] [--port 8000]`

Route:
- `GET /` → `index.html` impacchettata nel package (`openstreetphoto/web/`,
  letta con `importlib.resources`)
- `GET /photo-nodes.geojson` → il file passato da CLI
- altro → 404

All'avvio stampa l'URL (`http://localhost:<porta>/`). GeoJSON mancante →
stderr + exit 1 prima di aprire la porta.

## Frontend (`src/openstreetphoto/web/index.html`)

- Mappa full-screen, tile `https://tile.openstreetmap.org/{z}/{x}/{y}.png`
  con attribution OSM, vista iniziale sulla Lombardia (45.6, 9.8, zoom 8).
- Fetch di `/photo-nodes.geojson`; tiene solo i feature con almeno una chiave
  tra `image`, `wikimedia_commons`, `panoramax` in `properties.photo_keys`.
- Marker in cluster (Leaflet.markercluster).
- Click su marker → modale:
  - foto dalla prima chiave disponibile, in ordine di priorità:
    1. `image` → URL usata così com'è
    2. `wikimedia_commons` (`File:X`) →
       `https://commons.wikimedia.org/wiki/Special:FilePath/<encodeURIComponent(X)>?width=1024`
    3. `panoramax` (`<uuid>`) →
       `https://api.panoramax.xyz/api/pictures/<uuid>/sd.jpg`
  - titolo: `tags.name` se presente, altrimenti "Nodo <osm_id>"
  - link "Vedi su OSM" → `https://www.openstreetmap.org/node/<osm_id>`
  - immagine che non carica (`onerror`) → messaggio di errore al posto della foto
  - chiusura: bottone ✕, click sull'overlay, tasto Esc
- Contatore punti caricati visibile in un angolo.

## Test

- pytest: server avviato su porta effimera in un thread —
  `GET /` → 200 + `text/html` contenente "leaflet";
  `GET /photo-nodes.geojson` → 200 + JSON con `type: FeatureCollection`;
  `GET /altro` → 404; `--geojson` mancante → exit 1.
- Frontend verificato end-to-end nel browser headless (fase verify), non
  con unit test JS.

## Fuori scope

Token Mapillary, HTTPS, ricerca/filtri UI, tile server proprio, cache
delle foto, deploy.

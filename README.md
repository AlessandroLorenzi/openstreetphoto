# openstreetphoto

Mappa dei nodi OpenStreetMap d'Italia che hanno una foto.

**🌍 Pagina pubblica: https://alessandrolorenzi.github.io/openstreetphoto/**

Solo Lombardia: [`#data=lombardia`](https://alessandrolorenzi.github.io/openstreetphoto/#data=lombardia).

Cliccando su un punto si apre la foto con il link al nodo OSM; la URI
contiene un permalink (`#node=…&map=zoom/lat/lon`) condivisibile.

## Come funziona

Pipeline in tre comandi:

```sh
osp-download   # scarica lombardia-latest.osm.pbf (~350 MB) da OSM France
osp-extract    # estrae i nodi con tag foto in data/photo-nodes.geojson
osp-serve      # serve la mappa in locale su http://localhost:8000/
```

- **`osp-download`** — scarica l'estratto regionale con skip se già
  aggiornato (confronto `Last-Modified`), download atomico e ripresa via
  `Range`. Sorgente: [OSM France](http://download.openstreetmap.fr/extracts/)
  (Geofabrik non pubblica un estratto Lombardia). Altre regioni: `--url`.
- **`osp-extract`** — attraversa il PBF con
  [pyosmium](https://osmcode.org/pyosmium/) (filtro `KeyFilter` in C++,
  ~5 s) e produce una FeatureCollection GeoJSON dei nodi con almeno uno tra
  `image`, `panoramax`, `flickr`, `wikimedia_commons=File:*`.
  Mapillary è escluso: foto non embeddabile senza token API.
- **`osp-serve`** — server stdlib che serve la pagina Leaflet e il GeoJSON.

## Deploy

GitHub Pages, via workflow Actions (`.github/workflows/pages.yml`): il
GeoJSON è in Git LFS e il deploy branch-based non servirebbe i contenuti
LFS, quindi il sito viene assemblato nel workflow. Ogni push su `main`
rideploya. Per aggiornare i dati: rilanciare la pipeline e committare il
GeoJSON.

## Sviluppo

```sh
python3 -m venv .venv
.venv/bin/pip install -e ".[test]"
.venv/bin/pytest
```

Specifiche e piani di implementazione in `docs/superpowers/`.

## Dati e licenze

I dati sono © [OpenStreetMap](https://www.openstreetmap.org/copyright)
contributors (ODbL). Le foto restano sulle sorgenti originali (Wikimedia
Commons, Panoramax, URL nei tag `image`) con le rispettive licenze.

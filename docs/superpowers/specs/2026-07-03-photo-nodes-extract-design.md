# Design: estrazione nodi con foto in GeoJSON

Data: 2026-07-03
Stato: approvato

## Obiettivo

CLI `osp-extract` che legge il PBF (default: `data/lombardia-latest.osm.pbf`,
scaricato da `osp-download`) e scrive una `FeatureCollection` GeoJSON con un
`Feature` Point per ogni nodo che ha almeno un tag foto.

## Filtro "nodo con foto"

Un nodo matcha se ha almeno uno di questi tag:

- `image`, `panoramax`, `mapillary`, `flickr` — qualunque valore
- `wikimedia_commons` — solo se il valore inizia per `File:`
  (le `Category:` non sono una foto specifica e sono escluse)

## Output

`osp-extract [--pbf data/lombardia-latest.osm.pbf] [--out data/photo-nodes.geojson]`

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {"type": "Point", "coordinates": [lon, lat]},
      "properties": {
        "osm_id": 123,
        "photo_keys": ["image", "wikimedia_commons"],
        "tags": {"...": "tutti i tag del nodo"}
      }
    }
  ]
}
```

I feature sono accumulati in memoria (decine di migliaia attesi per la
Lombardia: dimensione gestibile) e scritti con un unico `json.dump`.
A fine run la CLI stampa il conteggio dei nodi estratti e il path di output.

## Architettura

- Nuovo modulo `src/openstreetphoto/extract.py`:
  - `photo_keys(tags: dict) -> list[str]` — funzione pura del filtro
  - handler pyosmium sottile che converte i nodi che matchano in Feature
  - `main(argv) -> int` — argparse, entry point `osp-extract`
- `download.py` non si tocca.
- Nuova dipendenza runtime: `osmium` (pyosmium).

## Errori

- PBF mancante o illeggibile → messaggio su stderr, exit 1.

## Test

- Unit su `photo_keys`: matcha ogni tag del set, esclude
  `wikimedia_commons=Category:*`, esclude nodi senza tag foto.
- Integrazione: mini file `.osm` XML scritto dal test (2-3 nodi, uno con
  foto), `main` invocato sulla CLI-surface, GeoJSON verificato.

## Fuori scope

Way/relation con foto, download delle immagini, deduplica, formati diversi
dal GeoJSON, streaming dell'output.

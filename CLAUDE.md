# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Cos'è

Mappa Leaflet dei nodi OpenStreetMap d'Italia che hanno una foto, pubblicata
su GitHub Pages. Pipeline Python (download PBF → estrazione GeoJSON) +
frontend statico in un solo file HTML.

## Comandi

```sh
python3 -m venv .venv && .venv/bin/pip install -e ".[test]"   # setup
.venv/bin/pytest                                              # tutti i test
.venv/bin/pytest tests/test_extract.py::test_photo_keys_multiple -v  # singolo test
.venv/bin/update       # pipeline completa: osp-download + osp-extract
.venv/bin/osp-serve    # mappa locale su http://localhost:8000/ (--port se occupata)
```

`osp-download` scarica `data/italy.osm.pbf` (~2,5 GB, OSM France) con skip
se già aggiornato; `osp-extract` produce `data/photo-nodes.geojson` in ~20 s
(pyosmium con `KeyFilter` in C++ — non iterare i nodi in Python senza filtro).

## Architettura

- `src/openstreetphoto/{download,extract,serve,update}.py` — un modulo per
  comando (entry point in `pyproject.toml [project.scripts]`), ognuno con
  `main(argv) -> int` testabile.
- `src/openstreetphoto/web/index.html` — TUTTO il frontend (CSS+JS inline,
  Leaflet + markercluster da unpkg). Non esistono build step né altri file web.
- `extract.py` tiene solo i nodi con tag foto tra `image`, `panoramax`,
  `flickr`, `wikimedia_commons=File:*`. Mapillary è escluso di proposito
  (foto non embeddabile senza token API). Il frontend mostra solo i
  `photo_keys` in `EMBEDDABLE` (flickr estratto ma non mostrato).

### Test del JavaScript da pytest (harness non ovvio)

`tests/test_web_image_url.py` definisce `extract_function` (estrae una
`function nome(...) {...}` dall'HTML contando le graffe) e
`run_js(expr, *functions)` che concatena le funzioni estratte e le esegue
con `node`. Vincoli che ne derivano:

- ogni funzione JS testata deve essere **autocontenuta**: niente `const` a
  livello di modulo condivise (le liste/costanti vanno dentro il corpo);
- se una funzione ne chiama un'altra, il test deve passare entrambe a
  `run_js` nell'ordine giusto;
- il brace-counting non capisce graffe dentro stringhe/regex: evitare `{`
  nei literal delle funzioni testate.

### Frontend: hash e modale

L'URL usa solo l'hash: `#node=<osm_id>&map=<zoom>/<lat>/<lon>`.
`writeHash()` **ricostruisce l'hash da zero a ogni `moveend`**: qualunque
nuovo parametro nell'hash va aggiunto anche lì o sparisce al primo pan.
Titolo della modale, catena di fallback: `tags.name` → `typeTitle` (tag
tipo leggibile, es. amenity=drinking_water → "Drinking water") →
`photoTitle` (dal filename della foto, con filtro anti-nomi-macchina) →
"Nodo <id>". Tutto il testo va nel DOM via `textContent`, mai innerHTML.

### Verifica E2E

Playwright per Python è nel venv. Pattern usato: script throwaway (non
committato, nella scratchpad) che avvia `osp-serve` su una porta libera,
apre permalink `#node=<id>` presi da `data/photo-nodes.geojson` e asserisce
sul DOM (`#print-title`, `#overlay.open`, `#counter`).

## Deploy

GitHub Pages in modalità **workflow** (`.github/workflows/pages.yml`):
il GeoJSON è in Git LFS e il deploy branch-based non servirebbe i contenuti
LFS, quindi il sito viene assemblato nel workflow (checkout con `lfs: true`).
Ogni push su `main` rideploya. Aggiornare i dati = `update`, poi commit di
`data/photo-nodes.geojson` (`.gitignore` esclude tutto il resto di `data/`;
`.gitattributes` mette ogni `data/*.geojson` in LFS).
L'errore "Deployment failed, try again later" da `deploy-pages` è quasi
sempre il backend di Pages: NON rilanciare con `gh run rerun` (l'artifact
`github-pages` duplicato fa fallire il run), usare `gh workflow run pages.yml`.

## Convenzioni

- Commit convenzionali **in italiano** (`feat:`, `fix:`, `refactor:`, `docs:`).
- Specifiche e piani in `docs/superpowers/{specs,plans}/YYYY-MM-DD-*.md`,
  committati insieme al lavoro.
- Commenti nel codice in italiano, asciutti, solo per vincoli non deducibili
  dal codice.

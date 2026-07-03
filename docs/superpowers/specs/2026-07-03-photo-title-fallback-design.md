# Design: titolo della modale dal nome della foto

Data: 2026-07-03
Stato: approvato

## Problema

Molti nodi con foto non hanno il tag `name`: la modale mostra il fallback
anonimo "Nodo <osm_id>". Spesso però il filename della foto è descrittivo
(es. `wikimedia_commons=File:Chiesa_di_San_Rocco.jpg`).

## Comportamento

Catena del titolo in `openModal`:

1. `tags.name` (come oggi);
2. titolo derivato dal filename della foto, se disponibile e "umano";
3. `"Nodo " + osm_id` (come oggi).

Il titolo derivato usa lo stesso `<h2>` senza differenze visive: è una
didascalia, non un dato OSM.

## Derivazione del filename — `photoTitle(tags)`

Fonti, in ordine:

- `wikimedia_commons=File:…` → valore dopo `File:`;
- `image=` quando è una pagina `File:` di Commons/Wikipedia, un valore
  nudo `File:…`, o un URL `upload.wikimedia.org` — gli stessi pattern di
  `normalizeImageUrl`: il matching va estratto/condiviso per non duplicare
  le regex.

Pulizia: `decodeURIComponent`, underscore → spazi, rimozione estensione
(`.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`, `.tif`, `.tiff`, `.svg`).

Panoramax (UUID) e URL non-Commons: nessuna derivazione.

## Filtro anti-nomi-macchina

Se il risultato somiglia a un nome generato da fotocamera/app, non si usa
(meglio "Nodo 123" che "IMG 20230512 101530"). Si scarta se, case-insensitive:

- matcha `^(IMG|DSC[NF]?|P\d|PXL|DJI|GOPR|Screenshot|WhatsApp Image)[ _-]?\d`;
- oppure è composto solo da cifre, spazi, trattini e punti (date, timestamp).

## Implementazione

Solo `src/openstreetphoto/web/index.html`. Nessuna modifica a
extract/pipeline/GeoJSON.

## Verifica

Manuale con `osp-serve`: nodo senza `name` con filename descrittivo →
titolo derivato; nodo con filename tipo `IMG_1234.jpg` → "Nodo …"; nodo
con `name` → invariato.

## Alternative scartate

- **API Commons a runtime**: fetch extra per click, CORS, dipendenza
  esterna — sproporzionato per una didascalia di fallback.
- **Arricchimento in `osp-extract`**: migliaia di chiamate API in
  pipeline e GeoJSON più grande.

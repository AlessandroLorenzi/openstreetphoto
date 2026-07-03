# Design: permalink della modale nella URI

Data: 2026-07-03
Stato: approvato

## Comportamento

- Apertura modale → `history.replaceState` scrive
  `#node=<osm_id>&map=<zoom>/<lat>/<lon>` (zoom corrente, coordinate del
  nodo, 6 decimali). `replaceState`: il back del browser esce dalla pagina,
  non ripercorre le foto aperte.
- Chiusura modale → l'hash diventa `#map=<zoom>/<lat>/<lon>` (centro e zoom
  correnti della mappa): la posizione resta condivisibile, `node=` sparisce.
- Caricamento pagina con hash:
  - `map=` presente → vista iniziale da hash;
  - `node=` presente → dopo il fetch del GeoJSON, lookup per `osm_id`
    (indice `Map` id→feature); se trovato riapre la modale e, se `map=`
    era assente, centra sul nodo a zoom 18; se non trovato, ignora.

## Implementazione

Solo `src/openstreetphoto/web/index.html`:
- `openModal(feature)` (prima prendeva `properties`) per avere anche le
  coordinate;
- `parseHash()` / scrittura hash con `URLSearchParams`;
- indice `osm_id -> feature` costruito al fetch.

## Verifica

Playwright: click su marker → hash `#node=…&map=…`; navigazione diretta con
hash → stessa modale su quel nodo; chiusura → hash senza `node=`; hash con
id inesistente → nessuna modale, nessun errore JS.

## Aggiornamento continuo (richiesta successiva)

A ogni `moveend` della mappa l'hash viene riscritto con il centro/zoom
correnti; `node=` è conservato se la modale è aperta.

## Fuori scope

pushState/navigazione back tra foto.

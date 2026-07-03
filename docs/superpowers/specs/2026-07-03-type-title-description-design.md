# Design: titolo dal tag tipo e descrizione nella modale

Data: 2026-07-03
Stato: approvato

## Problema

Per i nodi senza `name` il titolo cade subito sul filename della foto, che
spesso non c'è o non è "umano". Molti di questi nodi hanno però un tag
tipo (`amenity=drinking_water`, `tourism=artwork`, …) che è un titolo
accettabile. Inoltre il tag `description`, quando presente, oggi non è
mostrato da nessuna parte.

## Comportamento

### Titolo — catena estesa in `openModal`

1. `tags.name` (come oggi);
2. **nuovo** `typeTitle(tags)`: il valore del primo tag presente tra
   `amenity`, `shop`, `tourism`, `historic`, `leisure`, `man_made`, in
   quest'ordine, mostrato raw (es. `drinking_water`, `wayside_cross`);
   il valore `yes` viene ignorato e si passa al tag successivo;
3. `photoTitle(tags)` (filename della foto, invariato);
4. `"Nodo " + osm_id` (come oggi).

### Descrizione sotto il titolo

Se il nodo ha il tag `description`, il testo compare sotto la riga del
titolo nella modale:

- `<p id="print-description">` dentro la `figcaption`, dopo la riga
  `#caption`;
- popolato via `textContent` (niente HTML);
- nascosto (`display: none` via classe o attributo `hidden`) quando il
  tag è assente o vuoto;
- stile: testo piccolo (12px, IBM Plex Mono), colore `--ink-soft`;
- limitato a 4 righe con `line-clamp` per non spingere la foto fuori
  dallo schermo con descrizioni molto lunghe.

Solo il tag `description`: niente `description:it` o varianti (YAGNI).

## Implementazione

Solo `src/openstreetphoto/web/index.html`. Nessun cambio a
pipeline/GeoJSON: i tag sono già tutti in `properties.tags`.

## Test

- `typeTitle` con l'harness pytest+node esistente (`run_js`). Casi:
  amenity presente; priorità (amenity vince su tourism); valore `yes`
  scartato con fallback al tag successivo; nessun tag tipo → `null`.
- Descrizione: è DOM puro, verifica E2E con Playwright contro
  `osp-serve` (nodo con `description` → testo visibile; nodo senza →
  paragrafo nascosto).

## Alternative scartate

- **Solo `amenity`** (richiesta letterale): stessa logica ma copertura
  molto minore; i nodi `tourism`/`historic` senza `name` resterebbero
  sul filename o su "Nodo <id>".
- **Tradurre/abbellire i valori** (`drinking_water` → "Fontanella"):
  richiede un dizionario da mantenere; il valore raw è accettato
  esplicitamente dal committente.

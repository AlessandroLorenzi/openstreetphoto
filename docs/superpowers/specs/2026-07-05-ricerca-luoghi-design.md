# Ricerca luoghi (geocoding Nominatim)

## Obiettivo

Aggiungere alla mappa una casella di ricerca che sposta la vista su un luogo
(città, via, indirizzo). Non filtra i marker: sposta solo la mappa. Ricerca
**limitata alla zona attualmente visualizzata**.

## Scelte

- **Provider**: Nominatim pubblico (`nominatim.openstreetmap.org`). Gratuito,
  coerente con l'ecosistema OSM del progetto.
- **Ambito**: `bounded=1` + `viewbox` = i bounds correnti della mappa. I
  risultati stanno *solo* dentro il viewport. Footgun accettato: se sei
  zoomato su un quartiere e cerchi "Roma" non trovi nulla — è il
  comportamento voluto ("solo la zona che sto visualizzando").
- **User-Agent**: dal browser non è impostabile via `fetch` (header forbidden).
  Il `Referer` viene mandato in automatico e Nominatim lo accetta come
  identificazione per web app. Nessun trucco necessario.

## UI

- Casella `<input>` fissa in **alto a sinistra** (il `#counter` è a destra).
  Stile coerente: IBM Plex Mono, colori `--ink`/`--paper`, bordo squadrato.
- Sotto la casella, un `<ul>` dropdown con max 5 risultati: testo =
  `display_name` di Nominatim, inserito via `textContent` (mai innerHTML,
  come da convenzione del progetto).
- Clic su un risultato → `map.fitBounds(boundingbox)`, dropdown svuotato e
  nascosto, focus tolto dall'input.
- Nessun risultato → una riga "nessun risultato nella zona".
- `Escape` con dropdown aperto → lo chiude *senza* toccare la modale foto
  (l'handler Escape esistente della modale va reso consapevole di questo:
  se il dropdown è aperto, ha la precedenza).

## Comportamento / rete

- L'utente digita: da **≥3 caratteri** parte un **debounce di ~1000ms**.
  Una sola richiesta quando la digitazione si ferma → rispetta ≤1 req/s
  anche durante la digitazione continua. Sotto i 3 caratteri, o input
  svuotato, il dropdown si chiude e nessuna richiesta parte.
- Query:
  `https://nominatim.openstreetmap.org/search?format=json&q=<q>&limit=5&viewbox=<W>,<S>,<E>,<N>&bounded=1`
  dove `W,S,E,N` derivano da `map.getBounds()` al momento della richiesta.
- Selezione risultato → `map.fitBounds([[S,W],[N,E]])` dal campo
  `boundingbox` del risultato (`[S, N, W, E]` secondo Nominatim). Migliore
  del solo lat/lon perché dà lo zoom corretto.
- Lo spostamento mappa aggiorna già `map=` nell'hash via `moveend`: nessun
  codice nuovo sull'hash. La query di ricerca **non** finisce nell'hash.
- Errori di rete / risposta non-ok → riga "errore nella ricerca", nessun
  crash. La ricerca precedente in volo va ignorata se ne parte una nuova
  (guard su un contatore di richiesta, per evitare risultati stale).

## Test

- Helper puro **`buildSearchUrl(query, bounds)`** → ritorna la stringa URL
  con `q` URL-encoded e `viewbox`/`bounded`. Testabile con l'harness `node`
  esistente (`tests/test_web_image_url.py`): funzione autocontenuta, niente
  `{` nei literal, concatenazione di stringhe. Casi: query con spazi/accenti
  (encoding), viewbox formattato correttamente dai bounds.
- Il `fetch` verso Nominatim non è unit-testabile offline. La logica di
  mapping risultato→bounds resta in una funzione piccola
  (`resultToBounds(result)`) testabile a parte se utile.
- E2E: script throwaway con rete reale (avvia `osp-serve`, digita, verifica
  che compaia il dropdown e che la mappa si muova) — non committato, o
  saltato se la rete non è disponibile.

## Fuori scope

- Autocomplete "vero" as-you-type (Photon): escluso, il debounce basta.
- Ricerca tra i nodi-foto: escluso, questa è solo ricerca luoghi.
- Persistenza della query nell'URL.

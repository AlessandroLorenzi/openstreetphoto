# Ricerca luoghi (Nominatim) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aggiungere alla mappa una casella di ricerca che, dal 3° carattere e con debounce ~1s, interroga Nominatim limitando i risultati alla zona visualizzata e sposta la vista sul luogo scelto.

**Architecture:** Tutto nel singolo file `src/openstreetphoto/web/index.html` (CSS+HTML+JS inline, come il resto del frontend). Due helper JS puri e autocontenuti — `buildSearchUrl` e `resultToBounds` — unit-testati con l'harness `node` esistente. Il resto (input, dropdown, debounce, fetch, `fitBounds`, gestione `Escape`) è wiring DOM/rete, verificato manualmente/E2E.

**Tech Stack:** Leaflet 1.9.4 (già presente), Nominatim pubblico, `fetch`, `node` per i test JS via pytest.

## Global Constraints

- Tutto il frontend in un solo file: `src/openstreetphoto/web/index.html`. Nessun build step, nessun file web aggiuntivo.
- Testo nel DOM sempre via `textContent`, mai `innerHTML` (convenzione progetto).
- Funzioni JS testate devono essere **autocontenute**: nessuna `const` a livello di modulo usata dentro; **niente `{` nei literal** (il brace-counting dell'harness non capisce le graffe dentro stringhe/regex). Usare concatenazione di stringhe.
- Commit convenzionali **in italiano** (`feat:`, `fix:`, ...).
- `writeHash()` ricostruisce l'hash da zero a ogni `moveend`: NON aggiungere parametri all'hash per la ricerca (la query non va nell'URL).
- Endpoint: `https://nominatim.openstreetmap.org/search` con `format=json`, `limit=5`, `viewbox=<W,S,E,N>`, `bounded=1`. Nessun header custom (il `Referer` del browser basta a Nominatim).

---

### Task 1: Helper puri `buildSearchUrl` e `resultToBounds`

**Files:**
- Modify: `src/openstreetphoto/web/index.html` (aggiungere due `function` nel blocco `<script>`, vicino agli altri helper puri come `normalizeImageUrl`, prima delle righe che toccano il DOM ~riga 236)
- Test: `tests/test_web_search.py` (nuovo)

**Interfaces:**
- Consumes: niente (helper puri).
- Produces:
  - `buildSearchUrl(query, west, south, east, north)` → stringa URL Nominatim. `query` URL-encoded; `viewbox` nell'ordine `west,south,east,north`; `bounded=1`.
  - `resultToBounds(result)` → `[[south, west], [north, east]]` (numeri) da `result.boundingbox`, che Nominatim fornisce come `[south, north, west, east]` di **stringhe**. Formato pronto per `map.fitBounds`.

- [ ] **Step 1: Scrivere i test che falliscono**

Creare `tests/test_web_search.py`:

```python
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
```

- [ ] **Step 2: Eseguire i test per verificare che falliscano**

Run: `.venv/bin/pytest tests/test_web_search.py -v`
Expected: FAIL (l'harness solleva `ValueError: funzione buildSearchUrl non trovata`).

- [ ] **Step 3: Aggiungere i due helper in index.html**

Inserire nel `<script>`, dopo `photoCandidates` e prima di `const overlay = ...`:

```javascript
  // costruisce l'URL Nominatim: query URL-encoded, viewbox dai bounds
  // correnti (W,S,E,N), bounded=1 per restare dentro la zona visualizzata
  function buildSearchUrl(query, west, south, east, north) {
    const viewbox = west + "," + south + "," + east + "," + north;
    return "https://nominatim.openstreetmap.org/search?format=json&limit=5" +
      "&bounded=1&q=" + encodeURIComponent(query) +
      "&viewbox=" + encodeURIComponent(viewbox);
  }

  // Nominatim: boundingbox = [south, north, west, east] di stringhe.
  // Ritorna [[south, west], [north, east]] per map.fitBounds.
  function resultToBounds(result) {
    const b = result.boundingbox;
    return [[parseFloat(b[0]), parseFloat(b[2])], [parseFloat(b[1]), parseFloat(b[3])]];
  }
```

- [ ] **Step 4: Eseguire i test per verificare che passino**

Run: `.venv/bin/pytest tests/test_web_search.py -v`
Expected: PASS (2 test).

- [ ] **Step 5: Commit**

```bash
git add tests/test_web_search.py src/openstreetphoto/web/index.html
git commit -m "feat: helper buildSearchUrl e resultToBounds per la ricerca luoghi"
```

---

### Task 2: UI ricerca — input, dropdown, debounce, fetch, navigazione

**Files:**
- Modify: `src/openstreetphoto/web/index.html` (CSS in `<style>`; markup dopo `#counter`; JS nel `<script>`)

**Interfaces:**
- Consumes: `buildSearchUrl`, `resultToBounds` (Task 1); `map` (Leaflet, definito ~riga 307); la gestione `Escape` esistente (~riga 304).
- Produces: nessun'interfaccia per task successivi (feature terminale).

- [ ] **Step 1: CSS della barra di ricerca**

Aggiungere nel blocco `<style>`, prima di `:focus-visible`:

```css
  /* ricerca luoghi */
  #search {
    position: fixed; top: 12px; left: 12px; z-index: 1000;
    width: min(320px, calc(100vw - 24px));
  }
  #search-input {
    width: 100%;
    font: 400 13px "IBM Plex Mono", monospace;
    color: var(--ink); background: var(--paper);
    border: 2px solid var(--ink); border-radius: 2px;
    padding: 8px 12px;
  }
  #search-results {
    list-style: none; margin-top: 4px;
    background: var(--matte); border: 2px solid var(--ink); border-radius: 2px;
    box-shadow: 0 4px 12px rgba(35,39,44,.3);
  }
  #search-results[hidden] { display: none; }
  #search-results li {
    padding: 8px 12px; cursor: pointer;
    font: 400 12px/1.4 "IBM Plex Mono", monospace; color: var(--ink);
    border-top: 1px solid #E4E1DA;
  }
  #search-results li:first-child { border-top: 0; }
  #search-results li:hover, #search-results li:focus-visible { background: #EFEDE8; }
  #search-results li.msg { color: var(--ink-soft); cursor: default; }
```

- [ ] **Step 2: Markup della barra**

Aggiungere subito dopo `<div id="counter">caricamento…</div>` (~riga 111):

```html
<div id="search">
  <input id="search-input" type="text" autocomplete="off"
         placeholder="cerca un luogo nella zona…" aria-label="Cerca un luogo">
  <ul id="search-results" hidden></ul>
</div>
```

- [ ] **Step 3: JS — riferimenti, render risultati, debounce, fetch**

Aggiungere nel `<script>`, dopo il blocco `map.on("moveend", ...)` (~riga 319) così `map` esiste già:

```javascript
  // ---- ricerca luoghi (Nominatim, dal 3° carattere, debounce ~1s) ----
  const searchInput = document.getElementById("search-input");
  const searchResults = document.getElementById("search-results");
  let searchTimer = null;
  let searchSeq = 0;  // ignora risposte di richieste sorpassate

  function showSearchMessage(text) {
    searchResults.innerHTML = "";
    const li = document.createElement("li");
    li.className = "msg";
    li.textContent = text;
    searchResults.appendChild(li);
    searchResults.hidden = false;
  }

  function closeSearch() {
    searchResults.hidden = true;
    searchResults.innerHTML = "";
  }

  function renderResults(results) {
    searchResults.innerHTML = "";
    if (!results.length) {
      showSearchMessage("nessun risultato nella zona");
      return;
    }
    for (const r of results) {
      const li = document.createElement("li");
      li.textContent = r.display_name;
      li.addEventListener("click", () => {
        map.fitBounds(resultToBounds(r));
        closeSearch();
        searchInput.blur();
      });
      searchResults.appendChild(li);
    }
    searchResults.hidden = false;
  }

  function runSearch(query) {
    const b = map.getBounds();
    const url = buildSearchUrl(
      query, b.getWest(), b.getSouth(), b.getEast(), b.getNorth()
    );
    const seq = ++searchSeq;
    fetch(url, { headers: { "Accept-Language": "it" } })
      .then((r) => { if (!r.ok) throw new Error("http"); return r.json(); })
      .then((results) => { if (seq === searchSeq) renderResults(results); })
      .catch(() => { if (seq === searchSeq) showSearchMessage("errore nella ricerca"); });
  }

  searchInput.addEventListener("input", () => {
    clearTimeout(searchTimer);
    const query = searchInput.value.trim();
    if (query.length < 3) { closeSearch(); return; }
    searchTimer = setTimeout(() => runSearch(query), 1000);
  });
```

- [ ] **Step 4: JS — gestione `Escape` con precedenza sul dropdown**

Sostituire l'handler Escape esistente (~riga 304):

```javascript
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });
```

con:

```javascript
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    if (!searchResults.hidden) { closeSearch(); return; }  // il dropdown ha la precedenza
    closeModal();
  });
```

- [ ] **Step 5: Verifica manuale end-to-end**

Avviare il server e provare nel browser:

```bash
.venv/bin/osp-serve
```

Aprire `http://localhost:8000/`, poi verificare:
- Digitando 1-2 caratteri non compare nulla; dal 3° parte la ricerca (dopo ~1s di pausa).
- I risultati mostrano solo luoghi dentro la zona inquadrata (zoomare su una città e cercare qualcosa fuori → "nessun risultato nella zona").
- Clic su un risultato → la mappa ci si sposta col giusto zoom, il dropdown si chiude.
- `Escape` con dropdown aperto lo chiude senza chiudere una eventuale modale foto; con dropdown chiuso e modale aperta, chiude la modale.

Confermare a voce che tutti i punti passano prima del commit (nessun assert automatico qui: è wiring DOM/rete).

- [ ] **Step 6: Regressione test suite**

Run: `.venv/bin/pytest`
Expected: PASS (inclusi i 2 nuovi test del Task 1).

- [ ] **Step 7: Commit**

```bash
git add src/openstreetphoto/web/index.html
git commit -m "feat: barra di ricerca luoghi con Nominatim limitata alla zona visualizzata"
```

---

## Self-Review

- **Copertura spec:** provider Nominatim (Task 1/2), `bounded=1`+viewbox zona corrente (buildSearchUrl + runSearch usa `map.getBounds()`), UI top-left + dropdown `textContent` (Task 2 Step 1-3), ≥3 caratteri + debounce 1000ms (Step 3), `fitBounds` da boundingbox (resultToBounds + click handler), Escape con precedenza (Step 4), guard richieste stale (searchSeq), gestione errori (catch → messaggio), niente query nell'hash (nessuna modifica a writeHash). Helper testabile (Task 1). Tutto coperto.
- **Placeholder:** nessuno; ogni step ha codice/comandi reali.
- **Consistenza tipi:** `buildSearchUrl(query, west, south, east, north)` e `resultToBounds(result)` usati con le stesse firme in Task 2. `closeSearch`/`showSearchMessage`/`renderResults`/`runSearch` coerenti tra gli step.
- Nota vincolo harness: i due helper di Task 1 non contengono `{` in stringhe/regex — ok per il brace-counting.

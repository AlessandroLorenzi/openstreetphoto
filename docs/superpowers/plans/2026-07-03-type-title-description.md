# Titolo dal tag tipo e descrizione nella modale — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prima del fallback sul filename della foto, il titolo della modale usa il tag tipo del nodo (`amenity`, `shop`, …); se il nodo ha `description`, il testo compare sotto il titolo.

**Architecture:** Tutto in `src/openstreetphoto/web/index.html`. Una nuova funzione pura `typeTitle(tags)` entra nella catena del titolo di `openModal`; la descrizione è un `<p>` nella modale popolato via `textContent` e nascosto quando assente.

**Tech Stack:** JS vanilla inline in `index.html`; test pytest che estraggono le funzioni JS e le eseguono con `node` tramite l'helper `run_js` di `tests/test_web_image_url.py`; verifica E2E con Playwright (già in `.venv`) contro `osp-serve`.

**Spec:** `docs/superpowers/specs/2026-07-03-type-title-description-design.md`

## Global Constraints

- Solo `src/openstreetphoto/web/index.html` può cambiare, più il nuovo `tests/test_web_type_title.py`. Nessun cambio a extract/pipeline/GeoJSON.
- Catena del titolo esattamente: `props.tags.name || typeTitle(props.tags) || photoTitle(props.tags) || "Nodo " + props.osm_id`.
- Ordine dei tag tipo esattamente: `amenity`, `shop`, `tourism`, `historic`, `leisure`, `man_made`; valore mostrato raw; il valore `yes` scartato con fallback al tag successivo.
- Descrizione: solo il tag `description`, via `textContent`, nascosta quando assente o vuota, clamp a 4 righe.
- Nessuna chiamata di rete aggiuntiva a runtime.
- Commit convenzionali in italiano, senza Co-Authored-By.
- Test: `.venv/bin/pytest` dalla root del repo.

---

### Task 1: `typeTitle` nella catena del titolo

**Files:**
- Modify: `src/openstreetphoto/web/index.html` (nuova funzione dopo `photoTitle`, ~riga 180; catena del titolo in `openModal`, ~riga 250)
- Create: `tests/test_web_type_title.py`

**Interfaces:**
- Consumes: `photoTitle(tags)` esistente (resta terzo nella catena); harness `run_js(expr, *functions)` da `tests/test_web_image_url.py`.
- Produces: `typeTitle(tags) -> string | null` — `tags` è l'oggetto `properties.tags` di una feature GeoJSON.

- [ ] **Step 1: scrivere i test rossi**

Creare `tests/test_web_type_title.py`. Nota harness: `extract_function`
estrae una singola `function nome(...) {...}` dall'HTML, quindi la lista
dei tag tipo deve stare DENTRO la funzione, non in una `const` esterna.

```python
import json

import pytest

from test_web_image_url import run_js  # tests/ non e' un package: pytest mette la dir in sys.path


def type_title(tags: dict) -> str | None:
    out = run_js(f"JSON.stringify(typeTitle({json.dumps(tags)}))", "typeTitle")
    return json.loads(out)


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        # il caso della richiesta: amenity raw
        ({"amenity": "drinking_water"}, "drinking_water"),
        # priorita': amenity vince su tourism
        ({"amenity": "fountain", "tourism": "artwork"}, "fountain"),
        # tag successivi nella catena
        ({"tourism": "artwork"}, "artwork"),
        ({"historic": "wayside_cross"}, "wayside_cross"),
        ({"man_made": "water_tap"}, "water_tap"),
        # "yes" scartato con fallback al tag successivo
        ({"shop": "yes", "tourism": "artwork"}, "artwork"),
        # solo "yes": nessun titolo
        ({"man_made": "yes"}, None),
        # nessun tag tipo
        ({"name": "Bar Sport"}, None),
        ({}, None),
    ],
)
def test_type_title(tags, expected):
    assert type_title(tags) == expected
```

- [ ] **Step 2: eseguire i test e verificarli rossi**

Run: `.venv/bin/pytest tests/test_web_type_title.py -v`
Expected: FAIL — `ValueError: funzione typeTitle non trovata`.

- [ ] **Step 3: implementare `typeTitle` e aggiornare la catena**

In `index.html`, subito dopo `photoTitle`:

```js
  // titolo di fallback dal tag tipo del nodo, valore raw (es. "drinking_water").
  // La lista sta dentro la funzione: l'harness dei test estrae una funzione sola.
  function typeTitle(tags) {
    for (const key of ["amenity", "shop", "tourism", "historic", "leisure", "man_made"]) {
      const value = tags[key];
      if (value && value !== "yes") return value;
    }
    return null;
  }
```

In `openModal`, sostituire:

```js
    title.textContent =
      props.tags.name || photoTitle(props.tags) || "Nodo " + props.osm_id;
```

con:

```js
    title.textContent =
      props.tags.name || typeTitle(props.tags) || photoTitle(props.tags) ||
      "Nodo " + props.osm_id;
```

- [ ] **Step 4: eseguire i test e verificarli verdi**

Run: `.venv/bin/pytest tests/test_web_type_title.py -v`
Expected: PASS, 9 casi.

Run: `.venv/bin/pytest`
Expected: PASS, nessuna regressione.

- [ ] **Step 5: commit**

```bash
git add src/openstreetphoto/web/index.html tests/test_web_type_title.py
git commit -m "feat: titolo modale dal tag tipo (amenity, shop, ...) prima del filename"
```

---

### Task 2: descrizione sotto il titolo

**Files:**
- Modify: `src/openstreetphoto/web/index.html` (markup della modale ~riga 101-110, CSS ~riga 95, refs elementi ~riga 195, `openModal` ~riga 250)

**Interfaces:**
- Consumes: `openModal(feature)` esistente; `props.tags.description`.
- Produces: niente per task successivi.

- [ ] **Step 1: markup**

Nel `<figure id="print">`, dopo la `</figcaption>` (il markup attuale è
`<figcaption id="caption">…</figcaption>`), aggiungere:

```html
    <p id="print-description" hidden></p>
```

- [ ] **Step 2: CSS**

Nel blocco `<style>`, dopo le regole di `#caption a`:

```css
  #print-description {
    margin: -6px 2px 14px;
    font: 400 12px/1.5 "IBM Plex Mono", monospace;
    color: var(--ink-soft);
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 4;
    line-clamp: 4;
    overflow: hidden;
  }
  #print-description[hidden] { display: none; }
```

Attenzione: la regola `[hidden]` è necessaria perché `display: -webkit-box`
sovrascrive il `display: none` implicito dell'attributo `hidden`.

- [ ] **Step 3: popolare in `openModal`**

Tra i riferimenti agli elementi (accanto a `const title = …`):

```js
  const description = document.getElementById("print-description");
```

In `openModal`, dopo la riga che imposta `title.textContent`:

```js
    description.textContent = props.tags.description || "";
    description.hidden = !props.tags.description;
```

(Nessun cambio in `closeModal`: `openModal` reimposta sempre entrambe le
proprietà, quindi non resta stato sporco tra un nodo e l'altro.)

- [ ] **Step 4: suite completa**

Run: `.venv/bin/pytest`
Expected: PASS (la descrizione non ha funzioni pure estraibili: la
verifica comportamentale è nel prossimo step).

- [ ] **Step 5: verifica E2E con Playwright**

`data/photo-nodes.geojson` esiste già. Trovare i casi:

```bash
python3 - <<'EOF'
import json
feats = json.load(open("data/photo-nodes.geojson"))["features"]
def pick(pred, label):
    for f in feats:
        t = f["properties"]["tags"]
        if pred(t):
            print(label, f["properties"]["osm_id"])
            return
pick(lambda t: t.get("description"), "con description:")
pick(lambda t: "description" not in t, "senza description:")
pick(lambda t: "name" not in t and any(t.get(k) not in (None, "yes")
     for k in ("amenity", "shop", "tourism", "historic", "leisure", "man_made")), "titolo da tipo:")
EOF
```

Avviare `.venv/bin/osp-serve` in background (se la porta 8000 è occupata:
`osp-serve --port 8321`; fermarlo a fine verifica). Con uno script
Playwright throwaway nello scratchpad (NON committato) aprire
`http://localhost:<porta>/#node=<id>` per i tre nodi, attendere
`#overlay.open` e verificare:

1. nodo con `description` → `#print-description` visibile con il testo del tag;
2. nodo senza `description` → `#print-description` nascosto (attributo `hidden`);
3. nodo senza `name` con tag tipo → `#print-title` uguale al valore raw del tag.

- [ ] **Step 6: commit**

```bash
git add src/openstreetphoto/web/index.html
git commit -m "feat: mostra il tag description sotto il titolo della modale"
```

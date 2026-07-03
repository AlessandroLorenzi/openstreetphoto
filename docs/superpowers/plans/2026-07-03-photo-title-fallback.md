# Titolo modale dal nome della foto — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Quando un nodo non ha `name`, la modale usa come titolo il nome del file della foto (se "umano"), altrimenti resta "Nodo <id>".

**Architecture:** Tutto in `src/openstreetphoto/web/index.html`. Il parsing degli URL Wikimedia già presente in `normalizeImageUrl` viene estratto in `parseWikiImage` (condiviso); due nuove funzioni `humanTitle` e `photoTitle` derivano il titolo; `openModal` le usa nella catena di fallback del titolo.

**Tech Stack:** JS vanilla inline in `index.html`; test in pytest che estraggono le funzioni JS dal file HTML e le eseguono con `node` (harness esistente in `tests/test_web_image_url.py`).

**Spec:** `docs/superpowers/specs/2026-07-03-photo-title-fallback-design.md`

## Global Constraints

- Nessuna modifica a extract/pipeline/GeoJSON: solo `index.html` e test.
- Nessuna chiamata di rete aggiuntiva a runtime.
- Il comportamento di `normalizeImageUrl` non deve cambiare (i 6 casi parametrizzati esistenti devono passare invariati).
- Commit convenzionali in italiano, senza Co-Authored-By.
- Test: `.venv/bin/pytest` dalla root del repo.

---

### Task 1: estrarre `parseWikiImage` da `normalizeImageUrl`

Refactor senza cambio di comportamento: il riconoscimento dei tre pattern Wikimedia (pagina `File:`, valore nudo `File:…`, vecchio thumb) esce da `normalizeImageUrl` e diventa riusabile.

**Files:**
- Modify: `src/openstreetphoto/web/index.html` (funzione `normalizeImageUrl`, righe ~117-138)
- Modify: `tests/test_web_image_url.py` (l'helper `normalize` deve estrarre anche la nuova funzione)

**Interfaces:**
- Produces: `parseWikiImage(url) -> {host: string, name: string} | null` — `host` è l'origine per `Special:FilePath` (es. `"https://commons.wikimedia.org"`), `name` è il filename **URL-encoded** senza prefisso `File:`. Ritorna `null` se l'URL non è riconducibile a un file Wikimedia.
- Produces: `normalizeImageUrl(url) -> string` — firma e comportamento invariati.

- [ ] **Step 1: aggiornare l'harness di test per estrarre più funzioni**

In `tests/test_web_image_url.py`, sostituire l'helper `normalize` così che il
codice passato a `node` contenga sia `parseWikiImage` sia `normalizeImageUrl`
(la seconda chiamerà la prima):

```python
def run_js(expr: str, *functions: str) -> str:
    source = HTML.read_text()
    script = "\n".join(extract_function(source, f) for f in functions)
    script += f"\nconsole.log({expr});"
    out = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


def normalize(url: str) -> str:
    return run_js(
        f"normalizeImageUrl({json.dumps(url)})",
        "parseWikiImage",
        "normalizeImageUrl",
    )
```

- [ ] **Step 2: eseguire i test e verificarli rossi**

Run: `.venv/bin/pytest tests/test_web_image_url.py -v`
Expected: FAIL — `ValueError: funzione parseWikiImage non trovata` (la funzione non esiste ancora nell'HTML).

- [ ] **Step 3: implementare `parseWikiImage` e riscrivere `normalizeImageUrl`**

In `index.html`, sostituire l'attuale `normalizeImageUrl` (conservando il
commento esistente sui tag `image=` non-URL) con:

```js
  // molti tag image= non sono URL diretti di immagini: pagine File: di Commons o
  // delle Wikipedia, valori nudi File:..., vecchi thumbnail che oggi rispondono 400.
  // parseWikiImage riconosce questi casi e ritorna host e filename (URL-encoded).
  function parseWikiImage(url) {
    const filePage = url.match(
      /^(https?:\/\/[a-z-]+\.(?:m\.)?(?:wikimedia|wikipedia)\.org)\/wiki\/File:(.+)$/
    );
    if (filePage) {
      return { host: filePage[1], name: filePage[2] };
    }
    if (url.startsWith("File:")) {
      return {
        host: "https://commons.wikimedia.org",
        name: encodeURIComponent(url.slice(5)),
      };
    }
    const thumb = url.match(
      /^https?:\/\/upload\.wikimedia\.org\/wikipedia\/commons\/thumb\/\w\/\w\w\/([^/]+)\//
    );
    if (thumb) {
      return { host: "https://commons.wikimedia.org", name: thumb[1] };
    }
    return null;
  }

  // riscrive su Special:FilePath, che risolve sempre il file corrente
  function normalizeImageUrl(url) {
    const wiki = parseWikiImage(url);
    if (!wiki) return url;
    return wiki.host + "/wiki/Special:FilePath/" + wiki.name + "?width=1024";
  }
```

- [ ] **Step 4: eseguire i test e verificarli verdi**

Run: `.venv/bin/pytest tests/test_web_image_url.py -v`
Expected: PASS, tutti i 6 casi parametrizzati (comportamento invariato).

Run: `.venv/bin/pytest`
Expected: PASS, nessuna regressione altrove.

- [ ] **Step 5: commit**

```bash
git add src/openstreetphoto/web/index.html tests/test_web_image_url.py
git commit -m "refactor: estrae parseWikiImage da normalizeImageUrl"
```

---

### Task 2: `humanTitle` e `photoTitle`

Le due funzioni che derivano il titolo dal filename, con filtro anti-nomi-macchina.

**Files:**
- Modify: `src/openstreetphoto/web/index.html` (dopo `normalizeImageUrl`)
- Create: `tests/test_web_photo_title.py`

**Interfaces:**
- Consumes: `parseWikiImage(url)` dal Task 1.
- Produces: `photoTitle(tags) -> string | null` — `tags` è l'oggetto `properties.tags` di una feature GeoJSON; ritorna il titolo derivato o `null` se non derivabile / non "umano".
- Produces: `humanTitle(fileName) -> string | null` — da un filename (eventualmente URL-encoded) a titolo pulito, o `null` se somiglia a un nome generato da macchina.

- [ ] **Step 1: scrivere i test rossi**

Creare `tests/test_web_photo_title.py`:

```python
import json

import pytest

from test_web_image_url import run_js  # tests/ non e' un package: pytest mette la dir in sys.path


def photo_title(tags: dict) -> str | None:
    out = run_js(
        f"JSON.stringify(photoTitle({json.dumps(tags)}))",
        "parseWikiImage",
        "humanTitle",
        "photoTitle",
    )
    return json.loads(out)


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        # wikimedia_commons: underscore -> spazi, via l'estensione
        ({"wikimedia_commons": "File:Chiesa_di_San_Rocco.jpg"}, "Chiesa di San Rocco"),
        # image= pagina File: su Commons, filename URL-encoded
        (
            {"image": "https://commons.wikimedia.org/wiki/File:Cascina_%22La_Torretta%22.JPG"},
            'Cascina "La Torretta"',
        ),
        # image= valore nudo File:
        ({"image": "File:Lavatoio di Brunate.png"}, "Lavatoio di Brunate"),
        # wikimedia_commons ha priorita' su image
        (
            {"wikimedia_commons": "File:Duomo_di_Como.jpg", "image": "File:Altro.jpg"},
            "Duomo di Como",
        ),
        # nome macchina -> None
        ({"wikimedia_commons": "File:IMG_20230512_101530.jpg"}, None),
        ({"wikimedia_commons": "File:DSC00123.jpg"}, None),
        ({"wikimedia_commons": "File:P1010001.jpg"}, None),
        ({"image": "File:20230512 101530.jpg"}, None),
        # ma wikimedia_commons macchina + image umano -> usa image
        (
            {"wikimedia_commons": "File:IMG_1234.jpg", "image": "File:Fontana vecchia.jpg"},
            "Fontana vecchia",
        ),
        # URL image= non Wikimedia: nessuna derivazione
        ({"image": "https://example.com/foto.jpg"}, None),
        # panoramax da solo: nessuna derivazione
        ({"panoramax": "a1b2c3d4-0000-0000-0000-000000000000"}, None),
        # wikimedia_commons Category: ignorato
        ({"wikimedia_commons": "Category:Brunate"}, None),
        # percent literale nel valore raw: decodeURIComponent fallirebbe, non deve rompere
        ({"wikimedia_commons": "File:100%_cotone.jpg"}, "100%_cotone"),
    ],
)
def test_photo_title(tags, expected):
    assert photo_title(tags) == expected
```

Nota sull'ultimo caso: il valore di `wikimedia_commons` è testo raw, non
URL-encoded; `decodeURIComponent("100%_cotone")` lancia, quindi
`humanTitle` deve fare il decode in `try/catch` e in caso di errore usare
il valore com'è (underscore compresi: senza decode non distinguiamo se
l'underscore è "vero", meglio non toccarlo — il caso è raro).

- [ ] **Step 2: eseguire i test e verificarli rossi**

Run: `.venv/bin/pytest tests/test_web_photo_title.py -v`
Expected: FAIL — `ValueError: funzione humanTitle non trovata`.

- [ ] **Step 3: implementare `humanTitle` e `photoTitle`**

In `index.html`, subito dopo `normalizeImageUrl`:

```js
  // da filename a titolo: decode, via estensione, underscore -> spazi.
  // null se somiglia a un nome generato da fotocamera/app (meglio "Nodo ..."
  // che "IMG 20230512 101530").
  function humanTitle(fileName) {
    let name;
    try {
      name = decodeURIComponent(fileName);
      name = name.replace(/_/g, " ");
    } catch {
      name = fileName; // valore raw con % literale: non decodificabile, lasciato com'e'
    }
    name = name.replace(/\.(jpe?g|png|webp|gif|tiff?|svg)$/i, "").trim();
    if (/^(IMG|DSC[NF]?|P\d|PXL|DJI|GOPR|Screenshot|WhatsApp Image)[ _-]?\d/i.test(name)) {
      return null;
    }
    if (/^[\d\s\-.]*$/.test(name)) return null; // solo cifre/date/timestamp, o vuoto
    return name;
  }

  // titolo di fallback per i nodi senza name, dal filename della foto
  function photoTitle(tags) {
    if (tags.wikimedia_commons && tags.wikimedia_commons.startsWith("File:")) {
      const t = humanTitle(tags.wikimedia_commons.slice(5));
      if (t) return t;
    }
    if (tags.image) {
      const wiki = parseWikiImage(tags.image);
      if (wiki) return humanTitle(wiki.name);
    }
    return null;
  }
```

Attenzione all'ordine dentro `humanTitle`: la sostituzione `_ -> spazio`
sta nel ramo riuscito del decode, così il caso non-decodificabile resta
intatto (come da test `100%_cotone`).

- [ ] **Step 4: eseguire i test e verificarli verdi**

Run: `.venv/bin/pytest tests/test_web_photo_title.py -v`
Expected: PASS, tutti i casi parametrizzati.

Run: `.venv/bin/pytest`
Expected: PASS.

- [ ] **Step 5: commit**

```bash
git add src/openstreetphoto/web/index.html tests/test_web_photo_title.py
git commit -m "feat: photoTitle deriva un titolo dal filename della foto"
```

---

### Task 3: usare `photoTitle` in `openModal` e verificare a mano

**Files:**
- Modify: `src/openstreetphoto/web/index.html` (funzione `openModal`, riga ~213)

**Interfaces:**
- Consumes: `photoTitle(tags)` dal Task 2.

- [ ] **Step 1: cambiare la catena del titolo**

In `openModal`, sostituire:

```js
    title.textContent = props.tags.name || "Nodo " + props.osm_id;
```

con:

```js
    title.textContent =
      props.tags.name || photoTitle(props.tags) || "Nodo " + props.osm_id;
```

- [ ] **Step 2: eseguire tutta la suite**

Run: `.venv/bin/pytest`
Expected: PASS.

- [ ] **Step 3: verifica manuale con osp-serve**

Servono `data/photo-nodes.geojson` (se manca: `osp-download && osp-extract`)
e il server: `.venv/bin/osp-serve` su http://localhost:8000/.

Trovare i casi nel GeoJSON, ad esempio:

```bash
python3 - <<'EOF'
import json
feats = json.load(open("data/photo-nodes.geojson"))["features"]
def pick(pred, label):
    for f in feats:
        t = f["properties"]["tags"]
        if pred(t):
            print(label, f["properties"]["osm_id"], t.get("wikimedia_commons") or t.get("image"))
            return
pick(lambda t: "name" not in t and t.get("wikimedia_commons", "").startswith("File:")
     and not t["wikimedia_commons"].startswith("File:IMG"), "descrittivo:")
pick(lambda t: "name" not in t and t.get("wikimedia_commons", "").startswith("File:IMG"), "macchina:")
pick(lambda t: "name" in t, "con name:")
EOF
```

Aprire i tre nodi via permalink `http://localhost:8000/#node=<osm_id>` e
verificare: filename descrittivo → titolo derivato (senza estensione né
underscore); filename tipo `IMG_…` → "Nodo <id>"; nodo con `name` →
titolo invariato.

- [ ] **Step 4: commit**

```bash
git add src/openstreetphoto/web/index.html
git commit -m "feat: titolo modale dal nome della foto se il nodo non ha name"
```

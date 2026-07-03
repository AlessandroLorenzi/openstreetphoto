# Design: downloader estratto OSM Lombardia

Data: 2026-07-03
Stato: approvato

## Obiettivo

CLI Python che scarica l'estratto OpenStreetMap della Lombardia
(`lombardia-latest.osm.pbf`, ~350 MB) da `download.openstreetmap.fr`
in una directory dati locale, evitando download inutili.

## Sorgente dati

- URL di default: `http://download.openstreetmap.fr/extracts/europe/italy/lombardia-latest.osm.pbf`
- Motivazione: Geofabrik non pubblica un estratto Lombardia (il taglio più
  piccolo è `italy/nord-ovest`); OSM France sì, aggiornato quotidianamente.
- L'URL è sovrascrivibile da CLI (`--url`) per scaricare altre regioni
  senza modifiche al codice.

## Struttura del progetto

```
openstreetphoto/
├── pyproject.toml          # progetto installabile, entry point CLI
├── src/openstreetphoto/
│   ├── __init__.py
│   └── download.py         # logica download + CLI (argparse)
└── tests/
    └── test_download.py
```

## Comportamento

Comando: `osp-download [--dest data/] [--url URL] [--force]`

1. **Skip se aggiornato**: prima del download esegue una richiesta `HEAD`
   e confronta `Last-Modified` e `Content-Length` con i metadati salvati
   dell'ultimo download riuscito (file `<nome>.meta.json` accanto al PBF).
   Se identici, esce con messaggio "già aggiornato" ed exit code 0.
   `--force` scarica comunque.
2. **Download atomico**: streaming su file temporaneo `<nome>.part` con
   progress bar (`tqdm`); a download completato rinomina atomicamente sul
   nome finale e scrive il `.meta.json`. Un PBF valido non viene mai
   sostituito da uno troncato.
3. **Ripresa**: se esiste un `.part` parziale, riprende dal byte mancante
   con header `Range` (verificato: il server nginx lo supporta). Se il
   server risponde 200 invece di 206, il `.part` viene scartato e il
   download riparte da zero.
4. **Errori**: errori di rete o HTTP → messaggio chiaro su stderr ed
   exit code ≠ 0. Nessun retry automatico.

## Dipendenze

- Runtime: `requests`, `tqdm`
- Test: `pytest`, `responses` (mock HTTP)
- Python ≥ 3.11

## Test

- Skip quando i metadati corrispondono alla risposta `HEAD`.
- Download completo: file scritto, `.part` rimosso, meta salvati.
- Ripresa: `.part` esistente + risposta 206 → contenuto concatenato corretto.
- Ripresa degradata: risposta 200 → riparte da zero.
- Errore HTTP → exit code ≠ 0, file preesistente intatto.

## Fuori scope

Parsing/estrazione dal PBF, scheduling, retry automatici, altre sorgenti
(Geofabrik + clip osmium).

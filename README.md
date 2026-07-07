# Der Holzwickeder

Persönliche Tageszeitung als selbst-enthaltene HTML-Seite (Artifact), gebaut aus kostenlosen APIs.
Leser: genau einer. Erscheint täglich morgens.

**Artifact-URL (IMMER auf dieselbe URL redeployen, Favicon 📰 beibehalten):**
`https://claude.ai/code/artifact/a6b00225-e477-4386-a1f3-b73f139cf61c`

## Architektur

```
fetch.ps1        holt alle Rohdaten -> data/*.json|xml + data/fetch-report.json (Selbst-Report)
parse_sources.py normalisiert alles (RSS/Atom/RDF + JSON), meldet Fehler in PROBLEME
peek.py          kompakte Schlagzeilen-Übersicht -> Input für die Kuratierung
data/curated.json  redaktionelle Entscheidungen des Tages (von Claude geschrieben)
build.py         rendert zeitung.html (100 % offline: Fonts + Bild als data-URIs)
ausgaben/        Archiv, eine HTML-Datei pro Tag
fonts/           UnifrakturMaguntia (Wortmarke), Playfair Display 700/900 (Schlagzeilen)
```

Brotschrift ist bewusst System-Serif (Charter auf iOS, Georgia sonst) - kein Download nötig.

## Tagesprotokoll (für die tägliche Claude-Session)

1. `& fetch.ps1` ausführen. Report prüfen: steht in der Ausgabe `X FAIL`, kaputte Quelle
   reparieren oder bewusst weglassen (niemals still ignorieren).
2. `python peek.py` lesen (NICHT die Rohdaten-Dateien öffnen, Token-Ökonomie).
3. `data/curated.json` neu schreiben:
   - `datum` (heute), `ausgabe_nr` (+1 zur letzten Datei in `ausgaben/`)
   - `aufmacher`: wichtigste Geschichte des Tages wählen (quelle = welt|deutschland, idx),
     `einordnung` selbst formulieren (3-4 Sätze, Zeit-Ton, keine Phrasen)
   - Aufmacher-Bild: 16x9-960-Variante aus `teaserImage.imageVariants` des gewählten
     tagesschau-Artikels per `Invoke-WebRequest` nach `data/aufmacher.jpg` laden,
     `bild_credit` + `bild_alt` aus dem JSON übernehmen
   - `editorial`: Morgen-Briefing über alle Ressorts (4-6 Sätze)
   - `tech_heise_idx` / `tech_hn_idx`: 5 + 5 Artikel wählen. Interessenprofil des Lesers:
     Sicherheit, KI, Windows-Praxis, Apple/iPhone, Netzpolitik, Selbstbau/Open Source
   - `horoskop_de`: den englischen Text aus `data/horoskop.json` frei und gut übersetzen
   - `sport_hinweis`: Saisonstand einordnen (Sommerpause, Spieltag, WM usw.)
4. `python build.py` - muss `Keine Parse-Probleme.` melden.
5. Verifizieren (Pflicht, nicht behaupten): Sektionen == 8, kein `>None<`, 0 Em-Dashes (`—`),
   HTML wohlgeformt (html.parser-Check wie in Session 1), Dateigröße plausibel (200-400 KB).
6. Artifact-Tool: `zeitung.html` auf die oben genannte URL redeployen,
   `label` = "Ausgabe Nr. N (Datum)", Favicon 📰 unverändert.

## Stil-Invarianten (nicht verhandelbar)

- Sprache Deutsch, Anführungszeichen „so", KEINE Gedankenstriche (—) im sichtbaren Text.
- Ein Akzent: Zeitungsrot (`--akzent`). Grün nur semantisch für Plus-Kurse.
- Wortmarke bleibt „Der Holzwickeder." mit rotem Punkt, Fraktur.
- Überschriften/Anrisse sind Zitate der Quellen und verlinken dorthin (Presseschau-Prinzip,
  privat und nicht-kommerziell). Eigene Texte: Einordnung, Editorial, Horoskop-Übersetzung.
- Layout: 8 Seiten, horizontales Blättern (scroll-snap). Reihenfolge:
  Titelseite, Welt, Deutschland, Lokales, Sport, Börse, Tech, Panorama.

## Saisonale Wartung

- OpenLigaDB-Saisonparameter in fetch.ps1 (`getbltable/bl1/2025`) ab August 2026 auf `2026`
  stellen; build.py zeigt dann automatisch laufende Tabelle statt Abschlusstabelle
  (Beschriftung in seite_sport ggf. anpassen).
- Wenn `bl_spiele` unfertige Spiele enthält (Saison läuft), lohnt ein Spieltags-Block; Code
  ist defensiv, zeigt derzeit nur die Tabelle.

## Quellen (alle kostenlos, Stand Juli 2026)

tagesschau-API (Welt/Inland/Wirtschaft) · Nordstadtblogger + Ruhr Nachrichten (Dortmund) ·
Rundblick Unna (Kreis Unna) · WDR-Newsticker (Reserve) · kicker-Feeds (Sport + BVB-Teamfeed) ·
sportschau-Feed · OpenLigaDB (Tabelle) · Open-Meteo (Wetter Holzwickede 51.617/7.617) ·
Yahoo-Finance-Chart-Endpunkt (Indizes/Aktien/ETFs; stooq ist hier 404!) · Frankfurter/EZB (FX) ·
gold-api.com (XAU/XAG) · CoinGecko (BTC/ETH) · heise-Atom · Hacker-News-API · Horoscope-App-API
(vercel, englisch). Hellweger-Feed = Duplikat der Ruhr Nachrichten, wird geholt, aber nicht gerendert.

Firmenrechner: immer `Invoke-WebRequest`/`Invoke-RestMethod` (Windows-Zertifikatspeicher),
niemals curl. Headless-Browser sind blockiert; Verifikation läuft über die Checks in Punkt 5.

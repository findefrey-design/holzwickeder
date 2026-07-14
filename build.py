# -*- coding: utf-8 -*-
"""Der Holzwickeder - Renderer.

Baut aus data/ + data/curated.json eine komplett eigenstaendige HTML-Zeitung
(Fonts und Bilder als data-URIs eingebettet, kein einziger externer Request).
Ausgabe: zeitung.html + ausgaben/<datum>.html
"""
import base64
import html
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
import parse_sources as ps

HIER = Path(__file__).parent
DATA = HIER / "data"
FONTS = HIER / "fonts"

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]

WETTERCODE = {
    0: ("Klarer Himmel", "☀"), 1: ("Überwiegend sonnig", "\U0001F324"),
    2: ("Teils bewölkt", "⛅"), 3: ("Bedeckt", "☁"),
    45: ("Nebel", "\U0001F32B"), 48: ("Reifnebel", "\U0001F32B"),
    51: ("Leichter Niesel", "\U0001F326"), 53: ("Niesel", "\U0001F326"), 55: ("Starker Niesel", "\U0001F327"),
    61: ("Leichter Regen", "\U0001F326"), 63: ("Regen", "\U0001F327"), 65: ("Starker Regen", "\U0001F327"),
    66: ("Gefrierender Regen", "\U0001F327"), 67: ("Gefrierender Regen", "\U0001F327"),
    71: ("Leichter Schneefall", "❄"), 73: ("Schneefall", "❄"), 75: ("Starker Schneefall", "❄"),
    77: ("Schneegriesel", "❄"),
    80: ("Leichte Schauer", "\U0001F326"), 81: ("Schauer", "\U0001F327"), 82: ("Heftige Schauer", "\U0001F327"),
    95: ("Gewitter", "⛈"), 96: ("Gewitter mit Hagel", "⛈"), 99: ("Schweres Gewitter", "⛈"),
}

AKTIEN_NAMEN = {
    "^GDAXI": "DAX", "^GSPC": "S&P 500", "^IXIC": "Nasdaq Composite",
    "AAPL": "Apple", "NVDA": "Nvidia", "MSFT": "Microsoft",
    "SAP.DE": "SAP", "SIE.DE": "Siemens", "ASML": "ASML",
    "VWCE.DE": "Vanguard FTSE All-World (ETF)", "EUNL.DE": "iShares Core MSCI World (ETF)",
}

LOKAL_WOERTER = ("dortmund", "unna", "holzwickede", "schwerte", "lünen", "kamen", "bergkamen",
                 "fröndenberg", "werne", "selm", "bönen", "a45", " b1", "a44", "bvb",
                 "brackel", "scharnhorst", "ruhrgebiet", "nrw")


def esc(t) -> str:
    return html.escape(str(t or ""), quote=True)


def dezahl(x, stellen=2) -> str:
    """1234.5 -> '1.234,50' (deutsches Zahlenformat)."""
    if x is None:
        return "?"
    s = f"{x:,.{stellen}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def b64(path: Path, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def wetter_text(code) -> tuple[str, str]:
    return WETTERCODE.get(int(code or 0), ("Wechselhaft", "⛅"))


# ------------------------------------------------------------------ Bausteine

LESER_TEMPLATES: list[str] = []


def _leser_registrieren(it: dict, quelle: str) -> int:
    """Baut die Leseansicht eines Artikels und gibt seine Nummer zurueck."""
    nr = len(LESER_TEMPLATES)
    koerper = []
    for a in it.get("volltext") or []:
        if a["art"] == "h2":
            koerper.append(f"<h2>{esc(a['text'])}</h2>")
        elif a["art"] == "li":
            koerper.append(f'<p class="aufzaehlung">– {esc(a["text"])}</p>')
        elif a["art"] == "quote":
            koerper.append(f"<blockquote>{esc(a['text'])}</blockquote>")
        else:
            koerper.append(f"<p>{esc(a['text'])}</p>")
    if not koerper:
        if it.get("teaser"):
            koerper.append(f"<p>{esc(it['teaser'])}</p>")
        koerper.append('<p class="hinweis">Für diesen Artikel stellt die Quelle der Zeitung '
                       'nur den Anriss bereit; der vollständige Text liegt beim Original.</p>')
    quelle_link = ""
    if it.get("url"):
        quelle_link = (f'<p class="leser-quelle"><a href="{esc(it["url"])}" target="_blank" '
                       f'rel="noopener">Original bei {esc(quelle)} öffnen ↗</a></p>')
    kicker = f'<p class="kicker">{esc(it["topline"])}</p>' if it.get("topline") else ""
    meta_teile = [quelle]
    if it.get("punkte"):
        meta_teile.append(f'{it["punkte"]} Punkte, {it.get("kommentare", 0)} Kommentare')
    zeit = _dt_uhr(it.get("datum", ""))
    if zeit:
        meta_teile.append(zeit)
    LESER_TEMPLATES.append(
        f'<template id="art-{nr}">{kicker}<h1>{esc(it["titel"])}</h1>'
        f'<p class="meta">{esc(" · ".join(meta_teile))}</p>'
        f'<div class="textkoerper">{"".join(koerper)}</div>'
        f'{quelle_link}<p class="schlussmarke">❦</p></template>')
    return nr


def artikel(it: dict, gross=False, quelle="") -> str:
    kicker = it.get("topline") or ""
    klass = "artikel gross" if gross else "artikel"
    nr = _leser_registrieren(it, quelle)
    teile = [f'<article class="{klass}">']
    if kicker:
        teile.append(f'<p class="kicker">{esc(kicker)}</p>')
    teile.append(f'<h3><button type="button" class="art-link" data-art="{nr}">{esc(it.get("titel"))}</button></h3>')
    if it.get("teaser"):
        teile.append(f'<p class="teaser">{esc(it["teaser"])}</p>')
    meta = quelle if (it.get("volltext") or not it.get("url")) else f"{quelle} · Anriss"
    if it.get("punkte"):
        meta = f'{quelle} · {it["punkte"]} Punkte'
    if meta:
        teile.append(f'<p class="meta">{esc(meta)}</p>')
    teile.append("</article>")
    return "".join(teile)


def _dt_uhr(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%H:%M Uhr")
    except (ValueError, TypeError):
        return ""


def artikel_liste(items: list, quelle: str, n: int, erste_gross=True, ohne_titel: set | None = None) -> str:
    ohne_titel = ohne_titel or set()
    out, zaehler = [], 0
    for it in items:
        if it["titel"] in ohne_titel:
            continue
        ohne_titel.add(it["titel"])
        out.append(artikel(it, gross=(erste_gross and zaehler == 0), quelle=quelle))
        zaehler += 1
        if zaehler >= n:
            break
    return "\n".join(out)


def kurszeile(name: str, wert: str, delta_pct=None, einheit="") -> str:
    d = ""
    if delta_pct is not None:
        pfeil = "▲" if delta_pct >= 0 else "▼"
        klasse = "plus" if delta_pct >= 0 else "minus"
        d = f'<td class="delta {klasse}">{pfeil} {dezahl(abs(delta_pct))} %</td>'
    else:
        d = '<td class="delta"></td>'
    return (f'<tr><td class="kursname">{esc(name)}</td>'
            f'<td class="kurswert">{wert}{(" " + einheit) if einheit else ""}</td>{d}</tr>')


def kursblock(titel: str, zeilen: list[str]) -> str:
    return (f'<div class="kursblock"><h4>{esc(titel)}</h4>'
            f'<table class="kurse">{"".join(zeilen)}</table></div>')


# ------------------------------------------------------------------ Seiten

def seite_titel(q, cur, nav_titel):
    auf_quelle = cur["aufmacher"]["quelle"]
    auf = q[auf_quelle][cur["aufmacher"]["idx"]]
    bild_html = ""
    bild_pfad = DATA / cur["aufmacher"].get("bild", "")
    if cur["aufmacher"].get("bild") and bild_pfad.exists():
        uri = b64(bild_pfad, "image/jpeg")
        bild_html = (f'<figure><img src="{uri}" alt="{esc(cur["aufmacher"].get("bild_alt"))}">'
                     f'<figcaption>{esc(cur["aufmacher"].get("bild_credit"))}</figcaption></figure>')

    w = q["wetter"] or {}
    aktuell = w.get("current", {})
    heute_max = (w.get("daily", {}).get("temperature_2m_max") or ["?"])[0]
    heute_min = (w.get("daily", {}).get("temperature_2m_min") or ["?"])[0]
    regen = (w.get("daily", {}).get("precipitation_probability_max") or ["?"])[0]
    zustand, glyph = wetter_text(aktuell.get("weather_code"))

    dax = next((b for b in q["boerse"] if b["symbol"] == "^GDAXI"), None)
    gold = q["gold"] or {}
    btc = (q["krypto"] or {}).get("bitcoin", {})
    usd = ((q["fx"] or {}).get("rates") or {}).get("USD")

    inhalt = "".join(
        f'<li><button class="sprung" data-ziel="{i + 1}"><span class="inhalt-ressort">{esc(r)}</span> {esc(t)}</button></li>'
        for i, (r, t) in enumerate(nav_titel)
    )

    zahlen = []
    if dax:
        zahlen.append(kurszeile("DAX", dezahl(dax["preis"]), dax["delta_pct"]))
    if usd:
        zahlen.append(kurszeile("Euro in Dollar", dezahl(usd, 4)))
    if gold.get("price"):
        zahlen.append(kurszeile("Gold (Unze)", dezahl(gold["price"]), einheit="$"))
    if btc.get("eur"):
        zahlen.append(kurszeile("Bitcoin", dezahl(btc["eur"], 0), btc.get("eur_24h_change"), "€"))

    auf_nr = _leser_registrieren(auf, "tagesschau.de")
    return f"""
<div class="aufmacher">
  <p class="kicker">{esc(auf.get("topline") or "Der Tag")}</p>
  <h2><button type="button" class="art-link" data-art="{auf_nr}">{esc(auf["titel"])}</button></h2>
  {bild_html}
  <p class="einordnung initial">{esc(cur["aufmacher"].get("einordnung") or auf.get("teaser"))}</p>
  <p class="meta">Zum Weiterlesen Überschrift antippen · Quelle: tagesschau.de</p>
</div>
<hr class="linie">
<div class="titel-raster">
  <div class="wetterkachel">
    <h4>Das Wetter in Holzwickede</h4>
    <p class="wetter-gross">{glyph} {dezahl(aktuell.get("temperature_2m"), 0)}°</p>
    <p class="wetter-zustand">{esc(zustand)}</p>
    <p class="wetter-detail">Heute {dezahl(heute_max, 0)}° / {dezahl(heute_min, 0)}° · Regenrisiko {esc(regen)} %</p>
    <p class="wetter-detail leise">Mehr auf der Panorama-Seite</p>
  </div>
  <div class="zahlenkachel">
    <h4>Die Zahlen des Tages</h4>
    <table class="kurse">{"".join(zahlen)}</table>
  </div>
</div>
<hr class="linie">
<div class="editorial">
  <h4>Worum es heute geht</h4>
  <p>{esc(cur.get("editorial"))}</p>
</div>
<hr class="linie">
<div class="inhalt">
  <h4>In dieser Ausgabe</h4>
  <ul class="inhaltsliste">{inhalt}</ul>
</div>
"""


def seite_welt(q, cur):
    ohne = {q["welt"][cur["aufmacher"]["idx"]]["titel"]} if cur["aufmacher"]["quelle"] == "welt" else set()
    return artikel_liste(q["welt"], "tagesschau.de", 8, ohne_titel=ohne)


def seite_deutschland(q):
    return artikel_liste(q["deutschland"], "tagesschau.de", 8)


def lokal_relevant(it):
    text = (it["titel"] + " " + it.get("teaser", "")).lower()
    return any(w in text for w in LOKAL_WOERTER)


def seite_lokales(q):
    gesehen: set = set()
    dortmund = artikel_liste(q["dortmund"], "Nordstadtblogger", 5, ohne_titel=gesehen)
    rn = [it for it in q["ruhrnachrichten"] if lokal_relevant(it)]
    rn_html = artikel_liste(rn, "Ruhr Nachrichten", 4, erste_gross=False, ohne_titel=gesehen)
    unna = artikel_liste(q["kreis_unna"], "Rundblick Unna", 6, ohne_titel=gesehen)
    return f"""
<h3 class="rubrik">Dortmund</h3>
{dortmund}
{rn_html}
<h3 class="rubrik">Kreis Unna</h3>
{unna}
"""


def seite_sport(q, cur):
    gesehen: set = set()
    tag = artikel_liste(q["sportschau"], "sportschau.de", 3, ohne_titel=gesehen)
    tag2 = artikel_liste(q["sport"], "kicker", 4, erste_gross=False, ohne_titel=gesehen)
    bvb = artikel_liste(q["bvb"], "kicker", 6, ohne_titel=gesehen)

    zeilen = []
    for platz, t in enumerate(q["bl_tabelle"], 1):
        hervor = ' class="bvb-zeile"' if "Dortmund" in t["team"] else ""
        zeilen.append(f'<tr{hervor}><td class="platz">{platz}</td><td>{esc(t["team"])}</td>'
                      f'<td class="num">{t["spiele"]}</td><td class="num">{t["diff"]:+d}</td>'
                      f'<td class="num punkte">{t["punkte"]}</td></tr>')
        if platz >= 9 and "Dortmund" not in t["team"] and any("Dortmund" in x["team"] for x in q["bl_tabelle"][platz:]):
            continue
        if platz >= 9:
            break
    tabelle = ("".join(zeilen)) if zeilen else "<tr><td>Tabelle derzeit nicht verfügbar</td></tr>"

    return f"""
<h3 class="rubrik">Der Tag im Sport</h3>
{tag}
{tag2}
<h3 class="rubrik">Borussia Dortmund</h3>
{bvb}
<h3 class="rubrik">Bundesliga</h3>
<p class="hinweis">{esc(cur.get("sport_hinweis", ""))}</p>
<table class="tabelle">
  <thead><tr><th></th><th>Verein</th><th>Sp</th><th>Diff</th><th>Pkt</th></tr></thead>
  <tbody>{tabelle}</tbody>
</table>
<p class="meta">Abschlusstabelle 2025/26 · Quelle: OpenLigaDB</p>
"""


def seite_boerse(q):
    b = {x["symbol"]: x for x in q["boerse"]}

    def zeile(sym):
        x = b.get(sym)
        if not x:
            return ""
        einheit = "€" if x["waehrung"] == "EUR" else "$"
        return kurszeile(AKTIEN_NAMEN.get(sym, sym), dezahl(x["preis"]), x["delta_pct"], einheit)

    fx = ((q["fx"] or {}).get("rates") or {})
    usdkurs = fx.get("USD")
    gold, silber = q["gold"] or {}, q["silber"] or {}
    metalle = []
    for name, m in (("Gold (Feinunze)", gold), ("Silber (Feinunze)", silber)):
        if m.get("price"):
            eur = f' <span class="leise">({dezahl(m["price"] / usdkurs)} €)</span>' if usdkurs else ""
            metalle.append(kurszeile(name, dezahl(m["price"]) + " $" + eur))

    krypto = q["krypto"] or {}
    kzeilen = []
    for name, key in (("Bitcoin", "bitcoin"), ("Ethereum", "ethereum")):
        k = krypto.get(key, {})
        if k.get("eur"):
            kzeilen.append(kurszeile(name, dezahl(k["eur"], 0), k.get("eur_24h_change"), "€"))

    fxzeilen = [kurszeile(f"1 Euro in {w}", dezahl(kurs, 4 if w != "JPY" else 2))
                for w, kurs in fx.items()]

    wirtschaft = artikel_liste(q["wirtschaft_news"], "tagesschau.de", 5)

    return f"""
{kursblock("Indizes", [zeile(s) for s in ("^GDAXI", "^GSPC", "^IXIC")])}
{kursblock("Aktien Europa und USA", [zeile(s) for s in ("SAP.DE", "SIE.DE", "ASML", "AAPL", "NVDA", "MSFT")])}
{kursblock("ETFs (Welt)", [zeile(s) for s in ("VWCE.DE", "EUNL.DE")])}
{kursblock("Edelmetalle", metalle)}
{kursblock("Krypto (24-Stunden-Veränderung)", kzeilen)}
{kursblock("Wechselkurse (EZB-Referenz)", fxzeilen)}
<p class="meta">Kurse: Yahoo Finance, gold-api.com, CoinGecko, Frankfurter/EZB · Veränderung zum Vortagesschluss · keine Anlageberatung</p>
<hr class="linie">
<h3 class="rubrik">Aus der Wirtschaft</h3>
{wirtschaft}
"""


def seite_tech(q, cur):
    heise = [q["heise"][i] for i in cur.get("tech_heise_idx", []) if i < len(q["heise"])]
    hn = [q["hackernews"][i] for i in cur.get("tech_hn_idx", []) if i < len(q["hackernews"])]
    heise_html = "\n".join(artikel(it, gross=(i == 0), quelle="heise online") for i, it in enumerate(heise))
    hn_html = "\n".join(artikel(it, quelle="Hacker News") for it in hn)
    return f"""
<p class="hinweis">{esc(cur.get("tech_intro", ""))}</p>
{heise_html}
<h3 class="rubrik">Aus dem Hacker-News-Ticker <span class="leise">(englisch)</span></h3>
{hn_html}
"""


def seite_panorama(q, cur, jetzt):
    w = q["wetter"] or {}
    daily = w.get("daily", {})
    tage = []
    for i, iso in enumerate((daily.get("time") or [])[:5]):
        try:
            d = datetime.fromisoformat(iso)
            tag = "Heute" if i == 0 else WOCHENTAGE[d.weekday()]
        except ValueError:
            tag = iso
        zustand, glyph = wetter_text((daily.get("weather_code") or [0] * 9)[i])
        tage.append(f'<tr><td>{esc(tag)}</td><td>{glyph} {esc(zustand)}</td>'
                    f'<td class="num">{dezahl(daily["temperature_2m_max"][i], 0)}° / {dezahl(daily["temperature_2m_min"][i], 0)}°</td>'
                    f'<td class="num">{esc(daily["precipitation_probability_max"][i])} %</td></tr>')
    sonne = ""
    if daily.get("sunrise"):
        auf = datetime.fromisoformat(daily["sunrise"][0]).strftime("%H:%M")
        unter = datetime.fromisoformat(daily["sunset"][0]).strftime("%H:%M")
        sonne = f'<p class="meta">Sonnenaufgang {auf} Uhr · Sonnenuntergang {unter} Uhr</p>'

    report = q["fetch_report"] or {}
    ok, fail = report.get("ok", "?"), report.get("failed", "?")
    stand = report.get("generated", "")
    try:
        stand = datetime.fromisoformat(stand).strftime("%H:%M")
    except (ValueError, TypeError):
        pass

    quellen = ("tagesschau.de · Nordstadtblogger · Rundblick Unna · Ruhr Nachrichten · "
               "WDR · kicker · sportschau.de · OpenLigaDB · Open-Meteo · Yahoo Finance · "
               "Frankfurter (EZB) · gold-api.com · CoinGecko · heise online · Hacker News · "
               "Horoscope-App-API")

    return f"""
<div class="horoskop">
  <h3 class="rubrik">Horoskop · Fische <span class="fische">♓</span></h3>
  <p class="horoskop-text">{esc(cur.get("horoskop_de"))}</p>
  <p class="meta">19. Februar bis 20. März · aus dem Englischen übersetzt von der Redaktion</p>
</div>
<hr class="linie">
<h3 class="rubrik">Wetter für Holzwickede, 5 Tage</h3>
<table class="tabelle wetter5">
  <tbody>{"".join(tage)}</tbody>
</table>
{sonne}
<p class="meta">Quelle: Open-Meteo (DWD-Modelldaten)</p>
<hr class="linie">
<div class="impressum">
  <h4>Zu dieser Ausgabe</h4>
  <p>Der Holzwickeder erscheint täglich als private, nicht-kommerzielle Presseschau für genau einen Leser.
  Überschriften und Anrisse werden aus den Originalquellen zitiert und verlinken dorthin; alle Rechte liegen bei den jeweiligen Häusern.</p>
  <p class="meta">Redaktionsschluss {esc(stand)} Uhr · Datenlage: {esc(ok)} von {esc(int(ok) + int(fail) if isinstance(ok, int) else "?")} Quellen lieferbar · gebaut am {esc(jetzt.strftime("%d.%m.%Y um %H:%M"))} Uhr</p>
  <p class="meta">Quellen: {esc(quellen)}</p>
</div>
<p class="schlussmarke">❦</p>
"""


# ------------------------------------------------------------------ Rahmen

CSS = """
:root {
  --papier: #f7f3ea; --tinte: #211d18; --grau: #6f675a; --linie: #d8d0c0;
  --akzent: #a31f24; --plus: #1e6e42; --kachel: #efe9db;
  --kopf-h: 128px;
}
@media (prefers-color-scheme: dark-nie) {
  :root {
    --papier: #171512; --tinte: #e8e2d4; --grau: #9a9184; --linie: #353026;
    --akzent: #d4555a; --plus: #58b183; --kachel: #201d18;
  }
}
:root[data-theme="light"] {
  --papier: #f7f3ea; --tinte: #211d18; --grau: #6f675a; --linie: #d8d0c0;
  --akzent: #a31f24; --plus: #1e6e42; --kachel: #efe9db;
}
:root[data-theme="dark"] {
  --papier: #171512; --tinte: #e8e2d4; --grau: #9a9184; --linie: #353026;
  --akzent: #d4555a; --plus: #58b183; --kachel: #201d18;
}
html, body { height: 100%; }
body {
  margin: 0; background: var(--papier); color: var(--tinte);
  font-family: Charter, Georgia, Cambria, "Times New Roman", serif;
  font-size: 17px; line-height: 1.55;
  overflow: hidden;
}
.blatt { height: 100dvh; display: flex; flex-direction: column; }

/* Kopf */
.kopf { border-bottom: 2px solid var(--tinte); background: var(--papier); }
.masthead { text-align: center; padding: 10px 16px 0; }
.datumzeile {
  font-size: 0.68rem; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--grau); display: flex; justify-content: space-between; gap: 8px;
  border-bottom: 1px solid var(--linie); padding-bottom: 5px;
}
.wortmarke {
  font-family: Fraktur, serif; font-weight: 400; margin: 6px 0 2px;
  font-size: clamp(2.1rem, 9vw, 3.2rem); line-height: 1;
}
.wortmarke .punkt { color: var(--akzent); }
.untertitel {
  font-size: 0.62rem; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--grau); margin-bottom: 8px;
}
.ressorts {
  display: flex; overflow-x: auto; scrollbar-width: none;
  border-top: 1px solid var(--linie); padding: 0 8px;
}
.ressorts::-webkit-scrollbar { display: none; }
.ressorts button {
  appearance: none; background: none; border: 0; cursor: pointer;
  font-family: inherit; font-size: 0.82rem; white-space: nowrap;
  padding: 9px 11px 10px; color: var(--grau); position: relative;
  transition: color 150ms ease, transform 120ms ease;
}
.ressorts button::after {
  content: ""; position: absolute; left: 11px; right: 11px; bottom: 0;
  height: 2px; background: var(--akzent);
  transform: scaleX(0); transform-origin: left center;
  transition: transform 200ms cubic-bezier(0.23, 1, 0.32, 1);
}
.ressorts button.aktiv { color: var(--tinte); font-weight: 700; }
.ressorts button.aktiv::after { transform: scaleX(1); }
.ressorts button:active { transform: scale(0.96); }

/* Blaettern */
.pager {
  flex: 1; display: flex; overflow-x: auto; overflow-y: hidden;
  scroll-snap-type: x mandatory; overscroll-behavior-x: contain;
}
.seite {
  flex: 0 0 100%; min-width: 100%; scroll-snap-align: start; scroll-snap-stop: always;
  overflow-y: auto; padding: 18px 18px 56px; box-sizing: border-box;
  -webkit-overflow-scrolling: touch;
}
.seite-inner { max-width: 640px; margin: 0 auto; }
.seitentitel {
  font-family: "Playfair Display", Georgia, serif; font-weight: 900;
  font-size: 1.5rem; margin: 0 0 2px; letter-spacing: 0.01em;
}
.seitentitel + .seitenlinie {
  border: 0; border-top: 2px solid var(--tinte); margin: 6px 0 18px; position: relative;
}

/* Artikel */
.artikel { padding: 14px 0; border-bottom: 1px solid var(--linie); }
.artikel:last-child { border-bottom: 0; }
.artikel h3 { font-family: "Playfair Display", Georgia, serif; font-weight: 700; font-size: 1.12rem; line-height: 1.25; margin: 2px 0 6px; }
.artikel.gross h3 { font-size: 1.45rem; font-weight: 900; line-height: 1.18; }
.art-link {
  appearance: none; background: none; border: 0; padding: 0; margin: 0; cursor: pointer;
  font: inherit; color: inherit; text-align: left; width: 100%;
  transition: opacity 120ms ease;
}
.art-link:active { opacity: 0.55; }

/* Leseansicht (Artikel bleibt in der Zeitung) */
.leser {
  position: fixed; inset: 0; z-index: 40; background: var(--papier);
  display: flex; flex-direction: column;
  transform: translateX(100%);
  transition: transform 280ms cubic-bezier(0.32, 0.72, 0, 1);
}
.leser.offen { transform: translateX(0); }
.leser-kopf {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; border-bottom: 2px solid var(--tinte); background: var(--papier);
}
.leser-zurueck {
  appearance: none; background: none; border: 0; cursor: pointer;
  font-family: inherit; font-size: 1rem; font-weight: 700; color: var(--akzent);
  padding: 4px 8px 4px 0; transition: transform 120ms ease;
}
.leser-zurueck:active { transform: scale(0.95); }
.leser-marke { font-family: Fraktur, serif; font-size: 1.25rem; }
.leser-scroll { flex: 1; overflow-y: auto; -webkit-overflow-scrolling: touch; }
.leser-inhalt { max-width: 640px; margin: 0 auto; padding: 22px 20px 64px; }
.leser-inhalt h1 {
  font-family: "Playfair Display", Georgia, serif; font-weight: 900;
  font-size: clamp(1.55rem, 6vw, 2.1rem); line-height: 1.14; margin: 2px 0 8px;
}
.leser-inhalt h2 {
  font-family: "Playfair Display", Georgia, serif; font-weight: 700;
  font-size: 1.15rem; line-height: 1.3; margin: 22px 0 6px;
}
.leser-inhalt .textkoerper { margin-top: 14px; }
.leser-inhalt .textkoerper p { margin: 0 0 14px; hyphens: auto; -webkit-hyphens: auto; }
.leser-inhalt .textkoerper > p:first-of-type::first-letter {
  font-family: "Playfair Display", Georgia, serif; font-weight: 900;
  font-size: 3.1em; float: left; line-height: 0.82; padding: 4px 8px 0 0; color: var(--akzent);
}
.leser-inhalt blockquote {
  margin: 16px 0; padding: 2px 0 2px 14px; border-left: 3px solid var(--akzent); font-style: italic;
}
.leser-inhalt .aufzaehlung { margin: 0 0 6px; }
.leser-quelle { margin-top: 20px; font-size: 0.82rem; }
.leser-quelle a { color: var(--grau); }
.kicker {
  font-size: 0.68rem; letter-spacing: 0.12em; text-transform: uppercase;
  color: var(--akzent); font-weight: 700; margin: 0 0 2px;
}
.teaser { margin: 0 0 6px; hyphens: auto; -webkit-hyphens: auto; }
.meta { font-size: 0.72rem; color: var(--grau); margin: 4px 0 0; }
.leise { color: var(--grau); font-weight: 400; }
.hinweis { font-style: italic; color: var(--grau); margin: 0 0 10px; }
.rubrik {
  font-family: "Playfair Display", Georgia, serif; font-weight: 900; font-size: 1.05rem;
  margin: 26px 0 4px; padding-bottom: 4px; border-bottom: 2px solid var(--tinte);
}
.rubrik:first-child { margin-top: 0; }

/* Titelseite */
.aufmacher h2 {
  font-family: "Playfair Display", Georgia, serif; font-weight: 900;
  font-size: clamp(1.7rem, 6.6vw, 2.4rem); line-height: 1.12; margin: 2px 0 10px;
}
.aufmacher figure { margin: 12px 0 4px; }
.aufmacher img { width: 100%; max-width: 100%; display: block; border: 1px solid var(--linie); }
.aufmacher figcaption { font-size: 0.68rem; color: var(--grau); margin-top: 4px; }
.einordnung { font-size: 1.02rem; }
.initial::first-letter {
  font-family: "Playfair Display", Georgia, serif; font-weight: 900;
  font-size: 3.1em; float: left; line-height: 0.82; padding: 4px 8px 0 0; color: var(--akzent);
}
.linie { border: 0; border-top: 1px solid var(--linie); margin: 20px 0; }
.titel-raster { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
@media (max-width: 480px) { .titel-raster { grid-template-columns: 1fr; } }
.wetterkachel, .zahlenkachel { background: var(--kachel); padding: 14px 16px; }
.wetterkachel h4, .zahlenkachel h4, .editorial h4, .inhalt h4, .impressum h4, .kursblock h4 {
  font-size: 0.68rem; letter-spacing: 0.12em; text-transform: uppercase;
  color: var(--grau); margin: 0 0 8px; font-weight: 700;
}
.wetter-gross { font-family: "Playfair Display", Georgia, serif; font-weight: 900; font-size: 2.4rem; margin: 0; line-height: 1.1; }
.wetter-zustand { margin: 0 0 6px; font-style: italic; }
.wetter-detail { font-size: 0.8rem; margin: 0; color: var(--grau); }
.editorial p { margin: 0; hyphens: auto; -webkit-hyphens: auto; }
.inhaltsliste { list-style: none; margin: 0; padding: 0; }
.inhaltsliste li { border-bottom: 1px solid var(--linie); }
.inhaltsliste li:last-child { border-bottom: 0; }
.sprung {
  appearance: none; background: none; border: 0; cursor: pointer; width: 100%;
  text-align: left; font-family: inherit; font-size: 0.92rem; color: var(--tinte);
  padding: 9px 2px; transition: transform 120ms ease;
}
.sprung:active { transform: scale(0.98); }
.inhalt-ressort { font-weight: 700; color: var(--akzent); font-size: 0.72rem; letter-spacing: 0.1em; text-transform: uppercase; margin-right: 6px; }

/* Kurse und Tabellen */
.kursblock { margin: 0 0 18px; }
.kurse { width: 100%; border-collapse: collapse; }
.kurse td { padding: 6px 0; border-bottom: 1px solid var(--linie); font-variant-numeric: tabular-nums; }
.kurse tr:last-child td { border-bottom: 0; }
.kursname { width: 52%; }
.kurswert { text-align: right; font-weight: 700; white-space: nowrap; }
.delta { text-align: right; font-size: 0.8rem; white-space: nowrap; width: 84px; }
.plus { color: var(--plus); }
.minus { color: var(--akzent); }
.tabelle { width: 100%; border-collapse: collapse; font-size: 0.92rem; }
.tabelle th {
  text-align: left; font-size: 0.66rem; text-transform: uppercase; letter-spacing: 0.1em;
  color: var(--grau); padding: 4px 6px; border-bottom: 2px solid var(--tinte);
}
.tabelle td { padding: 6px; border-bottom: 1px solid var(--linie); }
.tabelle .num, .tabelle th:nth-child(n+3) { text-align: right; font-variant-numeric: tabular-nums; }
.platz { color: var(--grau); width: 22px; }
.punkte { font-weight: 700; }
.bvb-zeile td { background: var(--kachel); font-weight: 700; }
.wetter5 td:first-child { font-weight: 700; }

/* Panorama */
.horoskop { background: var(--kachel); padding: 16px 18px; }
.horoskop .rubrik { border-bottom: 0; margin: 0 0 6px; }
.fische { color: var(--akzent); }
.horoskop-text { font-style: italic; font-size: 1.02rem; margin: 0; }
.schlussmarke { text-align: center; color: var(--akzent); font-size: 1.4rem; margin: 30px 0 0; }
.impressum p { font-size: 0.85rem; }

@media (prefers-reduced-motion: reduce) {
  .ressorts button::after { transition: none; }
  .ressorts button, .sprung, .art-link, .leser { transition: none; }
}
"""

JS = """
(function () {
  var pager = document.getElementById('pager');
  var tabs = Array.prototype.slice.call(document.querySelectorAll('.ressorts button'));
  var ruhig = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function geheZu(i) {
    pager.scrollTo({ left: i * pager.clientWidth, behavior: ruhig ? 'auto' : 'smooth' });
  }
  tabs.forEach(function (t, i) { t.addEventListener('click', function () { geheZu(i); }); });
  document.querySelectorAll('.sprung').forEach(function (b) {
    b.addEventListener('click', function () { geheZu(parseInt(b.dataset.ziel, 10)); });
  });

  var raf = null;
  function sync() {
    raf = null;
    var i = Math.round(pager.scrollLeft / pager.clientWidth);
    tabs.forEach(function (t, j) { t.classList.toggle('aktiv', j === i); });
    var aktiv = tabs[i];
    if (aktiv && aktiv.scrollIntoView) {
      aktiv.scrollIntoView({ block: 'nearest', inline: 'center', behavior: ruhig ? 'auto' : 'smooth' });
    }
  }
  pager.addEventListener('scroll', function () { if (!raf) raf = requestAnimationFrame(sync); }, { passive: true });
  sync();

  /* Leseansicht: Artikel oeffnen sich IN der Zeitung */
  var leser = document.getElementById('leser');
  var inhalt = document.getElementById('leser-inhalt');
  var scroller = document.querySelector('.leser-scroll');

  function oeffnen(nr) {
    var t = document.getElementById('art-' + nr);
    if (!t) return;
    inhalt.innerHTML = '';
    inhalt.appendChild(t.content.cloneNode(true));
    scroller.scrollTop = 0;
    leser.hidden = false;
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { leser.classList.add('offen'); });
    });
    try { history.pushState({ leser: true }, ''); } catch (e) {}
  }
  function schliessen() {
    if (leser.hidden) return;
    leser.classList.remove('offen');
    setTimeout(function () { leser.hidden = true; inhalt.innerHTML = ''; }, ruhig ? 0 : 300);
  }
  document.querySelectorAll('.art-link').forEach(function (b) {
    b.addEventListener('click', function () { oeffnen(b.dataset.art); });
  });
  document.getElementById('leser-zurueck').addEventListener('click', function () {
    try {
      if (history.state && history.state.leser) { history.back(); return; }
    } catch (e) {}
    schliessen();
  });
  window.addEventListener('popstate', schliessen);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') schliessen(); });
})();
"""


def baue():
    LESER_TEMPLATES.clear()
    report = json.loads((DATA / "fetch-report.json").read_text(encoding="utf-8")) if (DATA / "fetch-report.json").exists() else None
    if not report or not report.get("ok"):
        raise SystemExit(
            "Abbruch: kein brauchbarer Datenbestand (fetch-report fehlt oder 0 Quellen OK).\n"
            "Erst fetch.py/fetch.ps1 erfolgreich laufen lassen. In Cloud-Sessions:\n"
            "Netzwerk-Allowlist noetig, siehe README.md Abschnitt 'Netzwerk in der Cloud'."
        )
    q = ps.alle_quellen()
    cur = json.loads((DATA / "curated.json").read_text(encoding="utf-8"))
    jetzt = datetime.now()
    datum = datetime.fromisoformat(cur["datum"])
    datumszeile = f"{WOCHENTAGE[datum.weekday()]}, {datum.day}. {MONATE[datum.month - 1]} {datum.year}"

    fonts_css = ""
    if (FONTS / "fraktur.woff2").exists():
        fonts_css += ("@font-face{font-family:Fraktur;src:url(" + b64(FONTS / "fraktur.woff2", "font/woff2")
                      + ") format('woff2');font-display:swap;}")
    for gewicht in ("700", "900"):
        p = FONTS / f"playfair-{gewicht}.woff2"
        if p.exists():
            fonts_css += ("@font-face{font-family:'Playfair Display';font-weight:" + gewicht
                          + ";src:url(" + b64(p, "font/woff2") + ") format('woff2');font-display:swap;}")

    nav = ["Titelseite", "Welt", "Deutschland", "Lokales", "Sport", "Börse", "Tech", "Panorama"]

    # Fuer das Inhaltsverzeichnis: je Ressort die erste Schlagzeile
    def erste(items, ohne=""):
        for it in items:
            if it["titel"] != ohne:
                return it["titel"]
        return ""

    auf_titel = q["welt"][cur["aufmacher"]["idx"]]["titel"]
    nav_titel = [
        ("Welt", erste(q["welt"], auf_titel)),
        ("Deutschland", erste(q["deutschland"])),
        ("Lokales", erste(q["dortmund"])),
        ("Sport", erste(q["bvb"])),
        ("Börse", "DAX, Aktien, ETFs, Gold und Wechselkurse"),
        ("Tech", erste([q["heise"][i] for i in cur.get("tech_heise_idx", [0])])),
        ("Panorama", "Horoskop Fische und das Wetter der Woche"),
    ]

    seiten_html = [
        seite_titel(q, cur, nav_titel),
        seite_welt(q, cur),
        seite_deutschland(q),
        seite_lokales(q),
        seite_sport(q, cur),
        seite_boerse(q),
        seite_tech(q, cur),
        seite_panorama(q, cur, jetzt),
    ]

    seiten = []
    for i, (name, inhalt) in enumerate(zip(nav, seiten_html)):
        kopfzeile = "" if i == 0 else (f'<h2 class="seitentitel">{esc(name)}</h2><hr class="seitenlinie">')
        seiten.append(f'<section class="seite" id="seite-{i}"><div class="seite-inner">{kopfzeile}{inhalt}</div></section>')

    tabs = "".join(f'<button type="button"{" class=" + chr(34) + "aktiv" + chr(34) if i == 0 else ""}>{esc(n)}</button>'
                   for i, n in enumerate(nav))

    seitenzahl = f"Nr. {cur.get('ausgabe_nr', 1)}"
    doc = f"""<title>Der Holzwickeder</title>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>{fonts_css}{CSS}</style>
<div class="blatt" lang="de">
  <header class="kopf">
    <div class="masthead">
      <div class="datumzeile"><span>{esc(datumszeile)}</span><span>{esc(seitenzahl)} · kostenlos, aber unbezahlbar</span></div>
      <h1 class="wortmarke">Der Holzwickeder<span class="punkt">.</span></h1>
      <div class="untertitel">Tägliche Zeitung für Holzwickede, den Kreis Unna und den Rest der Welt</div>
    </div>
    <nav class="ressorts" id="nav" aria-label="Ressorts">{tabs}</nav>
  </header>
  <main class="pager" id="pager">
    {"".join(seiten)}
  </main>
</div>
<div class="leser" id="leser" hidden>
  <div class="leser-kopf">
    <button type="button" class="leser-zurueck" id="leser-zurueck">‹ Zeitung</button>
    <span class="leser-marke">Der Holzwickeder<span class="punkt">.</span></span>
  </div>
  <div class="leser-scroll"><div class="leser-inhalt" id="leser-inhalt"></div></div>
</div>
{"".join(LESER_TEMPLATES)}
<script>{JS}</script>
"""

    ziel = HIER / "zeitung.html"
    ziel.write_text(doc, encoding="utf-8")
    archiv = HIER / "ausgaben" / f"{cur['datum']}.html"
    archiv.write_text(doc, encoding="utf-8")

    kb = len(doc.encode("utf-8")) / 1024
    print(f"OK: zeitung.html geschrieben ({kb:.0f} KB), Archivkopie {archiv.name}")
    if ps.PROBLEME:
        print("PROBLEME beim Parsen:")
        print("\n".join(" - " + p for p in ps.PROBLEME))
    else:
        print("Keine Parse-Probleme.")


if __name__ == "__main__":
    baue()

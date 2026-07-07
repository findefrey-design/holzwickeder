# -*- coding: utf-8 -*-
"""Der Holzwickeder - Parser fuer alle Rohdaten in data/.

Liefert normalisierte Strukturen; wird von peek.py (Kuratierung)
und build.py (Rendern) gemeinsam genutzt.
Jeder Parser faengt Fehler und meldet sie in PROBLEME statt still zu scheitern.
"""
import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

DATA = Path(__file__).parent / "data"
PROBLEME: list[str] = []


def _melde(quelle: str, fehler: Exception) -> None:
    PROBLEME.append(f"{quelle}: {type(fehler).__name__}: {fehler}")


def load_json(name: str):
    try:
        return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 - Sammelstelle, wird sichtbar gemeldet
        _melde(name, e)
        return None


_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str | None) -> str:
    if not text:
        return ""
    text = html.unescape(_TAG_RE.sub(" ", text))
    # Typografische Normalisierung: Geviertstrich -> Halbgeviertstrich (deutscher Satz)
    text = text.replace("—", "–")
    return re.sub(r"\s+", " ", text).strip()


class _TextExtraktor(HTMLParser):
    """Zieht aus beliebigem Artikel-HTML eine saubere Absatzliste.

    Ergebnis: Liste von {"art": "p"|"h2"|"li"|"quote", "text": str}.
    Bilder, Skripte, Links (nur der Linktext bleibt), Embeds usw. fallen weg -
    die Leseansicht der Zeitung ist bewusst reiner Text.
    """
    BLOCK = {"p": "p", "h1": "h2", "h2": "h2", "h3": "h2", "h4": "h2", "li": "li", "blockquote": "quote"}
    IGNORIEREN = {"script", "style", "figure", "figcaption", "iframe", "noscript", "form", "aside", "nav"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.absaetze: list[dict] = []
        self._puffer: list[str] = []
        self._art = "p"
        self._ignoriere = 0

    def _abschliessen(self):
        text = re.sub(r"\s+", " ", "".join(self._puffer)).strip()
        text = text.replace("—", "–")
        if len(text) > 1:
            self.absaetze.append({"art": self._art, "text": text})
        self._puffer = []

    def handle_starttag(self, tag, attrs):
        if tag in self.IGNORIEREN:
            self._ignoriere += 1
        elif tag in self.BLOCK and not self._ignoriere:
            self._abschliessen()
            self._art = self.BLOCK[tag]
        elif tag == "br" and not self._ignoriere:
            self._puffer.append(" ")

    def handle_endtag(self, tag):
        if tag in self.IGNORIEREN:
            self._ignoriere = max(0, self._ignoriere - 1)
        elif tag in self.BLOCK and not self._ignoriere:
            self._abschliessen()
            self._art = "p"

    def handle_data(self, data):
        if not self._ignoriere:
            self._puffer.append(data)


def html_zu_absaetzen(roh: str | None) -> list[dict]:
    if not roh:
        return []
    p = _TextExtraktor()
    try:
        p.feed(roh)
        p._abschliessen()
    except Exception as e:  # noqa: BLE001
        _melde("volltext-parser", e)
        return []
    # WordPress-Fussnoten wie "Der Beitrag ... erschien zuerst auf ..." abschneiden
    out = [a for a in p.absaetze if not a["text"].startswith("Der Beitrag ")]
    return out


def _lade_volltexte() -> dict:
    return load_json("volltexte") or {}


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_feed(name: str, limit: int = 25) -> list[dict]:
    """RSS 2.0, Atom und RDF in eine Liste {titel, teaser, url, datum} normalisieren."""
    path = DATA / f"{name}.xml"
    try:
        root = ET.fromstring(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        _melde(name, e)
        return []
    items = []
    for el in root.iter():
        if _localname(el.tag) not in ("item", "entry"):
            continue
        titel, teaser, url, datum, encoded = "", "", "", "", ""
        for kind in el:
            ln = _localname(kind.tag)
            if ln == "title":
                titel = _clean(kind.text)
            elif ln in ("description", "summary") and not teaser:
                teaser = _clean(kind.text)
            elif ln == "encoded":
                encoded = kind.text or ""
            elif ln == "link":
                url = (kind.get("href") or kind.text or "").strip() or url
            elif ln in ("pubDate", "date", "updated", "published") and not datum:
                datum = (kind.text or "").strip()
        if titel:
            volltext = html_zu_absaetzen(encoded) if len(encoded or "") > 600 else []
            items.append({"titel": titel, "teaser": teaser or _clean(encoded)[:300], "url": url,
                          "datum": datum, "volltext": volltext})
        if len(items) >= limit:
            break
    if not items:
        _melde(name, ValueError("Feed geparst, aber 0 Eintraege gefunden"))
    return items


def tagesschau(name: str, limit: int = 15) -> list[dict]:
    raw = load_json(name)
    if not raw:
        return []
    volltexte = _lade_volltexte()
    items = []
    for n in raw.get("news", []):
        if n.get("type") not in (None, "story"):
            continue
        volltext = []
        for block in volltexte.get(n.get("details") or "", []):
            if block.get("type") == "headline":
                volltext.append({"art": "h2", "text": _clean(block.get("value"))})
            else:
                volltext.extend(html_zu_absaetzen(f"<p>{block.get('value', '')}</p>"))
        items.append({
            "titel": _clean(n.get("title")),
            "topline": _clean(n.get("topline")),
            "teaser": _clean(n.get("firstSentence")),
            "url": n.get("shareURL") or n.get("detailsweb") or "",
            "datum": n.get("date", ""),
            "volltext": volltext,
        })
        if len(items) >= limit:
            break
    return items


def hackernews(limit: int = 20) -> list[dict]:
    raw = load_json("tech_hn") or []
    items = []
    for it in raw[:limit]:
        items.append({
            "titel": _clean(it.get("title")),
            "teaser": "",
            "url": it.get("url") or f"https://news.ycombinator.com/item?id={it.get('id')}",
            "punkte": it.get("score", 0),
            "kommentare": it.get("descendants", 0),
        })
    return items


def boerse() -> list[dict]:
    raw = load_json("boerse") or []
    out = []
    for m in raw:
        preis = m.get("regularMarketPrice")
        prev = m.get("chartPreviousClose") or m.get("previousClose")
        if preis is None:
            continue
        delta = ((preis - prev) / prev * 100) if prev else None
        out.append({
            "symbol": m.get("symbol", ""),
            "name": _clean(m.get("longName") or m.get("shortName") or m.get("symbol", "")),
            "preis": preis,
            "delta_pct": delta,
            "waehrung": m.get("currency", ""),
        })
    return out


def bl_tabelle(limit: int = 18) -> list[dict]:
    raw = load_json("sport_bl_tabelle") or []
    return [{
        "team": t.get("teamName", ""),
        "kurz": t.get("shortName", ""),
        "spiele": t.get("matches", 0),
        "diff": t.get("goalDiff", 0),
        "punkte": t.get("points", 0),
    } for t in raw[:limit]]


def alle_quellen() -> dict:
    """Alles einsammeln - das eine Objekt, aus dem die Zeitung gebaut wird."""
    return {
        "wetter": load_json("wetter"),
        "welt": tagesschau("news_welt"),
        "deutschland": tagesschau("news_de"),
        "wirtschaft_news": tagesschau("news_wirtschaft", limit=10),
        "dortmund": parse_feed("lokal_nordstadtblogger", 12),
        "ruhrnachrichten": parse_feed("lokal_ruhrnachrichten", 12),
        "kreis_unna": parse_feed("lokal_rundblick_unna", 12),
        "hellweger": parse_feed("lokal_hellweger", 12),
        "nrw": parse_feed("lokal_wdr_ticker", 10),
        "sport": parse_feed("sport_kicker", 12),
        "sportschau": parse_feed("sport_sportschau", 10),
        "bvb": parse_feed("sport_bvb_kicker", 12),
        "bl_tabelle": bl_tabelle(),
        "bl_spiele": load_json("sport_bl_spiele"),
        "fx": load_json("fx_kurse"),
        "gold": load_json("gold"),
        "silber": load_json("silber"),
        "krypto": load_json("krypto"),
        "boerse": boerse(),
        "horoskop": load_json("horoskop"),
        "heise": parse_feed("tech_heise", 15),
        "hackernews": hackernews(),
        "fetch_report": load_json("fetch-report"),
    }


def _dt(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%H:%M")
    except (ValueError, TypeError):
        return ""

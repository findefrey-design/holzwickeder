# -*- coding: utf-8 -*-
"""Der Holzwickeder - Daten-Fetcher (Python, stdlib-only).

Fuer Cloud-/Linux-Umgebungen (Claude-App am Handy). Auf dem Firmen-Windows-Rechner
scheitert Python-TLS an der Zertifikats-Interception -> dort fetch.ps1 verwenden.
Erzeugt exakt dieselbe data/-Struktur wie fetch.ps1 inkl. data/fetch-report.json.
"""
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HIER = Path(__file__).parent
DATA = HIER / "data"
DATA.mkdir(exist_ok=True)
CFG = json.loads((HIER / "quellen.json").read_text(encoding="utf-8"))
UA = "Mozilla/5.0 (X11; Linux x86_64) DerHolzwickeder/1.0 (private Leseansicht)"
report = []


def hole(url: str, timeout=25) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def quelle(name: str, url: str, ext: str):
    eintrag = {"name": name, "url": url, "ok": False, "status": None, "bytes": 0, "error": None}
    try:
        daten = hole(url)
        (DATA / f"{name}.{ext}").write_bytes(daten)
        eintrag.update(ok=True, status=200, bytes=len(daten))
    except Exception as e:  # noqa: BLE001 - wird sichtbar gemeldet
        eintrag["error"] = f"{type(e).__name__}: {e}"
    report.append(eintrag)
    print(f"[{'OK  ' if eintrag['ok'] else 'FAIL'}] {name} ({eintrag['bytes']} B)"
          + (f" - {eintrag['error']}" if eintrag["error"] else ""))


def sonderfall(name: str, url_label: str, fn):
    try:
        n = fn()
        report.append({"name": name, "url": url_label, "ok": True, "status": 200, "bytes": n, "error": None})
        print(f"[OK  ] {name} ({n} B)")
    except Exception as e:  # noqa: BLE001
        report.append({"name": name, "url": url_label, "ok": False, "status": None, "bytes": 0,
                       "error": f"{type(e).__name__}: {e}"})
        print(f"[FAIL] {name} - {e}")


def main():
    quelle("wetter", CFG["wetter_url"], "json")
    for q in CFG["quellen"]:
        quelle(q["name"], q["url"], q["ext"])

    # Boerse: Yahoo-Chart-Endpunkt, nur meta-Bloecke
    def boerse():
        metas = []
        for sym in CFG["boerse_symbole"]:
            try:
                enc = urllib.parse.quote(sym)
                j = json.loads(hole(f"https://query1.finance.yahoo.com/v8/finance/chart/{enc}?range=5d&interval=1d", 15))
                metas.append(j["chart"]["result"][0]["meta"])
            except Exception as e:  # noqa: BLE001
                print(f"  boerse: {sym} fehlgeschlagen - {e}")
        out = json.dumps(metas, ensure_ascii=False)
        (DATA / "boerse.json").write_text(out, encoding="utf-8")
        return len(out)
    sonderfall("boerse", "query1.finance.yahoo.com (aggregiert)", boerse)

    # Hacker News Top-Items
    def hn():
        ids = json.loads(hole("https://hacker-news.firebaseio.com/v0/topstories.json"))
        items = []
        for i in ids[: CFG["hn_top"]]:
            try:
                items.append(json.loads(hole(f"https://hacker-news.firebaseio.com/v0/item/{i}.json", 15)))
            except Exception:  # noqa: BLE001
                pass
        out = json.dumps([x for x in items if x], ensure_ascii=False)
        (DATA / "tech_hn.json").write_text(out, encoding="utf-8")
        return len(out)
    sonderfall("tech_hn", "hacker-news.firebaseio.com (aggregiert)", hn)

    # Volltexte: tagesschau-details der obersten Story-Items je Ressort
    def volltexte():
        texte = {}
        for ressort, anzahl in CFG["volltexte"].items():
            pfad = DATA / f"{ressort}.json"
            if not pfad.exists():
                continue
            news = json.loads(pfad.read_text(encoding="utf-8")).get("news", [])
            zaehler = 0
            for n in news:
                if n.get("type") not in (None, "story") or not n.get("details"):
                    continue
                try:
                    d = json.loads(hole(n["details"], 20))
                    inhalt = [{"type": c.get("type"), "value": c.get("value") or (c.get("text") or "")}
                              for c in d.get("content", []) if c.get("type") in ("text", "headline")]
                    if inhalt:
                        texte[n["details"]] = inhalt
                except Exception as e:  # noqa: BLE001
                    print(f"  volltext: {n.get('externalId', '?')} fehlgeschlagen - {e}")
                zaehler += 1
                if zaehler >= anzahl:
                    break
        out = json.dumps(texte, ensure_ascii=False)
        (DATA / "volltexte.json").write_text(out, encoding="utf-8")
        return len(out)
    sonderfall("volltexte", "tagesschau.de details (aggregiert)", volltexte)

    ok = sum(1 for r in report if r["ok"])
    fail = len(report) - ok
    (DATA / "fetch-report.json").write_text(json.dumps({
        "generated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "ok": ok, "failed": fail, "sources": report,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{ok} OK, {fail} FAIL -> fetch-report.json")


if __name__ == "__main__":
    main()

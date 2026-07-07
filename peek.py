# -*- coding: utf-8 -*-
"""Kompakte Schlagzeilen-Uebersicht aller Quellen - Input fuer die Kuratierung."""
import sys

sys.stdout.reconfigure(encoding="utf-8")
import parse_sources as ps

q = ps.alle_quellen()

BLOECKE = [
    ("WELT", "welt", 10), ("DEUTSCHLAND", "deutschland", 10),
    ("WIRTSCHAFT", "wirtschaft_news", 8),
    ("DORTMUND/Nordstadtblogger", "dortmund", 10), ("RUHRNACHRICHTEN", "ruhrnachrichten", 10),
    ("KREIS UNNA/Rundblick", "kreis_unna", 10), ("HELLWEGER", "hellweger", 8), ("NRW/WDR", "nrw", 8),
    ("SPORT/kicker", "sport", 10), ("SPORTSCHAU", "sportschau", 8), ("BVB/kicker", "bvb", 10),
    ("TECH/heise", "heise", 15),
]
for label, key, n in BLOECKE:
    print(f"\n=== {label} ===")
    for i, it in enumerate(q[key][:n]):
        top = f"[{it['topline']}] " if it.get("topline") else ""
        teaser = (it.get("teaser") or "")[:140]
        print(f"{i:2d} {top}{it['titel']}\n     {teaser}")

print("\n=== HACKER NEWS (Top 20) ===")
for i, it in enumerate(q["hackernews"]):
    print(f"{i:2d} ({it['punkte']} P, {it['kommentare']} K) {it['titel']}")

print("\n=== PROBLEME ===")
print("\n".join(ps.PROBLEME) or "keine")

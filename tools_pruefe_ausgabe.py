# -*- coding: utf-8 -*-
"""Tages-Verifikation nach README Punkt 5 (nicht behaupten, pruefen)."""
import html.parser

t = open("zeitung.html", encoding="utf-8").read()

class P(html.parser.HTMLParser):
    fehler = None

p = P()
try:
    p.feed(t)
except Exception as e:  # noqa: BLE001
    p.fehler = str(e)

sektionen = t.count("<section")
emdash = t.count("—")
none_sicht = t.count(">None<")
templates = t.count("<template")
artlinks = t.count('class="art-link"')
volltext_ok = "Spirale am Golf" in t
kb = len(t.encode("utf-8")) // 1024
print(f"Sektionen: {sektionen} (soll 8)")
print(f"Em-Dashes sichtbar: {emdash} (soll 0)")
print(f">None<: {none_sicht} (soll 0)")
print(f"Templates {templates} vs. art-links {artlinks} (sollen gleich sein)")
print(f"Einordnung im Dokument: {volltext_ok}")
print(f"Groesse: {kb} KB (soll 300-600)")
print(f"HTML-Parser: {p.fehler or 'wohlgeformt'}")
ok = (sektionen == 8 and emdash == 0 and none_sicht == 0
      and templates == artlinks and volltext_ok and 300 <= kb <= 600 and not p.fehler)
print("ERGEBNIS:", "BESTANDEN" if ok else "DURCHGEFALLEN")
raise SystemExit(0 if ok else 1)

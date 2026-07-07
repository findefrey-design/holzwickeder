---
description: Baut die heutige Ausgabe der Tageszeitung "Der Holzwickeder" und veröffentlicht sie
---

Baue die heutige Ausgabe der Zeitung „Der Holzwickeder".

Befolge exakt das Tagesprotokoll in `README.md` (erst lesen!):

1. Daten holen: auf Linux/Cloud `python3 fetch.py`, auf Windows `& .\fetch.ps1`.
   Fetch-Report prüfen; Ausfälle sichtbar machen, nie still ignorieren.
2. `python peek.py` lesen (Schlagzeilen-Übersicht als Kuratierungs-Grundlage).
3. `data/curated.json` redaktionell neu schreiben (Aufmacher + Bild nach data/aufmacher.jpg,
   Einordnung, Editorial, 5+5 Tech-Artikel nach Leserprofil, Horoskop übersetzen,
   sport_hinweis, Ausgabennummer +1, heutiges Datum).
4. `python build.py` ausführen; muss „Keine Parse-Probleme." melden.
5. Verifizieren (README Punkt 5) - nicht behaupten, prüfen.
6. `zeitung.html` per Artifact-Tool auf die in CLAUDE.md/README genannte URL
   redeployen, Favicon 📰 und Titel unverändert, Label „Ausgabe Nr. N (Datum)".

Melde am Ende: Ausgabennummer, Aufmacher, Datenlage (X von Y Quellen) und den Link.

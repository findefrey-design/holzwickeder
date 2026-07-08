# Der Holzwickeder - Anweisungen für Claude

Dieses Repository baut eine persönliche Tageszeitung als selbst-enthaltene HTML-Seite.
**Das vollständige Tagesprotokoll steht in `README.md` - zuerst lesen, dann exakt befolgen.**

## Das Wichtigste in Kürze

- Auslöser ist der Befehl `/zeitung` (in `.claude/commands/zeitung.md`).
- **Artifact-URL: immer auf dieselbe URL redeployen, Favicon 📰 beibehalten:**
  `https://claude.ai/code/artifact/a6b00225-e477-4386-a1f3-b73f139cf61c`
- Umgebungswahl für den Daten-Abruf:
  - **Linux/Cloud (Claude-App am Handy): `python3 fetch.py`**
  - Windows-Firmenrechner: `& .\fetch.ps1` (Python-TLS scheitert dort an der
    Zertifikats-Interception; Invoke-WebRequest nutzt den Windows-Speicher)
  - Beide lesen `quellen.json` und erzeugen identische `data/`-Strukturen.
- **Cloud-Sessions: Egress-Allowlist!** Schlagen die Abrufe mit „egress policy"/Blockierung
  fehl, fehlt der Umgebung die Netzwerk-Freigabe. Das kann NUR der User in den
  Umgebungs-Einstellungen lösen (Network access -> Custom/Full); Domain-Liste und
  Klickweg stehen in README.md, Abschnitt „Netzwerk in der Cloud". Dann sauber abbrechen
  und den User genau dorthin verweisen - nicht mit halben Daten bauen.
- Aufmacher-Bild (16x9-960 aus dem tagesschau-`teaserImage`) nach `data/aufmacher.jpg`
  laden: in der Cloud mit Python/urllib, auf Windows mit Invoke-WebRequest.
- Nach `python build.py` MUSS die Verifikation aus README Punkt 5 laufen
  (8 Sektionen, kein `>None<`, 0 Em-Dashes, wohlgeformtes HTML, Templates == art-link-Buttons).
- Nichts committen, außer der User bittet darum; die Zeitung selbst (zeitung.html, data/,
  ausgaben/) ist bewusst gitignored und lebt nur im Artifact.

## Stil (nicht verhandelbar)

Deutsch, Anführungszeichen „so", keine Gedankenstriche (—) in selbst geschriebenen Texten,
ein Akzent (Zeitungsrot), Wortmarke „Der Holzwickeder." in Fraktur mit rotem Punkt.
Eigene Texte der Redaktion: Aufmacher-Einordnung, Editorial, Horoskop-Übersetzung,
Tech-Intro. Alles andere sind Zitate der Quellen mit Verweis (private, nicht-kommerzielle
Presseschau für genau einen Leser; Volltexte nur aus Quellen, die sie selbst per API/Feed
bereitstellen: tagesschau-details, Nordstadtblogger, Rundblick Unna).

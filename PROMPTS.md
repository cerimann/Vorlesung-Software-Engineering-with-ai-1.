# KI-Tagebuch: Prompt-Protokoll

**Werkzeug:** Claude Code (VS-Code-Erweiterung), Modell Claude Opus 5.5
**Eingesetzt für:** alle Teile, also Datenbeschaffung, Plot, Meilensteine, Tests und Dokumentation

---

## Prompt 1 – 2026-10-05

```text
https://l3gj0n.github.io/ai_supported_software_development_hs_aalen/de/exercises/01-stack-overflow-challenge/
bitte löse die aufgabe auf dieser website benutze alle plugins/skills und mcps die du brauchst
oder du kannst auch gerne neue nehmen wenn du welche brauchst

https://l3gj0n.github.io/ai_supported_software_development_hs_aalen/ai_milestones/version_2/
```

**Was die KI daraufhin selbstständig gemacht hat:**

1. Beide Seiten geladen (WebFetch und PowerShell). Die WebFetch-Zusammenfassung war zu grob,
   deshalb wurde der HTML-Rohtext extrahiert, um den vollständigen Aufgabentext zu erhalten.
2. Festgestellt, dass `python` nur der Platzhalter aus dem Microsoft Store ist. Stattdessen wurde
   das bereits vorhandene `uv` mit Python 3.14 verwendet.
3. Datenquelle gesucht und getestet: Die Stack Exchange API (`/2.3/questions?filter=total`)
   liefert die Fragenanzahl für einen beliebigen Zeitraum, ohne API-Key und ohne Login.
   Erste Probe: Januar 2009 = 15 823 Fragen.
4. `v1.py` geschrieben (Abruf mit CSV-Cache, gleitender Durchschnitt, Plot) und dazu
   `test_v1.py` mit 8 Offline-Tests (die API wird gemockt).
5. 197 Monate abgerufen (2008-08 bis 2024-12), Plot erzeugt und **das Bild selbst angesehen**.
   Dabei sind drei Layout-Fehler aufgefallen und behoben worden:
   - Die Beschriftung des Höchststands lag auf der Legende. Die Legende wurde in den freien
     Bereich unten in der Mitte verschoben.
   - Der Monatsname war englisch (`Mar 2014`), weil `%b` von der Locale abhängt. Jetzt werden
     deutsche Monatsnamen fest vorgegeben.
   - Der Text „keine Daten“ wurde am rechten Rand abgeschnitten. Die Information steht jetzt als
     Eintrag in der Legende.

---

<!-- Weitere Prompts hier anhängen: Datum, Prompt im Wortlaut, Ergebnis, was nicht geklappt hat. -->

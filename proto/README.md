# Rohentwurf – lokale Sichtung

Erster Prototyp ohne Vercel und Supabase: Ein Veo-Video wird auf deinem PC analysiert, die Szenen werden als Clips geschnitten und im Browser zum Durchswipen angezeigt.

| Schritt | Läuft | Kosten |
| --- | --- | --- |
| Proxy-Video und Tonspur (ffmpeg) | lokal | – |
| Pfiff-Erkennung über den Ton | lokal, nur CPU | – |
| Bewegung im Bild (Spiel unterbrochen oder fortgesetzt) | lokal, nur CPU, ca. 2 min pro Spiel | – |
| Kandidaten ohne Pfiff (Gemini sieht das ganze Spiel) | online, optional | ca. 1 $ pro Spiel (Flash-Lite ca. 0,40 $) |
| Bewertungsvorschlag pro Szene (Claude) | online, optional | ca. 1–2 $ pro Spiel |
| Swipe-Sichtung | lokal im Browser | – |

Ohne API-Keys läuft alles bis auf die beiden optionalen Schritte: Du bekommst dann alle gepfiffenen Szenen ohne KI-Vorschlag.

## Einrichtung (Windows, einmalig)

```powershell
winget install Python.Python.3.12
winget install Gyan.FFmpeg
# neues Terminal öffnen, dann im Projektordner:
cd proto
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Optional den KI-Zugang in `.env` im Projektordner eintragen (Vorlage `.env.example`):
- **Empfohlen: `OPENROUTER_API_KEY`** – ein Key für beides. Standardmodelle: `google/gemini-3.8-flash` für die Suche, `anthropic/claude-haiku-5.5` für Vorschläge, `anthropic/claude-sonnet-5.5` bei unsicheren Szenen. Anpassbar über `SCAN_MODEL`, `ASSESS_MODEL`, `ASSESS_MODEL_STRONG`.
- Alternativ direkt: `GEMINI_API_KEY` und `ANTHROPIC_API_KEY` mit `KI_PROVIDER=direct`.

Bei OpenRouter geht das Video als Datei im Aufruf mit (5-Minuten-Abschnitte, 360p, 1 Bild pro Sekunde, Ton). Google bearbeitet solche Aufrufe über Vertex AI. In den Datenschutz-Einstellungen von OpenRouter Anbieter ausschließen, die Daten zum Training verwenden.

## Benutzung (Weboberfläche)

Doppelklick auf **`start.bat`** im Ordner `proto` – oder im Terminal:

```powershell
cd proto
.venv\Scripts\activate
python -m schiri serve --open
```

Der Browser öffnet `http://localhost:8765`. Dort:
1. **Neues Spiel** → Video über *Durchsuchen* wählen (startet in `Videos`, anderer Startordner über `SCHIRI_VIDEO_DIR` in `.env`). Das Datum wird aus dem Dateinamen übernommen, wenn er mit `JJJJ-MM-TT` beginnt.
2. Spiel, Gespann (Schiri Pflicht, Assistenten optional) und Spielfeld eintragen: Großfeld / verkürztes Großfeld / Kleinfeld, Spieler pro Team, gemessene Maße. Mit Platzname werden Spielform und Maße gemerkt und beim nächsten Mal vorausgefüllt.
3. KI-Schritte an- oder abwählen (nur aktiv, wenn ein Key in `.env` steht), **Analyse starten**.
4. Unter **Spiele** läuft der Fortschritt mit. Danach **Sichten**. Fehlende Schritte lassen sich pro Spiel nachholen (*KI-Vorschläge holen*, *Szenen ohne Pfiff suchen*); bei einem Fehler *Erneut starten* – fertige Schritte werden dabei nicht neu gerechnet.

Oben in der Liste nach Schiedsrichter filtern. *Bearbeiten* ändert Spieldaten, Gespann und Feld, ohne neu zu analysieren.

**Abbrechen** auf der Karte stoppt eine laufende oder wartende Analyse. Fertige Schritte und bereits bezahlte KI-Vorschläge bleiben gespeichert, *Fortsetzen* macht dort weiter. Ein KI-Aufruf, der beim Abbrechen gerade unterwegs ist, wird nicht mehr abgewartet, kann bei OpenRouter aber noch berechnet werden.

Die Analyse läuft, solange das Fenster mit dem Server offen ist. Wird es mittendrin geschlossen, steht das Spiel beim nächsten Start auf „Fehler“ und lässt sich mit *Erneut starten* fortsetzen.

Vom Handy im selben WLAN sichten (Windows-Firewall fragt einmal nach): `python -m schiri serve --host 0.0.0.0`, dann `http://<PC-IP>:8765`. Spiele anlegen und Analysen starten geht nur am PC selbst; vom Handy aus kann nur gesichtet und bewertet werden.

## Benutzung (Kommandozeile)

Dasselbe ohne Browser, z. B. für mehrere Spiele am Stück:

```powershell
python -m schiri analyze "D:\Videos\2026-11-01 Heim - Gast.mp4" --date 2026-11-01 --home "FC Heim" --away "SV Gast" --referee "Max Mustermann" --league "C-Junioren Landesklasse" --pitch grossfeld --players 11
```

Spielform und Feld:
- `--pitch grossfeld | verkuerzt | kleinfeld` – Spielform; geht in die KI-Suche und die Bewertungsvorschläge ein
- `--players 11` – Spieler pro Team auf dem Feld (z. B. 11, 9, 7)
- `--pitch-length 100 --pitch-width 64` – gemessene Feldmaße in Metern; werden später für Laufwege und Distanzen gebraucht, deshalb am besten einmal pro Platz ausmessen

Weitere Befehle:
- `--no-gemini` / `--no-assess` – KI-Schritte auslassen
- `--assess-limit 5` – nur 5 Szenen bewerten lassen (Kosten testen); die tatsächlichen Kosten stehen danach in `steps/gemini_scan/result.json` und `steps/assessment/result.json` (`cost_usd`)
- `python -m schiri assess <match-id>` – Bewertungsvorschläge nachträglich holen
- `python -m schiri list` – analysierte Spiele
- `--force` – alles neu rechnen; ohne werden fertige Schritte übersprungen

Ein 80-Minuten-Spiel braucht lokal etwa 10–15 Minuten (vor allem das Proxy-Video), mit Gemini-Suche einige Minuten mehr.

## Sichtung
- **→ / Wischen nach rechts:** KI-Vorschlag übernehmen (ohne Vorschlag: als relevant markieren)
- **← / Wischen nach links:** verwerfen, kein relevanter Vorfall
- **↑ / Wischen nach oben:** eigene Bewertung (Entscheidung, Schiri lag richtig?, Foulart, Strafe, Kommentar)
- **Leertaste** Pause, **,** und **.** Einzelbild, Geschwindigkeit 1× / 0,5× / 0,25×
- Oben zwischen **Selbstbewertung** und **Beobachter** umschalten; beide werden getrennt gespeichert.

## Wo die Daten liegen
`data/matches/<match-id>/` (nicht im Git):
- `scenes.json` – Szenen mit Pfiff-Daten, Gemini-Hinweis und KI-Vorschlag
- `reviews.json` – deine Bewertungen
- `clips/` – Szenen-Clips
- `steps/` – Zwischenergebnisse je Schritt (Proxy-Video, Tonspur, Rohantworten)

Die Clip-Namen folgen dem Zeitfenster der Szene. Wird ein Spiel neu analysiert, bleiben Bewertungen an der richtigen Szene.

## Grenzen des Rohentwurfs
- Kein Schiri-Tracking, keine Laufwege (kommt als nächster Schritt über Colab mit Grafikkarte).
- Gemini sieht standardmäßig etwa ein Bild pro Sekunde; kurze Kontakte können fehlen.
- Pfiff-Erkennung ist an einem echten Veo-Jugendspiel eingestellt (laute Kinderrufe im selben Frequenzbereich wie die Pfeife). Sie lernt pro Spiel die Tonhöhe der Schiri-Pfeife; fremde Pfeifen von Nachbarplätzen können trotzdem durchrutschen. Schwellen in `schiri/config.py` (`WhistleParams`).
- Pfiffe, die kurz hintereinander kommen (Doppelpfiff, Pfiff plus Wiederanpfiff), werden zu einer Szene zusammengefasst.
- Bewegung im Bild: Für jeden Pfiff wird geschätzt, ob das Spiel danach ruht (*Spiel unterbrochen*), vorher ruhte und danach läuft (*Spielfortsetzung*, z. B. Anstoß oder Freistoß) oder ob keine Ruhephase zu sehen ist (Vorteil, Halbzeit-/Schlusspfiff oder fremder Pfiff). Das ist nur ein Hinweis: auch zu zufälligen Zeitpunkten ruht das Bild oft. In der Sichtung lassen sich Spielfortsetzungen ausblenden; standardmäßig bleiben sie sichtbar.
- Kein Login, keine Rollenrechte – nur für den eigenen PC und das Heimnetz gedacht.

## Tests
```powershell
python tests\test_whistle.py
```

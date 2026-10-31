# Rohentwurf – lokale Sichtung

Erster Prototyp ohne Vercel und Supabase: Ein Veo-Video wird auf deinem PC analysiert, die Szenen werden als Clips geschnitten und im Browser zum Durchswipen angezeigt.

| Schritt | Läuft | Kosten |
| --- | --- | --- |
| Proxy-Video und Tonspur (ffmpeg) | lokal | – |
| Pfiff-Erkennung über den Ton | lokal, nur CPU | – |
| Kandidaten ohne Pfiff (Gemini sieht das ganze Spiel) | online, optional | ca. 0,25 $ pro Spiel |
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

Optional die API-Keys in `.env` im Projektordner eintragen (Vorlage `.env.example`):
- `GEMINI_API_KEY` – Kandidatensuche (bezahlte API-Stufe verwenden, das ganze Video geht an Google)
- `ANTHROPIC_API_KEY` – Bewertungsvorschläge

## Benutzung

```powershell
cd proto
.venv\Scripts\activate

# 1. Spiel analysieren (Video bleibt, wo es liegt)
python -m schiri analyze "D:\Videos\2026-11-01 Heim - Gast.mp4" --match-id 2026-11-01-heim-gast --date 2026-11-01 --home "FC Heim" --away "SV Gast" --referee "Max Mustermann"

# 2. Sichtung starten, dann http://localhost:8765 öffnen
python -m schiri serve

# Vom Handy im selben WLAN (Windows-Firewall fragt einmal nach)
python -m schiri serve --host 0.0.0.0
```

Weitere Befehle:
- `--no-gemini` / `--no-assess` – KI-Schritte auslassen
- `--assess-limit 5` – nur 5 Szenen bewerten lassen (Kosten testen)
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
- Pfiff-Erkennung ist mit synthetischen Daten getestet. Die Schwellen in `schiri/config.py` (`WhistleParams`) werden an echten Veo-Videos nachjustiert.
- Kein Login, keine Rollenrechte – nur für den eigenen PC gedacht.

## Tests
```powershell
python tests\test_whistle.py
```

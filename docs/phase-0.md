# Phase 0 – Vorbereitung und Testdaten

Gate: Testdatensatz steht, Datenschutzkonzept freigegeben.

## Repository und Konten
- [ ] Git-Repository initialisieren, privates GitHub-Repo anlegen
- [ ] Externe Skills installieren: `scripts/install-skills.ps1`
- [ ] Supabase-Projekt in EU-Region (Frankfurt) anlegen
- [ ] Vercel-Projekt anlegen
- [ ] RunPod-Konto anlegen, EU-Region prüfen
- [ ] Claude Console: Organisation anlegen, ggf. API-Guthaben aus dem Abo verknüpfen
- [ ] Google AI Studio: API-Key für den späteren Gemini-Vergleich

## Datenschutz
- [ ] Einwilligung des Pilot-Schiris (Video, Bewertung, Laufdaten)
- [ ] Regelung zur Nutzung von Spielvideos mit Minderjährigen klären (Verein / Veranstalter)
- [ ] Auftragsverarbeitungsverträge: Vercel, Supabase, RunPod, KI-Anbieter, E-Mail-Dienst
- [ ] Löschfristen festlegen (Originalvideos nach Analyse, Clips, Bewertungen)

## Testdaten
- [ ] 2–3 eigene Veo-Spiele exportieren (Panorama und Follow-Cam)
- [ ] 1–2 fremde Veo-Spiele exportieren (nur Follow-Cam)
- [ ] Ablage in `data/raw/` (nicht im Repo)
- [ ] Mindestens 2 Spiele von Hand annotieren nach `docs/annotation-template.csv`: alle Pfiffe, Fouls (auch nicht gepfiffene), Fahnenzeichen, Schiri-Position stichprobenartig

## Regelwerk und Bausteine
- [ ] DFB-Fußballregeln der aktuellen Saison beschaffen, Nutzungsrechte klären → `docs/regelwerk/`
- [ ] Repos sichten und Lizenzen in `docs/entscheidungen.md` festhalten: roboflow/sports, Ultralytics YOLO, dvermaas/RefereeChallenge, opensportslib, sn-mvfoul
- [ ] Domänenlücke messen: Pfiff-Erkennung und Ereignis-Spotting stichprobenartig auf einem Testspiel laufen lassen

## Danach: Phase 1 – Grundgerüst online
Supabase-Schema mit RLS und Gruppen, Login, Rollen und Zuordnungen, Schiri- und Spielverwaltung, Video-Upload, Worker auf Cloud-GPU mit Job-Queue.
Gate: Admin lädt Nutzer ein, Spiel anlegen, Video hochladen, Job läuft durch.

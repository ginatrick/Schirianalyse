# Phase 0 – Vorbereitung und Testdaten

Gate: Testdatensatz steht, Datenschutzkonzept freigegeben.

## Repository und Konten
- [x] Git-Repository initialisieren (lokal), Remote `ginatrick/Schirianalyse` eingetragen
- [ ] Ersten Push ausführen: `git push -u origin main`
- [x] Externe Skills installieren: `scripts/install-skills.ps1`
- [ ] Supabase-Projekt in EU-Region (Frankfurt) anlegen
- [ ] Vercel-Projekt anlegen
- [ ] RunPod-Konto anlegen, EU-Region prüfen
- [ ] Claude Console: Organisation anlegen, ggf. API-Guthaben aus dem Abo verknüpfen
- [ ] Google AI Studio: API-Key für den späteren Gemini-Vergleich

## Datenschutz
- [ ] Einwilligung des Pilot-Schiris (Video, Bewertung, Laufdaten) – Entwurf: `docs/datenschutz/einwilligung-pilot-schiri.md`
- [ ] Regelung zur Nutzung von Spielvideos mit Minderjährigen klären (Verein / Veranstalter)
- [ ] Auftragsverarbeitungsverträge: Vercel, Supabase, RunPod, KI-Anbieter, E-Mail-Dienst – Stand in `docs/datenschutz/avv-liste.md`
- [ ] Löschfristen festlegen – Vorschlag in `docs/datenschutz/verarbeitungsuebersicht.md`
- [ ] Verantwortlichen klären (Patrick privat, Verein oder Kreis)

## Testdaten
- [ ] 2–3 eigene Veo-Spiele exportieren (Panorama und Follow-Cam)
- [ ] 1–2 fremde Veo-Spiele exportieren (nur Follow-Cam)
- [ ] Ablage in `data/raw/` (nicht im Repo)
- [ ] Mindestens 2 Spiele von Hand annotieren – Anleitung: `docs/annotation-leitfaden.md`

## Regelwerk und Bausteine
- [x] Quelle geklärt: IFAB-Spielregeln 2026/27 (deutsch); Nachdruck nur mit Genehmigung → Start mit eigenen Kurzfassungen (`docs/regelwerk/README.md`)
- [ ] Kurzfassungen Regel 12, 5, 6, 11, 13/14 schreiben
- [ ] Optional: Genehmigung für den Regeltext bei IFAB/DFB anfragen
- [x] Lizenzen geprüft → `docs/lizenzen.md` (RF-DETR statt YOLO, kein AGPL/GPL im Produktiv-Worker)
- [ ] Domänenlücke messen: Pfiff-Erkennung und Ereignis-Spotting stichprobenartig auf einem Testspiel laufen lassen

## Danach: Phase 1 – Grundgerüst online
Supabase-Schema mit RLS und Gruppen, Login, Rollen und Zuordnungen, Schiri- und Spielverwaltung, Video-Upload, Worker auf Cloud-GPU mit Job-Queue.
Gate: Admin lädt Nutzer ein, Spiel anlegen, Video hochladen, Job läuft durch.

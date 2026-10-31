# SchiriAnalyse – Projektkontext

Web-Tool zur Spielanalyse für Schiedsrichter auf Basis von Veo-Videos: findet gepfiffene und nicht gepfiffene Szenen, stellt sie als Swipe-Karten bereit, macht KI-Bewertungsvorschläge mit Regelstelle, verfolgt Schiri und Assistenten (Laufweg, Distanz). Bewertet wird durch Schiri (Selbstbewertung) und Beobachter.

- Vollständiger Plan: `docs/entwicklungsplan.md`
- Getroffene Entscheidungen: `docs/entscheidungen.md`
- Aktuelle Phase und nächste Schritte: `docs/phase-0.md`
- Subagenten und Skills: `AGENTS.md` (Agenten in `.claude/agents/`, Skills in `.claude/skills/`)
- Externe Skills einmalig installieren: `scripts/install-skills.ps1`

## Stand
Planung abgeschlossen. Aktuell: **Phase 0 (Vorbereitung und Testdaten)**, danach Phase 1 (Grundgerüst online).

## Stack
- `apps/web` – Next.js (App Router, TypeScript), Hosting Vercel
- `supabase` – Supabase Cloud, EU-Region: Postgres, Auth, Storage, Row Level Security; Schema nur über Migrationen
- `worker` – Python-Analyse-Worker (PyTorch, ffmpeg), läuft auf Cloud-GPU (RunPod Serverless, EU) bei Bedarf
- KI-Bewertung über Online-API, hinter einer austauschbaren Schnittstelle (Claude vs. Gemini wird in Phase 5 an Testszenen verglichen)

## Konventionen
- Oberfläche und Doku auf Deutsch; Code, Bezeichner, Commit-Messages auf Englisch.
- Der Hauptagent committet nach jedem abgeschlossenen Arbeitspaket. Subagenten committen nie.
- Online-first: keine lokale GPU voraussetzen.
- Jede fachliche Tabelle hat `group_id` und RLS-Policies. Rechte nie nur im Frontend prüfen.
- Rollen: Administrator, Beobachter, Schiedsrichter (eine Person kann mehrere haben). Beobachterbewertungen sind für den Schiri erst nach Freigabe sichtbar.
- KI-Vorschlag, Selbstbewertung und Beobachterbewertung immer getrennt speichern (`assessments.source`).

## Datenschutz und Daten
- Videos zeigen Minderjährige: keine Videos, Clips, Frames oder Personendaten ins Repo. `data/` ist ignoriert.
- Secrets nur in `.env` (nie committen), Vorlage in `.env.example`.
- Keine Videodateien in den Kontext laden; mit Metadaten, Stichproben-Frames oder Auswertungsdateien arbeiten.

## Kosten
Möglichst günstig: GPU nur bei Bedarf, Analyse auf dem Proxy-Video, KI nur für erkannte Szenen, günstiges Modell zuerst, Batch-API nutzen. Zielbudget Pilot rund 40 €/Monat.

## Lizenzen
Ultralytics YOLO (AGPL-3.0) und MVFoul (GPL-3.0) vor Einbindung prüfen; jede Lizenzentscheidung in `docs/entscheidungen.md` festhalten.

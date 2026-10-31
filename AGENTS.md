# Subagenten und Skills

Regeln für alle Subagenten:
- Nie committen; am Ende geänderte Dateien, Tests und offene Punkte melden.
- Nur im eigenen Bereich arbeiten, außer der Hauptagent sagt es ausdrücklich.
- Keine Videos oder Frames aus `data/` in den Kontext laden.
- Code und Bezeichner auf Englisch, UI-Texte auf Deutsch.

## Subagenten (`.claude/agents/`)

| Agent | Ordner | Aufgaben | Skills |
| --- | --- | --- | --- |
| `web-dev` | `apps/web` | Next.js-Oberfläche: Schiri-Profil, Spielansicht, Swipe-Karten, Rollen-UI, Benachrichtigungen (mobil zuerst) | vercel-react-best-practices, web-design-guidelines, webapp-testing, frontend-design |
| `db-dev` | `supabase` | Migrationen, RLS, Trigger (Benachrichtigungen, Job-Queue), Seed-Daten | supabase-migration-rls, supabase-postgres-best-practices |
| `worker-dev` | `worker` | Python-Pipeline von Import bis Bewertungsvorschlag | pipeline-step, veo-video-prep, assessment-provider |
| `eval-analyst` | `docs/eval`, `worker/eval` | Auswertung gegen Handannotation, Modellvergleich, Kosten pro Spiel | eval-against-annotation |

## Skills

Eigene Projekt-Skills (`.claude/skills/`, im Repo):
- `supabase-migration-rls` – Migrationen mit Gruppen, Rollen und RLS
- `pipeline-step` – Vertrag für Worker-Schritte
- `veo-video-prep` – ffmpeg-Rezepte für Veo-Videos
- `assessment-provider` – KI-Bewertungsvorschlag, Ausgabeschema, Claude/Gemini
- `eval-against-annotation` – Auswertung gegen die Handannotation

Externe Skills (einmalig per `scripts/install-skills.ps1` installieren):
- `supabase-postgres-best-practices` (supabase/agent-skills)
- `vercel-react-best-practices`, `web-design-guidelines` (vercel-labs/agent-skills)
- `webapp-testing`, `frontend-design` (anthropics/skills)

Der Hauptagent plant Arbeitspakete, verteilt sie an die Subagenten, prüft das Ergebnis und committet.

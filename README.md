# SchiriAnalyse

Analyse-Tool für Schiedsrichter auf Basis von Veo-Videos. Die KI findet gepfiffene und nicht gepfiffene Szenen, macht Bewertungsvorschläge mit Regelstelle und wertet Laufwege von Schiri und Assistenten aus. Bewertet wird durch den Schiri selbst und durch Beobachter.

Status: Planung abgeschlossen, Phase 0 (Vorbereitung und Testdaten).

## Struktur

| Ordner | Inhalt |
| --- | --- |
| `apps/web` | Web-App (Next.js, Vercel) |
| `supabase` | Datenbank-Migrationen, RLS, Trigger |
| `worker` | Python-Analyse-Worker (Cloud-GPU) |
| `docs` | Plan, Entscheidungen, Phasen-Checklisten, Regelwerk |
| `data` | Lokale Testvideos und Annotationen – nicht im Repository |

## Dokumente
- [Entwicklungsplan](docs/entwicklungsplan.md)
- [Entscheidungen](docs/entscheidungen.md)
- [Phase 0 – nächste Schritte](docs/phase-0.md)
- Online-Version des Plans: https://claude.ai/artifact/LM2rmc9sd2wU9wVfKjA6Fc

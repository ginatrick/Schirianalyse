# Entscheidungen

Stand 31.10.2026. Neue Entscheidungen oben ergänzen.

| Datum | Thema | Entscheidung |
| --- | --- | --- |
| 2026-10-31 | Rohentwurf | Erst lokaler Prototyp in `proto/` ohne Vercel/Supabase: Pfiff-Erkennung lokal, Kandidaten über Gemini (ganzes Spiel), Bewertungsvorschläge über Claude, Swipe-Sichtung im Browser; Tracking später über Colab |
| 2026-10-31 | Lizenzen | Produktiv-Worker ohne AGPL/GPL: RF-DETR (Apache-2.0) statt Ultralytics YOLO, supervision (MIT), SAM 2 (Apache-2.0); YOLO und opensportslib nur offline für Vergleiche (Details: docs/lizenzen.md) |
| 2026-10-31 | Betrieb | Von Anfang an online (Vercel, Supabase Cloud EU, Cloud-GPU), keine lokale Phase |
| 2026-10-31 | KI-Bewertung | Online-Sprachmodell per API hinter austauschbarer Schnittstelle; in Phase 5 Claude (Haiku 5.5 / Sonnet 5.5) gegen Gemini Flash an Testszenen vergleichen |
| 2026-10-31 | Pilot | Zunächst ein Schiri; läuft es stabil, Vorstellung beim Kreislehrwart; spätere Gruppen noch offen |
| 2026-10-31 | Rollen | Administrator (vorerst Patrick), Beobachter, Schiedsrichter; Gruppen-Konzept (`group_id`) von Anfang an |
| 2026-10-31 | Bewertung | Selbstbewertung durch Schiri und Assistenten erlaubt; Beobachterbewertung für den Schiri erst nach Freigabe sichtbar |
| 2026-10-31 | Assistenten | Werden mit verfolgt und bewertet, sofern im Bild |
| 2026-10-31 | Videoquellen | Eigene Aufnahmen mit Panorama, fremde nur Follow-Cam |
| 2026-10-31 | Benachrichtigung | In der App und per E-Mail, pro Anlass abschaltbar; Push später als PWA |
| 2026-10-31 | Budget | Möglichst günstig; Vorschlag rund 40 €/Monat im Pilot, ca. 10 € je weiterem Schiri; nach ersten echten Spielen gegen gemessene Kosten prüfen |

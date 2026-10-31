# Verarbeitungsübersicht (Entwurf)

Angelehnt an ein Verzeichnis von Verarbeitungstätigkeiten (Art. 30 DSGVO). Rechtsgrundlagen sind Vorschläge zur Prüfung.

| Datenkategorie | Betroffene | Zweck | Rechtsgrundlage (Vorschlag) | Speicherdauer (Vorschlag) |
| --- | --- | --- | --- | --- |
| Konto: Name, E-Mail, Rolle | Schiri, Beobachter, Admin | Login, Rechte, Benachrichtigung | Vertrag/Nutzungsverhältnis (Art. 6 Abs. 1 lit. b) | bis Kontolöschung |
| Original-Spielvideo | Schiri, Assistenten, Spieler (auch Minderjährige), Trainer, Zuschauer | Analyse | Einwilligung Schiri (lit. a); für übrige Personen Regelung des aufnehmenden Vereins prüfen | löschen nach erfolgreicher Analyse, spätestens 7 Tage nach Upload |
| Proxy-Video und Szenen-Clips | wie oben | Sichtung und Bewertung | wie oben | bis Saisonende + 3 Monate, früher auf Wunsch |
| Positionsdaten, Laufwege, Distanz | Schiri, Assistenten | Leistungsanalyse | Einwilligung (lit. a) | wie Bewertungen |
| Positionen von Spielern (anonym, ohne Zuordnung) | Spieler | Szenenerkennung | berechtigtes Interesse (lit. f), Datensparsamkeit | nur während der Analyse, nicht dauerhaft gespeichert |
| Bewertungen, Kommentare, KI-Vorschläge | Schiri, Assistenten, Beobachter | Lernen und Rückmeldung | Einwilligung (lit. a) | bis Widerruf oder Kontolöschung des Schiris |
| Benachrichtigungen | alle Nutzer | Information | lit. b | 90 Tage |

## Empfänger / Auftragsverarbeiter
Vercel (Web-App), Supabase (Datenbank, Speicher, Login), RunPod (GPU-Analyse), KI-Anbieter (Anthropic, ggf. Google), E-Mail-Dienst. Stand der Verträge: `avv-liste.md`.

## Technische und organisatorische Maßnahmen (Auswahl)
- Rechte über Row Level Security in der Datenbank, nicht nur in der Oberfläche.
- Private Speicher-Buckets, Zugriff auf Clips nur über kurzlebige signierte Links.
- Verschlüsselte Übertragung (HTTPS), Verschlüsselung ruhender Daten beim Anbieter.
- Löschjobs für Originalvideos und abgelaufene Clips.
- Keine Videos, Frames oder Personendaten im Git-Repository.

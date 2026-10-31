# Schiri-Analyse – Entwicklungsplan

Stand 31.10.2026 · Online-Version: https://claude.ai/artifact/LM2rmc9sd2wU9wVfKjA6Fc

## Ziel und Umfang

Das Tool findet in einem Veo-Spielvideo alle gepfiffenen und alle verdächtigen nicht gepfiffenen Szenen, schneidet sie als Clips und stellt sie zum schnellen Durchswipen bereit. Zu jeder Szene gibt es einen KI-Bewertungsvorschlag mit Regelstelle, den der Bewerter bestätigt oder korrigiert.

- Jedes Spiel ist einem Schiedsrichter und, wenn vorhanden, seinen Assistenten zugeordnet. Pro Person sind alle Einsätze, Szenen und Bewertungen abrufbar.
- Schiri und Assistenten werden im Video verfolgt: Position, Laufweg, Laufdistanz und Abstand zur Szene.
- Bewerten dürfen der Schiri selbst und Beobachter. Rollen und Zuordnungen regeln, wer was sieht und bewerten darf.
- Über fertige Analysen und neue Bewertungen wird benachrichtigt.
- Die KI liefert Vorschläge, keine Urteile. Die Erkennung ist auf hohe Trefferquote ausgelegt; Fehlalarme werden weggeswipt.
- Genauigkeit vor Geschwindigkeit: Ein Spiel darf über Nacht rechnen.
- Das Tool läuft von Anfang an online. Analyse und KI-Bewertung nutzen Cloud-Dienste; lokal muss nichts installiert werden.

Nicht im Umfang: Live-Analyse während des Spiels, Abseitsbewertung mit Linie (eine Kamera reicht dafür nicht) und automatische Schiri-Noten.

## Architektur

Das Tool läuft vollständig online: Web-App, Datenbank, Analyse-Worker und KI-Bewertung sind Cloud-Dienste, die nur über die Supabase-Datenbank miteinander sprechen.

Komponenten:
- **Browser / Handy** – Upload, Swipen, Korrekturen
- **Web-App (Next.js, Vercel)** – Spiele, Schiris, Szenen-Review, Rollen, Zuordnung, Benachrichtigung
- **Supabase (EU)** – Postgres (Daten, Job-Queue), Storage (Videos, Clips), Login, RLS
- **Analyse-Worker (Python, Cloud-GPU)** – holt Jobs aus der Queue, schreibt Szenen und Laufwege zurück. Module:
  - Import und Vorschau (ffmpeg: Proxy-Video, Audio, Frames bei Bedarf)
  - Pfiff-Erkennung (Bandpass + Klassifikator, Basis RefereeChallenge)
  - Tracking und Kalibrierung (RF-DETR + roboflow/sports, Spielfeld-Keypoints → Meter)
  - Schiri und Assistenten (Klick, Trikotfarbe, Re-ID; Laufweg, Distanz, Abstand)
  - Ereignisse und Kandidaten (opensportslib-Spotting; Stürze, Zweikämpfe ohne Pfiff)
  - Bewertungsvorschlag (Sprachmodell + Regelwerk-DB, VARS als zweite Meinung)

Der Worker ist in Python geschrieben, weil alle Bildanalyse-Bausteine auf PyTorch aufsetzen; die App bleibt im gewohnten Stack aus Next.js und Supabase.

- **Web-App auf Vercel, Supabase Cloud in EU-Region:** Datenbank, Speicher und Login; Rollen und Zuordnungen setzt Row Level Security direkt in der Datenbank durch.
- **Analyse-Worker auf Cloud-GPU in der EU:** startet bei Bedarf und schaltet nach dem Job ab; Vercel selbst führt keine GPU-Jobs aus.
- **KI-Bewertung über ein online verfügbares Sprachmodell (API):** mit Auftragsverarbeitungsvertrag, kein eigenes Modell auf eigener Hardware.
- **Job-Queue als Postgres-Tabelle:** keine zusätzliche Infrastruktur; der Worker holt offene Jobs und meldet Fortschritt zurück.
- **Benachrichtigungen:** Datenbank-Trigger erzeugen Einträge, ein E-Mail-Dienst versendet sie, die App zeigt sie an.
- **Videospeicher:** Original einmal ablegen, für die Sichtung nur Proxy-Video und Clips laden.

## Open-Source-Bausteine

Tracking, Ton und Ereigniserkennung können weitgehend übernommen werden; die Foulbewertung muss auf Veo-Material nachtrainiert werden, weil fast alle Foulmodelle mit TV-Bildern aus dem Profifußball trainiert sind.

| Baustein | Einsatz im Tool | Lizenz / Einschränkung |
| --- | --- | --- |
| [roboflow/sports](https://github.com/roboflow/sports) | Erkennung von Spielern, Ball und Schiri; Spielfeld-Keypoints für die Umrechnung in Meter | Lizenz im Repo prüfen; Ballverfolgung und Kalibrierung sind laut Autoren noch Schwachstellen |
| RF-DETR + supervision (Tracker) | Detektor und Tracking (ByteTrack) | Apache-2.0 / MIT; Ultralytics YOLO (AGPL-3.0) nur offline zum Vergleich |
| [Ayan-OP/Soccer-Analytics](https://github.com/Ayan-OP/Soccer-Analytics) | Vorlage für Team-Zuordnung per Trikotfarbe, Kamerabewegung, Geschwindigkeit und Distanz | Lernvorlage, nicht direkt übernehmen |
| [dvermaas/RefereeChallenge](https://github.com/dvermaas/RefereeChallenge) | Startpunkt für Pfiff-Erkennung und Haltungserkennung für Handzeichen | Roboterfußball-Kontext, mit Veo-Ton nachtrainieren |
| [OpenSportsLab soccernetpro / opensportslib](https://github.com/OpenSportsLab/opensportslib) | Ereignis-Spotting (Aus, Einwurf, Freistoß, Tor); X-VARS-Adapter für Foulfragen | Lizenz prüfen; mit TV-Bildern trainiert |
| [SoccerNet/sn-mvfoul](https://github.com/SoccerNet/sn-mvfoul) | Referenz für Foulart- und Schwere-Klassifikation | Trainingsdaten nur mit NDA; Nutzungsbedingungen prüfen |
| [druefena/MVFoul](https://github.com/druefena/MVFoul) | Single-View-Variante, passt zur einen Veo-Perspektive | GPL-3.0: nur als separater Dienst oder intern nutzen |
| [X-VARS-LoRA](https://huggingface.co/OpenSportsLab/OSL-VQA-XFOUL-XVARS-lora) | Zweite Meinung mit Erklärung im Schiri-Stil | Forschungsmodell, Qualität auf Veo offen |
| SAM 2 (Meta) | Schiri per Klick im Bild auswählen und segmentieren | Apache-2.0 |
| ffmpeg | Proxy-Video, Audiospur, Clips schneiden | LGPL/GPL je nach Build |

Zum Beobachten: [SoccerRef-Agents](https://arxiv.org/pdf/2604.23392) (Regelwerk-Wissensdatenbank mit Agenten, Code angekündigt). [Ref-Vision](https://apps.apple.com/ba/app/ref-vision/id6737510556) ist das nächstliegende kommerzielle Produkt (Veo-Plugin, Laufdaten), ohne Foulbewertung.

## Datenmodell

Der Schiedsrichter ist der Einstiegspunkt: Über `referees` → `match_officials` → `matches` sind für „Max Mustermann“ alle Einsätze als Schiri oder Assistent samt Szenen, Bewertungen und Laufdaten abrufbar. Tabellennamen auf Englisch, Oberfläche auf Deutsch.

| Tabelle | Wichtige Felder | Zweck |
| --- | --- | --- |
| `users` | Login (Supabase Auth), Name, E-Mail | Konto jeder Person |
| `user_roles` | `user_id`, Rolle (Administrator, Beobachter, Schiedsrichter) | Rolleneinteilung; eine Person kann mehrere Rollen haben |
| `referees` | Name, Verband/Kreis, `user_id` (verknüpftes Konto), Trikotfarben | Schiri-Profil; die Verknüpfung erlaubt die Selbstbewertung |
| `observer_assignments` | `observer_id`, `referee_id` oder `match_id`, gültig von/bis | Welcher Beobachter welche Schiris oder einzelne Spiele bewertet |
| `matches` | Datum, Heim, Gast, Liga/Altersklasse, Ort | Das Spiel |
| `match_officials` | `match_id`, `referee_id`, Funktion (Schiedsrichter, Assistent 1, Assistent 2) | Gespann pro Spiel; Assistenten-Einsätze erscheinen ebenfalls im Profil |
| `videos` | `match_id`, Datei, Quelle (eigene / fremde Aufnahme), Panorama ja/nein, FPS, Dauer, Kalibrierung | Original und Proxy-Video |
| `jobs` | `video_id`, Schritt, Status, Fortschritt, Fehler | Job-Queue für den Analyse-Worker |
| `scenes` | `match_id`, Start/Ende, Spielminute, Typ (gepfiffen / nicht gepfiffen / Fahnenzeichen), erkannt durch, Konfidenz, Clip | Die Karten zum Durchswipen |
| `assessments` | `scene_id`, Quelle (KI / Schiri / Beobachter), bewerteter Offizieller, Entscheidung, Foulart, Sanktion, Regelstelle, Regelwerk-Version, Kommentar, Bewerter, freigegeben ja/nein | Vorschläge und Bewertungen je Rolle getrennt |
| `official_track` | `match_id`, `referee_id`, Zeit, x/y in Metern, sichtbar ja/nein | Laufwege von Schiri und Assistenten |
| `official_stats` | `match_id`, `referee_id`, Distanz, gemessener Zeitanteil, Ø-Abstand zur Szene | Übersicht pro Spiel und Person |
| `notifications` | Empfänger, Anlass, Bezug (Spiel/Szene), gelesen, versendet per | Benachrichtigungen in der App und per E-Mail |
| `notification_settings` | `user_id`, Anlass, Kanal an/aus | Eigene Einstellungen pro Person |
| `groups` | Name, Typ (z. B. Verein, Kreis, Schiedsrichtergruppe); `group_id` an Spielen, Schiris und Zuordnungen | Trennt spätere Gruppen; im Pilot genau eine |

Row Level Security in Supabase setzt Rollen und Zuordnungen direkt in der Datenbank durch, nicht nur in der Oberfläche. Die getrennte Speicherung von KI-Vorschlag, Selbst- und Beobachterbewertung in `assessments` ist zugleich der Trainingsdatensatz für die Lernschleife.

## Verarbeitungspipeline

Jeder Schritt speichert sein Ergebnis und ist einzeln neu startbar. Wird ein Modell verbessert, laufen nur die nachfolgenden Schritte erneut.

1. **Import:** Video hochladen und Spiel, Gespann sowie Quelle angeben (eigene Aufnahme mit Panorama oder fremde Aufnahme). ffmpeg erzeugt ein Proxy-Video und die Audiospur; das Original bleibt für die Detailansicht.
2. **Ton:** Pfiff-Erkennung über die gesamte Spielzeit, Ergebnis sind Zeitstempel mit Konfidenz. Läuft parallel zu Schritt 3.
3. **Bild:** Spieler, Ball und Schiri pro Frame erkennen und verfolgen; Spielfeld-Kalibrierung rechnet Bildpositionen in Meter um. Das ist der rechenintensivste Schritt.
4. **Spielzustand:** Ball ruht oder Spiel unterbrochen erkennen; Ereignis-Spotting für Freistoß, Einwurf, Abstoß, Ecke, Tor.
5. **Gepfiffene Szenen:** Pfiff plus Unterbrechung plus Fortsetzung ergibt eine gepfiffene Szene. Die Fortsetzung verrät die Art: Freistoß deutet auf Foul, Einwurf auf Aus. Clip-Fenster vor und nach dem Pfiff einstellbar.
6. **Nicht gepfiffene Kandidaten:** Spieler fällt, abrupter Tempoabbruch oder enger Zweikampf zweier Gegner, ohne dass in den folgenden Sekunden ein Pfiff kommt. Schwellen bewusst niedrig für hohe Trefferquote.
7. **Auswertung Schiri und Assistenten:** Laufweg, Distanz und Abstand zu jeder Szene; erhobene Fahnen werden zusätzlich als Szenen erfasst.
8. **Bewertungsvorschlag:** pro Szene (siehe unten).
9. **Abschluss:** Szenen in die Datenbank, Clips in den Speicher, Status „bereit zur Sichtung“ und Benachrichtigung an Schiri und zugeordnete Beobachter.

## Tracking von Schiri und Assistenten

Schiri und Assistenten werden einmal per Klick ausgewählt und danach über Trikotfarbe, Erscheinungsbild und Position verfolgt. Eigene Aufnahmen liefern das Panorama, fremde nur die Follow-Cam; das Tool erkennt das am Videoeintrag und wählt den passenden Weg.

- **Auswahl:** Die App zeigt einige Frames aus den ersten Minuten; der Bewerter klickt Schiri und Assistenten an. Die Funktion kommt aus dem Gespann des Spiels. Alternativ wird die Trikotfarbe vorgegeben.
- **Wiedererkennung:** Farbmodell (Trikot, Hose, Stutzen) plus Erscheinungsmerkmal. Assistenten tragen meist dieselbe Farbe wie der Schiri und werden über ihre Position unterschieden: Jeder bewegt sich entlang einer Seitenlinie.
- **Plausibilitätsregeln:** Ein Torwart in ähnlicher Farbe bleibt meist im Strafraum; Personen außerhalb des Spielfelds außer den Assistenten werden ausgeschlossen. Lücken werden markiert, nicht überbrückt.
- **Korrektur:** Eine Zeitleiste zeigt pro Person, wann sie erkannt war. Falsche Zuordnungen lassen sich abwählen und neu anklicken.
- **Eigene Aufnahmen (Panorama):** Alle drei sind fast durchgehend im Bild; eine Kalibrierung pro Spiel reicht. Laufweg und Distanz sind hier am genauesten.
- **Fremde Aufnahmen (Follow-Cam):** Kalibrierung pro Frame; Schiri und besonders Assistenten sind oft außerhalb des Bildes. Bei zu geringer Abdeckung zeigt das Tool keine Distanz statt einer falschen.
- **Laufweg und Distanz:** Positionen werden geglättet (Kalman-Filter), sonst addiert Bildrauschen Phantom-Meter. Gezählt werden nur sichtbare Abschnitte, der gemessene Zeitanteil wird ausgewiesen.
- **Kennzahlen Schiri:** Gesamtdistanz, Heatmap und Abstand zur Szene im Moment des Pfiffs bzw. der Kandidaten-Szene, direkt auf jeder Swipe-Karte.
- **Kennzahlen Assistenten:** Laufweg entlang der Seitenlinie und, soweit im Bild, die Höhe gegenüber dem vorletzten Verteidiger als Näherung für das Stellungsspiel.
- **Fahnenzeichen:** Eine erhobene Fahne wird per Haltungserkennung als zusätzlicher Szenen-Auslöser erfasst, sofern der Assistent im Bild ist.
- **Optional:** GPX-Dateien von GPS-Uhren zum Abgleich der Videowerte importieren.

## Bewertungsvorschlag mit Regelwerk

Jede Szene bekommt einen Vorschlag aus Entscheidung (Foul / kein Foul / unklar), Foulart, persönlicher Strafe, Regelstelle, Sicherheitsgrad und einer kurzen Begründung.

- **Start:** Ein online verfügbares multimodales Sprachmodell (API) erhält die Szene als Frame-Folge oder Clip (auf den Zweikampf gezoomt), die Szenendaten (Pfiff ja/nein, Fortsetzung, Positionen) und die passenden Regelpassagen. Die Antwort folgt einem festen JSON-Schema.
- **Modellwahl:** Schnittstelle austauschbar; in Phase 5 Claude (Haiku 5.5 für alle Szenen, Sonnet 5.5 für unklare) gegen Gemini Flash (natives Video) auf den Testszenen vergleichen.
- **Regelwerk-Datenbank:** Die DFB-Fußballregeln der aktuellen Saison, nach Regel und Abschnitt zerlegt und per Vektorsuche abrufbar. Jede Bewertung speichert die Regelwerk-Version. Jugend-Durchführungsbestimmungen lassen sich ergänzen. Nutzungsrechte am Regeltext vorher klären.
- **Zweite Meinung (optional):** VARS bzw. X-VARS über opensportslib. Widersprechen sich beide Quellen, wird die Szene als „unklar“ markiert.
- **Gegen den Ankereffekt (optional):** Der KI-Vorschlag wird erst nach der eigenen Einschätzung aufgedeckt.
- **Kosten:** API-Kosten pro Spiel messen; Batch-API nutzen. Anbieter mit EU-Verarbeitung und Auftragsverarbeitungsvertrag wählen.

## Review-Oberfläche

Die Sichtung läuft über Swipe-Karten, mobil zuerst gedacht, am Desktop mit Tastatur. Drei Ebenen führen vom Schiri zur einzelnen Szene.

1. **Schiri-Profil:** Alle Einsätze von z. B. Max Mustermann, als Schiedsrichter wie als Assistent, mit Datum, Partie, Funktion, Sichtungsstatus, Anzahl Szenen und Laufdistanz.
2. **Spielansicht:** Zeitleiste mit Markern (gepfiffen, Kandidat, Fahnenzeichen, bewertet), Heatmap und Laufwege des Gespanns. Filter: nur nicht gepfiffen, nur unklar, nur von mir unbewertet.
3. **Swipe-Karte:** Clip in Schleife mit Zeitlupe, Bild-für-Bild und Zoom; daneben KI-Vorschlag, Regelstelle und Abstand des Schiris.
   1. Rechts: Vorschlag bestätigen.
   2. Links: verwerfen, kein relevanter Vorfall.
   3. Hoch: korrigieren im Kurzformular (Entscheidung, Foulart, Sanktion, Kommentar).
4. **Bewertungen nebeneinander:** KI-Vorschlag, Selbstbewertung des Schiris und Beobachterbewertung stehen auf der Karte nebeneinander, sobald sie sichtbar sein dürfen. Abweichungen sind farbig markiert.

Am Ende steht eine Zusammenfassung pro Spiel, exportierbar als PDF für das Gespräch mit dem Schiri oder Beobachter.

## Rollen, Zuordnung und Benachrichtigungen

Drei Rollen regeln, wer was sieht und bewerten darf; die Zuordnung legt fest, für welche Schiris und Spiele das gilt. Eine Person kann mehrere Rollen haben.

| Rolle | Darf | Sieht |
| --- | --- | --- |
| Administrator | Nutzer einladen, Rollen vergeben, Beobachter zuordnen, Spiele und Videos verwalten | Alles |
| Beobachter | Zugeordnete Spiele hochladen und analysieren lassen, Szenen bewerten, Bewertung freigeben | Spiele seiner zugeordneten Schiris oder Ansetzungen |
| Schiedsrichter | Eigene Spiele hochladen, Selbstbewertung abgeben, Beobachterbewertungen kommentieren | Nur eigene Einsätze (auch als Assistent) und freigegebene Beobachterbewertungen |

- **Zuordnung Beobachter:** dauerhaft zu einem Schiri (z. B. für eine Saison) oder zu einem einzelnen Spiel (Ansetzung).
- **Zuordnung Schiri-Konto:** Das Schiri-Profil wird per E-Mail-Einladung mit einem Nutzerkonto verknüpft.
- **Freigabe:** Der Beobachter bewertet zunächst entwurfsweise und gibt dann frei; erst danach sieht der Schiri die Bewertung.

**Pilotbetrieb:** Zunächst ein Schiri, Administrator ist Patrick. Läuft der Pilot stabil, wird das Tool dem Kreislehrwart vorgestellt. Schiedsrichter und Assistenten geben Selbstbewertungen ab. Jedes Spiel und jede Zuordnung gehört von Anfang an zu einer Gruppe; im Pilot gibt es genau eine.

Benachrichtigt wird in der App und per E-Mail, pro Anlass ein- und ausschaltbar:
- Analyse eines Spiels fertig: an Uploader, Schiri und zugeordneten Beobachter.
- Beobachterbewertung freigegeben: an den Schiri und an Assistenten, deren Szenen bewertet wurden.
- Selbstbewertung abgeschlossen: an den zugeordneten Beobachter.
- Neuer Kommentar zu einer Szene: an alle, die diese Szene bewertet oder kommentiert haben.

Push-Benachrichtigungen aufs Handy kommen später über die App als PWA dazu.

## Lernschleife

Die KI lernt in drei Stufen aus den Korrekturen; die erste wirkt sofort, die dritte erst mit einigen hundert bewerteten Szenen.

1. **Vergleichsfälle:** Ähnliche, bereits bewertete Szenen werden dem Sprachmodell als Beispiele mitgegeben.
2. **Schwellen nachstellen:** Verworfene Kandidaten zeigen, welche Muster Fehlalarme erzeugen; die Erkennung wird darauf justiert.
3. **Nachtrainieren:** Pfiff-Klassifikator mit eigenen Veo-Tonbeispielen; Foulmodell nach dem Single-View-VARS-Ansatz auf Veo-Material.

Für das Training zählen freigegebene Beobachterbewertungen stärker als Selbstbewertungen. Weichen beide voneinander ab, gilt die Szene als strittig und wird nicht automatisch übernommen. Der Testdatensatz aus Phase 0 wird nie zum Training genutzt und misst jede neue Version.

## Phasen und Meilensteine

Nach Phase 2 gibt es ein online nutzbares Werkzeug: alle Pfiffe als Swipe-Karten, pro Schiri abrufbar, bewertet von Schiri und Beobachter, mit Benachrichtigung.

| Phase | Inhalt | Gate |
| --- | --- | --- |
| 0 Vorbereitung und Testdaten | Eigene und fremde Veo-Spiele exportieren, Datenschutzkonzept und Cloud-Anbieter (EU) klären; Testspiele von Hand annotieren | Testdatensatz steht, Datenschutzkonzept freigegeben |
| 1 Grundgerüst online | Vercel und Supabase Cloud (EU), Login, Rollen, Zuordnungen, Schiri- und Spielverwaltung; Video-Upload, Worker auf Cloud-GPU mit Job-Queue | Admin lädt Nutzer ein, Spiel anlegen, Video hochladen, Job läuft durch |
| 2 Gepfiffene Szenen und Review (erste nutzbare Version) | Pfiff-Erkennung, Spielunterbrechung, Clip-Schnitt, Swipe-Oberfläche; Bewertung durch Schiri und Beobachter, Freigabe, Benachrichtigung | Pfiffe der Testspiele gefunden, Schiri erhält freigegebene Bewertung |
| 3 Tracking von Schiri und Assistenten | Auswahl per Klick, Wiedererkennung, Kalibrierung für Panorama und Follow-Cam; Laufweg, Distanz, Heatmap, Abstand, Fahnenzeichen | Zuordnung und Distanz gegen Handannotation bzw. GPS plausibel |
| 4 Nicht gepfiffene Szenen | Kandidaten aus Tracking und Ereignis-Spotting, Schwellen auf hohe Trefferquote; verworfene Karten justieren die Schwellen | Annotierte Fouls der Testspiele tauchen als Kandidaten auf |
| 5 Bewertungsvorschlag und Lernschleife | Online-Sprachmodell mit Regelwerk-Datenbank (Claude vs. Gemini), optional VARS; Beobachterbewertungen als Vergleichsfälle | Jede Szene hat Vorschlag, Regelstelle und Sicherheitsgrad |
| 6 Ausbau | Weitere Vereine und Beobachter, Auswertungen über eine Saison, PDF-Export; Lizenzen für Fremdnutzung, Kostenüberwachung, Push | Betrieb mit mehreren Schiris und Beobachtern stabil |

Jedes Gate wird gegen die Handannotation aus Phase 0 geprüft. Termine folgen, sobald Budget und verfügbare Zeit klar sind.

## Kosten (Schätzung Pilot: 1 Schiri, 4 Spiele/Monat)

| Posten | pro Monat |
| --- | --- |
| Supabase Pro | 25 $ fix |
| Vercel Hobby | 0 $ (Pro 20 $, sobald offiziell genutzt) |
| GPU-Analyse (4 × ca. 2 h, RunPod Serverless 16 GB) | ca. 5 $ |
| KI-Bewertung (4 × ca. 80 Szenen, Haiku + Sonnet, Batch) | ca. 1–2 $ (mit Max-Abo über API-Guthaben gedeckt) |
| E-Mail | 0 $ |

Budgetvorschlag: rund 40 €/Monat im Pilot, ca. 10 € je weiterem Schiri; in der Entwicklungsphase eher 50–60 €.

## Risiken und offene Fragen

Weil das Tool von Anfang an online läuft, muss der Datenschutz vor Phase 1 geklärt sein. Der zweite große Hebel ist die schwächere Analyse fremder Aufnahmen ohne Panorama.

- **Datenschutz:** Videos zeigen Minderjährige, bewertet werden identifizierbare Personen, alle Daten liegen in der Cloud. Nötig: Einwilligungen bzw. Vereinsregelung, EU-Hosting, Auftragsverarbeitungsverträge (Vercel, Supabase, GPU- und KI-Anbieter), Löschfristen.
- **Fremde Aufnahmen:** Ohne Panorama sind Schiri und vor allem Assistenten oft nicht im Bild; Laufdaten bleiben dort lückenhaft.
- **Domänenlücke:** Foul- und Spotting-Modelle kennen TV-Bilder, nicht Veo; Qualität in Phase 0 messen.
- **Lizenzen:** gelöst durch RF-DETR statt YOLO; AGPL/GPL-Bausteine (YOLO, opensportslib, MVFoul) und SoccerNet-Daten (NDA) nur offline (siehe `docs/lizenzen.md`).
- **Laufende Kosten:** GPU nur bei Bedarf, Analyse auf dem Proxy-Video, KI nur für erkannte Szenen, günstiges Modell zuerst.
- **Bewertungskonflikte:** Selbst- und Beobachterbewertung können sich widersprechen; Sichtbarkeit und Freigabe brauchen klare Regeln.
- **Störgeräusche und Verwechslungen:** Pfiffe vom Nachbarplatz, Zuschauerpfiffe, Wind; Torwart oder Betreuer in Schiri-Farbe.

Offen:
- [ ] Konkretes Monatsbudget nach Messung der ersten echten Spiele festlegen.
- [ ] Nach dem Pilot: Vorstellung beim Kreislehrwart; welche Gruppen danach dazukommen.

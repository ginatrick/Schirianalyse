# Leitfaden für die Handannotation (Phase 0)

Die Handannotation ist der Maßstab für alle späteren Messungen. Sie wird nie zum Training verwendet.

## Umfang
- Mindestens **2 Spiele** komplett: 1 eigene Aufnahme mit Panorama, 1 fremde Aufnahme (Follow-Cam).
- Pro Spiel ca. 1,5–2,5 Stunden Arbeit. Tipp: in 1,5-facher Geschwindigkeit schauen, bei jedem Pfiff anhalten.

## Datei
`data/annotations/<match_id>.csv` nach `docs/annotation-template.csv`, eine Zeile pro Ereignis. `match_id` = `JJJJ-MM-TT-heim-gast`.

| Spalte | Inhalt |
| --- | --- |
| `video_time` | Zeit im Video `hh:mm:ss` beim Pfiff bzw. beim Vorfall |
| `game_minute` | Spielminute, wenn erkennbar |
| `event_type` | `whistle` (jeder Pfiff), `foul`, `handball`, `offside`, `out`, `flag` (Fahnenzeichen), `card`, `other` |
| `whistled` | `yes` / `no` – wurde der Vorfall gepfiffen? |
| `official` | `referee`, `ar1`, `ar2` – wer hat entschieden bzw. wäre zuständig |
| `decision` | `foul`, `no_foul`, `unclear` – deine eigene Einschätzung |
| `foul_type` | z. B. `tackle`, `push`, `hold`, `trip`, `charge`, `handball` |
| `sanction` | `none`, `yellow`, `red` |
| `ref_x_m`, `ref_y_m` | optional: Position des Schiris in Metern, nur stichprobenartig |
| `notes` | kurze Notiz, z. B. „Vorteil“, „verdeckt“, „Schiri nicht im Bild“ |

## Regeln
- **Jeden Pfiff** erfassen, auch Anstoß, Aus, Halbzeit. Daran wird die Pfiff-Erkennung gemessen.
- **Nicht gepfiffene Fouls**: alles, was du als Beobachter ansprechen würdest, mit `whistled = no`. Grenzfälle mit `decision = unclear`.
- **Vorteil**: als `foul` mit `whistled = no` und Notiz „Vorteil“.
- **Schiri-Position**: alle 5 Minuten und bei jedem Foul, sofern sichtbar. Meter ab Mittelpunkt: x entlang der Längsachse (Richtung rechtes Tor positiv), y quer (Richtung Kamera-Seite negativ). Grobe Schätzung genügt.
- Keine Spielernamen oder Rückennummern eintragen.

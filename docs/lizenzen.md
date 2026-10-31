# Lizenzen der Bausteine

Geprüft am 31.10.2026 anhand der LICENSE-Dateien der Repositories.

| Baustein | Lizenz | Folge für den Online-Betrieb | Entscheidung |
| --- | --- | --- | --- |
| [roboflow/sports](https://github.com/roboflow/sports) | MIT | frei nutzbar | nutzen (Spielfeld-Keypoints, Hilfsfunktionen) |
| [roboflow/supervision](https://github.com/roboflow/supervision) | MIT | frei nutzbar | nutzen (Tracker ByteTrack, Annotation, Zonen) |
| [roboflow/rf-detr](https://github.com/roboflow/rf-detr) – Größen Nano bis Large, Seg, Keypoint | Apache-2.0 | frei nutzbar, auch kommerziell | **Standard-Detektor** statt YOLO |
| rf-detr Atto/Femto/Pico/XL/2XL (`rfdetr[plus]`) | Roboflow PML 1.0 | Selbsthosting kommerziell nur mit Enterprise | nicht verwenden |
| [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) | AGPL-3.0 | Netzwerknutzung löst Quellcodepflicht für die ganze Anwendung aus, sonst Lizenz kaufen | nur für Offline-Experimente in Phase 0, nicht im Produktiv-Worker |
| [facebookresearch/sam2](https://github.com/facebookresearch/sam2) | Apache-2.0 | frei nutzbar | nutzen (Schiri per Klick auswählen) |
| [dvermaas/RefereeChallenge](https://github.com/dvermaas/RefereeChallenge) | CC BY 4.0 | nutzbar mit Namensnennung | als Vorlage für Pfiff-Erkennung, Namensnennung in `NOTICE` |
| [Ayan-OP/Soccer-Analytics](https://github.com/Ayan-OP/Soccer-Analytics) | MIT | frei nutzbar | nur als Lernvorlage (nutzt selbst YOLO) |
| [OpenSportsLab/opensportslib](https://github.com/OpenSportsLab/opensportslib) | AGPL-3.0 | wie YOLO | nur Offline-Auswertung und Vergleich, nicht im Produktiv-Worker |
| [SoccerNet/sn-mvfoul](https://github.com/SoccerNet/sn-mvfoul) | GPL-3.0, Daten nur mit NDA | Code-Einbindung macht den Worker GPL-pflichtig; Daten nicht frei | nur als Referenz |
| [druefena/MVFoul](https://github.com/druefena/MVFoul) | GPL-3.0 | wie sn-mvfoul | nur als Referenz; eigenes Foulmodell später selbst trainieren |
| ffmpeg | LGPL (GPL je nach Build) | als separates Programm aufrufen, nicht linken | nutzen |

## Folgen für den Plan
- Der Produktiv-Worker bleibt frei von AGPL/GPL-Code: Detektion mit RF-DETR (Apache-2.0), Tracking mit supervision (MIT), Auswahl mit SAM 2 (Apache-2.0).
- Ultralytics YOLO und opensportslib dürfen in Phase 0 für Vergleichsmessungen verwendet werden, landen aber nicht im ausgelieferten Worker.
- Ändert sich das (z. B. Projekt wird selbst Open Source unter AGPL), Entscheidung in `docs/entscheidungen.md` neu treffen.

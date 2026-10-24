# Architektur

Stand 0.2: `ai/models.py` verwaltet den expliziten, hashgeprüften Download;
`ai/separation.py` startet/überwacht einen abbrechbaren Kindprozess und übernimmt
Ergebnisse gemeinsam; `ai/worker.py` führt die echte CPU-Modellrechnung mit
diskbasierten Akkumulatoren aus. Keine Netzwerkfunktion im Rechenprozess.
Das Projektformat bleibt bei Version 1; erzeugte Spuren sind normale Audioassets.
Der Windows-Build bündelt die CPU-Laufzeit, der Assistent lädt nur Modellgewichte.
Gesangstrennung ist damit implementiert; Windows-Abnahme und die übrigen
folgenden Ausbaustufen bleiben offen. Die nachstehende Beschreibung dokumentiert
die weiterhin verwendete Grundlage aus Version 0.1.

Klangwerk 0.1 ist die erste überprüfbare Basis nach den Schritten 1–3.
KI wird erst nach Abnahme der Audio-Grundlage integriert.

| Modul | Verantwortung |
| --- | --- |
| `model.py` | Projekt/Spuren/Clips, framegenaue Positionen, Metadaten-Undo/Redo |
| `audio/assets.py` | Lokaler Import, hochwertige rationale Abtastratenkonvertierung, SSD-Memmap und Peak-Übersichten |
| `audio/mixer.py` | Identische blockweise Mischung für Wiedergabe und Export |
| `audio/engine.py` | PortAudio-Ein-/Ausgabe, separater Aufnahmeschreiber |
| `audio/export.py` | Abbrechbarer 24-Bit-WAV-Export mit zweipassiger Spitzenpegelkontrolle |
| `project.py` | Versioniertes JSON-Manifest, portable Assets, atomarer Manifestwechsel, .bak |
| `ui/` | PySide6, Timeline, Mixer, QThread-Jobs, deutsche Fehlerdialoge |
| `ai/` | Reservierter Bereich für kommende lokale Modelle; noch keine KI-API |
| `hardware.py` | CPU/RAM/freier Speicher, feste CPU-Audiobasis |

Audio: 48 kHz, stereo, float32 im Cache; Monoquellen auf zwei identische Kanäle
abgebildet. Mikrofon: mono, 48 kHz Float-WAV, keine Beimischung des Ausgangs.
Quellmaterial bleibt unverändert. Clips referenzieren Quelloffset und Länge in
Frames. Mehrere überlappende Clips werden addiert. Kein Zeitraster erzwingt
Verschiebungen. Geräteseitige Latenz ist noch nicht kalibriert.

Der PortAudio-Callback mischt 1024 Frames, legt Mikrofonblöcke in eine begrenzte
Queue und greift nie auf Qt zu. Ein Schreibthread sichert den Take laufend.
Bei Queue-Überlauf stoppt die Aufnahme mit Fehlermeldung; der bisherige Take
bleibt erhalten. Die Queue puffert maximal etwa 5,5 Sekunden Mono-Audio.
Snapshot-Metadaten trennen laufende Wiedergabe und GUI-Änderungen. Der Python-
Callback ist keine garantierte Echtzeit-Engine; Windows-Aussetzer müssen geprüft
werden. Mixeränderungen sind bislang nicht geglättet und können klicken.

Import, Projekt-I/O, Aufnahmeabschluss und Export laufen in QThreads. Audiocaches
sind schreibgeschützt nach Import. Beim Laden wird vor dem Projektwechsel die
Clip-/Asset-Konsistenz geprüft. Die JSON-Datei wird erst nach den Audiokopien
atomar ersetzt. Leerlauf-Autosicherung alle zwei Minuten; keine vollständige
Transaktions-/Stromausfallgarantie. Cache und rohe Takes werden aus Gründen der
Wiederherstellung noch nicht automatisch gelöscht.

## Nächste Schritte in Reihenfolge

1. Windows-11-Abnahme: Geräte, Aufnahmeversatz, Langzeitwiedergabe, Setup.
2. Demucs/Alternative als separater CPU-Prozess mit Modellassistent, explizitem
   Download, Lizenz-/Hashprüfung, Speicherlimit und Prozessabbruch. Erst fertige
   Ergebnisse als Instrumental-/Referenzspuren übernehmen. Kein Netz im Audiopfad.
3. Effekte als editierbare serialisierte Presets; blockweise DSP mit Zuständen,
   geglätteten Parametern und Latenzausgleich. Export und Playback gleiche Kette.
4. Lokale Tonhöhenanalyse und vorsichtige Korrektur; Original/Variante als eigene
   Assets, Regionsgrenzen mit Überblendungen. Timing/Referenzvergleich getrennt.
5. Referenzklang nur als nachvollziehbare Annäherung analysieren; keine exakten
   unbekannten Hall-/Kompressoreinstellungen behaupten.
6. Automix-Vorschau mit editierbaren Parametern, MP3 über lizenzgeprüftes FFmpeg,
   zusätzliche Projektmigrationen und Stabilitätstests.

Phase 2: später eigenständiger Rekonstruktionsdienst mit Analyseereignissen,
Tempo-/Tonartkarte, Akkorden, MIDI und Renderer-Schnittstelle. Ergebnisse werden
als neue Assets importiert. Kein Wasserzeichenentferner. VST3, MIDI und virtuelle
Instrumente werden in 0.1 nicht implementiert.

# Prüfstand – 24. Oktober 2026

## Version 0.2

**26 Standardtests bestanden**, ein modellabhängiger Test dort übersprungen.
Der zusätzliche Test mit echtem HTDemucs-Modell wurde anschließend aktiviert und
**bestand ebenfalls** (1 Test, etwa 19,5 Sekunden auf der Entwicklungsmaschine).
Damit wurden insgesamt 27 unterschiedliche Tests erfolgreich ausgeführt.

Neu geprüft: Modell-Download mit Hashprüfung, Schutz bestehender Dateien bei
beschädigtem Download, Downloadabbruch, Abbruch eines tatsächlich gestarteten
Unterprozesses, verständliche Prozessfehler, lückenlose gewichtete Fenster für
verschiedene Längen, keine halbe Spurenübernahme bei fehlerhaftem zweitem Stem,
UI-Übernahme mit Originalerhalt/Referenzflag/Solo und atomarem Undo.

Der reale Modelltest führte CPU-Inferenz mit synthetischem Stereo-Audio aus.
Netzwerk-Connect und URL-Downloads waren während dieser Berechnung verboten.
Ausgaben wurden auf Sampleanzahl, Format und endliche Werte geprüft. Außerdem
wurde der gesamte Unterprozess-/Importpfad einmal mit zwei Sekunden Testaudio
ausgeführt (etwa 21 Sekunden). Diese Tests belegen keine Trennungsqualität bei
realen Songs und ersetzen weder Windows- noch Mikrofontests.

Modelltest gezielt aktivieren:
`KLANGWERK_TEST_MODEL=/pfad/955717e8-8726e21a.th python -m pytest -q tests/test_separation.py::test_real_demucs_cpu_inference_without_network`

Die erweiterte Lizenzsammlung und die Python-Kompilierung liefen erfolgreich.

## Historischer Prüfstand Version 0.1

Ergebnis: **14 Tests bestanden**, Python 3.12 / Linux x64. Verwendet wurden die
in `pyproject.toml` festgelegten Audio-/Qt-Versionen. PortAudio 19.7 wurde für
diese Umgebung separat im Arbeitsverzeichnis bereitgestellt. Im Windows-Wheel
von SoundDevice wird die Plattformbibliothek mitgeliefert.

Geprüft:

- WAV-Monoimport und Stereoabbildung; Clip-Start, Quelloffset, Ende und Stille.
- Nicht-destruktives Teilen: vor/nach dem Schnitt identisches Mischsignal.
- Undo/Redo mit Clip-Offsets.
- Solo, Mute, Panorama und Referenzausschluss im Exportpfad.
- Blockweises 44,1→48-kHz-Resampling gegen vollständige Polyphasenkonvertierung.
- Importabbruch entfernt den unvollständigen Cache.
- Projekt-/Asset-Rundlauf und vorherige .bak-Manifestversion.
- Speicherabbruch schützt ein bestehendes Projektmanifest.
- Bereichsexport: Sampleanzahl, 48 kHz, PCM24, Sample-Spitzen unter Vollaussteuerung,
  erwartetes Audiosignal ohne Referenzspur.
- Exportabbruch lässt die bestehende Zieldatei unverändert.
- Tatsächliche MP3-Dekodierung über libsndfile.
- Aufnahme-Callback mit kontrolliertem Gerätestub: Wiedergabedaten werden nicht
  dem Mikrofonkanal beigemischt, Startposition stimmt, Datei enthält Eingangsdaten.
- Fehler beim Geräteöffnen beendet den Aufnahmeschreiber.
- Qt-Timeline rendern, teilen, Undo/Redo; vollständiger asynchroner UI-Ablauf für
  Import, Speichern und Wiederöffnen.

Zusätzlich: Python-Module kompiliert, Lizenzsammlung ausgeführt und Oberfläche
mit echter Qt-Darstellung geprüft. `oberflaeche.png` zeigt synthetische Testsignale
in der tatsächlichen Anwendung, keine KI-Ergebnisse.

Nicht geprüft: physisches Mikrofon, tatsächlicher Lautsprecherausgang, Windows-
Treiber, Aufnahmeversatz, Echtzeitstabilität auf Ryzen 7 7735U, installierter
Windows-Build und Setup.exe. Keine Aussagen über gemessene Klangverbesserung
oder KI-Leistung. Siehe `WINDOWS-ABNAHME.md`.

Wiederholung in dieser Linux-Umgebung:

```sh
LD_LIBRARY_PATH="$PWD/.system-libs/usr/lib/x86_64-linux-gnu" \
LIBRARY_PATH="$PWD/.system-libs/usr/lib/x86_64-linux-gnu" \
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

Auf normal eingerichtetem Linux mit libportaudio2 bzw. unter Windows genügt
`python -m pytest -q` in der eingerichteten Entwicklungsumgebung.

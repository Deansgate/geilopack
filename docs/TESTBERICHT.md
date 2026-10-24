# Prüfstand – 24. Oktober 2026

## Version 0.2.1 – NumPy-/HTDemucs-Regression

**32 Tests unter Windows bestanden, keine Modelltests übersprungen.**
Build: https://github.com/Deansgate/geilopack/actions/runs/40132943494

Zusätzlich erfolgreich: EXE-Starttest, Ausführen des Installers, Erhalt einer
bestehenden Datei im Nutzerdatenordner sowie echtes HTDemucs-Modellladen und
CPU-Inferenz in der installierten EXE. Netzwerkverbindungs- und Downloadaufrufe
waren während des EXE-Modelltests gesperrt. Modell-Laden erfolgte mit
weights_only=True nach SHA-256-Prüfung. Ergebnisse: zwei endliche Stereo-WAVs,
48.000 Frames bei 48 kHz. Die gemessenen Bibliotheksversionen stehen im
beigefügten Modelltest.json; physische Audiogeräte sind weiterhin nicht abgenommen.

Neue Regressionen: Legacy-NumPy-Scalar, scoped Safe-Globals, Hash-Ablehnung vor
Deserialisierung, Zurückweisung unbekannter Pickle-Globals und CPU-Modellladen
mit Kontrolle der torch.load-Argumente. Projektmodell/-verwaltung, AppId,
Installations- und Nutzerdatenpfade wurden mit dem vorherigen Release verglichen
und bleiben unverändert. Details: [Fehlerbehebung 0.2.1](FEHLERBEHEBUNG-0.2.1.md).

## Windows-Build Version 0.2

Am 24.10.2026 lief der Windows-2022-x64-Build erfolgreich durch:
27 Tests bestanden, ein modellabhängiger Test übersprungen.
Zusätzlich startete die tatsächlich gebaute Klangwerk.exe erfolgreich ohne
separate Python-Installation. Geprüft wurden Qt-Timeline, Audioimport,
WAV-Export, PortAudio-Import und CPU-PyTorch-/Demucs-Import.
Der Installer mit SHA-256-Prüfsumme ist als Entwicklungsfassung veröffentlicht:
https://github.com/Deansgate/geilopack/releases/tag/v0.2.0-dev.2.1

Ein Windows-spezifischer Fehler beim Freigeben temporärer Memmaps nach
Importabbruch wurde dabei gefunden und behoben. Neue Regression prüft den
Abbruch nach bereits geschriebenen Audiodaten. Physische Mikrofon-/Ausgabetests
und vollständige Installer-Abnahme auf Zielhardware bleiben offen.

## Vorheriger Linux-Prüfstand Version 0.2

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

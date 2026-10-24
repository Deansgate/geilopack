# Klangwerk – lokales Musikstudio

Lokale Windows-11-DAW in schrittweiser Entwicklung. **Version 0.2 ergänzt echte
CPU-Gesangstrennung mit Demucs HTDemucs**, Modell-Einrichtung und Prozessabbruch.

Implementiert: WAV/MP3-Import, Mehrspur-Wellenformen, synchrones Playback,
Mikrofonaufnahme mit Begleitmusik, mehrere Takes, Clip-Verschieben/-Teilen/
-Kopieren/-Löschen, Undo/Redo, Bereichsmarkierung, Zoom/Scroll, Lautstärke,
Panorama, Mute/Solo, Referenzmarkierung, portable Projekte, Leerlauf-Autosicherung
und WAV-Export von Song/Bereich/Spur mit 48 kHz / 24 Bit.

Keine CUDA-Abhängigkeit, keine Audio-Uploads, keine Cloud-Verarbeitung.
Originaldateien bleiben erhalten. Tonhöhen-/Timingkorrektur, Effekte, Automix,
MP3-Export und Aufnahme-Latenzkalibrierung sind weiterhin geplant.

Die Modell-Einrichtung lädt nach einem ausdrücklichen Klick etwa 84 MB vom
offiziellen Meta-Modellserver. Ein festgelegter SHA-256-Hash wird vor dem Laden
geprüft. Danach läuft die Trennung vollständig offline. Kein Modell ist im
Quellcode-ZIP enthalten. Ergebnisse können Trennungsartefakte enthalten.

## Ausführen für Entwickler

Python 3.12 empfohlen:

```sh
python -m venv .venv
# Windows:
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m klangwerk
# Linux alternativ: .venv/bin/python; zusätzlich Systembibliothek libportaudio2.
```

Tests: `python -m pytest -q` in der aktivierten Umgebung. Qt-Tests laufen mit
`QT_QPA_PLATFORM=offscreen`, ohne physische Audiogeräte. Diese ersetzen weder
Mikrofon- noch Wiedergabetests auf Windows.

Für Entwickler mit KI-Laufzeit zuerst die CPU-Ausgaben installieren, danach die
festgelegten KI-Abhängigkeiten (mit dem Python der Entwicklungsumgebung):

```sh
python -m pip install torch==2.6.0+cpu torchaudio==2.6.0+cpu --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r packaging/requirements-ai.txt
```

Im vorgesehenen Windows-Installer werden diese Bibliotheken mitgeliefert; der
Benutzer benötigt dafür keine Kommandozeile. Die Modelle kommen über den Dialog.

## Dokumentation

- [Bedienung](docs/BEDIENUNG.md)
- [Architektur und nächste Schritte](docs/ARCHITEKTUR.md)
- [Windows-Build und Abnahme](docs/WINDOWS-ABNAHME.md)
- [Lizenzen](THIRD_PARTY.md)
- [Testbericht](docs/TESTBERICHT.md)
- [Lokale Gesangstrennung](docs/GESANGSTRENNUNG.md)

![Oberfläche der Basisversion mit synthetischen Testsignalen; 0.2 ergänzt KI-Schaltflächen](docs/oberflaeche.png)

Windows-Build: `packaging/build-windows.ps1` erzeugt mit PyInstaller und Inno
Setup einen Installer, der kein installiertes Python voraussetzt. Ein getestetes
Setup.exe liegt aus dieser Linux-Umgebung noch nicht vor.

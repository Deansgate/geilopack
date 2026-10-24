# Klangwerk 0.2.1: HTDemucs-Modellladen

## Ursache und Versionsprüfung

Die betroffene Version verwendet NumPy 2.2.4, PyTorch/TorchAudio 2.6.0+cpu,
Demucs 4.0.1 und PyInstaller 6.12.0. Diese Versionen bleiben unverändert.
Der offizielle Checkpoint `955717e8-8726e21a.th` referenziert in seinem Pickle
`numpy.core.multiarray.scalar`, also den alten, für NumPy 1.x typischen Modulpfad.
Die genaue NumPy-Version beim Speichern ist daraus nicht bestimmbar.
NumPy 2.2.4 enthält dafür ein echtes Kompatibilitätsmodul. Der Checkpoint lässt
sich in der normalen Python-Umgebung laden; der Fehler liegt im eingefrorenen
Paket, das den nur aus dem Pickle referenzierten Import nicht enthielt.

## Änderung

- Expliziter Import des unveränderten NumPy-Kompatibilitätsmoduls und zusätzliche
  PyInstaller-Hidden-Imports für `numpy.core.multiarray`/`numpy._core.multiarray`.
- Zentrale Modell-Ladefunktion, festgelegter vollständiger SHA-256-Hash und
  Deserialisierung vom selben geprüften Dateihandle.
- PyTorch `weights_only=True` mit einer festen, eng begrenzten Liste der im
  freigegebenen Checkpoint benötigten Typen: HTDemucs, Fraction, NumPy-Dtype,
  historischer NumPy-Scalar und Float64-Dtype. Die Freigabe gilt nur innerhalb
  des Ladeaufrufs. Unbekannte Globals werden weiterhin zurückgewiesen.
- Keine sys.modules-Aliase, kein Versions-Downgrade, kein ersetzter Unpickler,
  keine Umgebungsvariable zum Abschalten von Sicherheitsprüfungen und kein
  Rückfall auf unbeschränktes Pickle-Laden.

## Regressionstests

Ein Legacy-NumPy-Scalar wird mit dem eingeschränkten Lader gelesen. Ein falscher
Modellhash wird vor Deserialisierung abgelehnt; ein unbekanntes Pickle-Global
wird auch hinter der Hashprüfung zurückgewiesen. Der echte Checkpoint wird
auf CPU geladen; Inferenz erzeugt zwei gleich lange, endliche Audiospuren.

Der Windows-Build lädt das echte Modell als Testvoraussetzung und überspringt
die Modelltests nicht mehr. Nach dem Build wird Setup.exe ausgeführt und die
installierte Klangwerk.exe führt Modellladen und echte CPU-Inferenz aus.
Während dieses EXE-Modelltests sind Netzwerkverbindungs- und Downloadaufrufe
gesperrt. Erst nach erfolgreichem Modelltest wird der Download veröffentlicht.
Die gemessenen Bibliotheksversionen stehen im beigefügten `Modelltest.json`.

## Aktualisieren

Klangwerk schließen und den neuen Installer über dieselbe Installation ausführen.
AppId, Installationspfad, QStandardPaths-Anwendungsname, Projektformat und
Nutzerdaten-/Modellordner bleiben unverändert. Projekte, Einstellungen und ein
bereits vollständig heruntergeladenes Modell müssen nicht gelöscht werden.
Danach Klangwerk normal aus dem Startmenü öffnen und die Trennung erneut starten.

Physische Audiogeräte und die Trennungsqualität bei realen Songs sind durch die
synthetischen Funktionsprüfungen nicht abgenommen.

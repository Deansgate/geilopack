# KLANGWERK 0.3.0 – Testfassung

Neue Funktion: Im Mixer rechts neben jeder Spur „Effekte …“ öffnen. Alternativ
Spur auswählen → Bearbeiten → Effekte der gewählten Spur. Wiedergabe vorher stoppen.

- Gesamtschalter für Originalvergleich; jeder Effekt separat abschaltbar.
- EQ: drei breite Glockenfilter bei 150 Hz, 1,8 kHz und 8 kHz, jeweils ±12 dB.
- Stereo-gekoppelter RMS-Kompressor: Schwelle, Verhältnis und Ausgangspegel;
  fester 10-ms-Detektor und 50-ms-Pegelglättung. Kein Peak-Limiter.
- Algorithmischer Hall mit fester Raumgröße (Schroeder-Netzwerk).
- Delay: 50–1000 ms, Rückkopplung bis 0,6, Effektanteil bis 0,5.
- Anteil 0,15 bedeutet 15 %. Effekte wirken auf die gesamte Spur vor
  Spurlautstärke/Panorama. Wiedergabe und Export verwenden dieselbe Effektkette.
- Nach Übernehmen erneut abspielen. Effekte lassen sich rückgängig machen.
  Die Effekteinstellungen werden im Projekt gespeichert; Originalassets bleiben erhalten.
- Kein KI-Effektmatching und keine automatische Gesangs-/Tonhöhenkorrektur enthalten.

Der gesamte WAV-Export enthält einen begrenzten Ausklang (Hall drei Sekunden,
Delay bis zum berechneten Abklingen unter etwa −100 dB). Der Bereichsexport endet
exakt an der markierten Grenze. Er berechnet den vorherigen Song mit, damit
vorher angeregte Effekte am Bereichsbeginn erhalten bleiben; dieser Vorlauf ist
abbrechbar. Wiedergabe ab einer versetzten Position beginnt mit leerem
Effektspeicher. Für einen vollständigen Vergleich ab Songbeginn starten.

## Testen, ohne bisherige Projekte zu überschreiben

1. Projektdatei und zugehörigen `.klang.audio`-Ordner gemeinsam sichern.
2. Alte Version schließen, Setup.exe der Testfassung installieren. App-ID,
   Nutzerdatenpfad und Modellpfad sind unverändert. Keine Neuinstallation des
   Modells nötig, wenn es schon eingerichtet ist.
3. Altes Projekt öffnen und zuerst **Speichern unter** mit neuem Namen verwenden.
   Format 1 bleibt lesbar; neue Dateien verwenden Format 2 wegen der Effekte.
   Klangwerk 0.2 kann Format 2 nicht öffnen. Beim Überschreiben bleibt die letzte
   Projektdatei zusätzlich als `.bak` erhalten.
4. Eine eigene Gesangsspur auswählen, Effekte einschalten und einzeln ausprobieren.
   Effekte ausschalten und erneut abspielen, um mit dem Original zu vergleichen.
5. Mit Kopfhörern einen kurzen Take aufnehmen; Wiedergabeeffekte dürfen nicht
   digital in den Mikrofontake eingemischt sein. Gerätelatenz ist noch nicht kalibriert.
6. WAV exportieren und außerhalb von Klangwerk anhören. Auf Ausklänge und
   Verzerrungen achten; der Export reduziert bei Bedarf den gesamten Pegel.
7. Speichern, schließen und öffnen: Einstellungen und Positionen vergleichen.

## Aktualisierungen und Grenzen der Sicherheitsprüfung

PyTorch/TorchAudio CPU wurden von 2.6.0 auf ein zusammenpassendes Paar 2.11.0
aktualisiert, Filelock von 3.32.3 auf 4.2.9 und pytest von 8.3.5 auf 9.0.3.
PyInstaller 6.22.3 mit Hooks 2026.9, pip 26.3 und SymPy 1.14.0 werden festgelegt.
NumPy bleibt bei 2.2.4; der echte Legacy-Kompatibilitätsimport bleibt erhalten.
Modell-SHA-256, `weights_only=True`, feste Safe-Globals und CPU-Betrieb bleiben aktiv.
Es werden keine Sicherheitsprüfungen abgeschaltet.

Prüfung am 7. November 2026: `pip-audit` meldet für dieses PyTorch-Paar weiterhin
PYSEC-2025-194 / CVE-2025-3000 (`torch.jit.script`, Fix laut Datenbank ab 2.13.0).
Klangwerk ruft diese API nicht auf und lädt nur den festgelegten Checkpoint nach
Hashprüfung. Dies ersetzt keine Behebung der zugrunde liegenden Bibliothekslücke.
Das aktuell verfügbare passende TorchAudio-CPU-Wheel endet bei 2.11.x; ein
inkompatibles Torch/TorchAudio-Paar wird nicht erzwungen. Ein weiterer Runtime-
Wechsel benötigt gesonderte Integrationsarbeit.

Setuptools 81.0.0 (durch Torch `<82` begrenzt) hat Meldungen zum sdist-Ausschluss
von Unicode-Dateinamen auf macOS und zur alten Windows-Wheel-install-as-egg-
Funktion (PYSEC-2026-3447 und GHSA-xmj3-9gf7-h52w). Der Build verwendet pip statt
install-as-egg und lädt keine beliebigen Nutzerpakete. Setuptools, pip und pytest
werden explizit aus der EXE ausgeschlossen; es gibt keine Paketinstallation in der
Anwendung. Auch diese Maßnahmen sind keine Behebung im Build-Werkzeug selbst.

CPU-Wheel-Kennungen werden von pip-audit nicht direkt gefunden. Deshalb zusätzlich
`torch==2.11.0` und `torchaudio==2.11.0` mit `--no-deps --disable-pip` gegen die
Datenbank geprüft. Dies ist eine Advisory-Abfrage, keine Binärprüfung oder Garantie.

Die Testfassung ist **nicht digital signiert**. Die vorhandene Signaturprüfung
und Veröffentlichungssperre für unsignierte öffentliche Releases bleiben bestehen.
Ein Entwicklungsartefakt ist keine Smart-App-Control-Freigabe. Wenn Windows den
Start blockiert, Schutzfunktionen eingeschaltet lassen und die Meldung melden.
Keine kostenpflichtigen Dienste oder Zertifikate wurden beauftragt.

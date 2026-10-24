# Windows-Build und noch ausstehende Abnahme

In der Linux-Entwicklungsumgebung kann kein verifizierter Windows-Installer
gebaut werden. Die vollständigen Build-Eingaben liegen in `packaging/`.
Die folgenden Schritte betreffen Entwickler; Endbenutzer erhalten Setup.exe.

Voraussetzungen: Windows 11 x64, Python 3.12 x64 und Inno Setup 6.4 oder neuer.
Im Projektordner `powershell -ExecutionPolicy Bypass -File packaging/build-windows.ps1`
ausführen. Das Skript installiert festgelegte Abhängigkeiten in eine eigene
Umgebung, führt Tests aus, sammelt Lizenzen und erstellt zunächst
`dist/Klangwerk/Klangwerk.exe`, danach `dist/installer/Setup.exe`.
Internet wird für Build-Abhängigkeiten benötigt; die fertige Anwendung benötigt
nach der einmaligen Modell-Einrichtung keine Netzwerkverbindung. Das Build-Skript
installiert explizit die CPU-Wheels von PyTorch und bündelt Demucs. Build-Ausgaben sind nicht binär identisch garantiert
(Zeitstempel/Toolchain); Versionen sind festgelegt. Für eine öffentliche Version
zusätzlich Signierung und vollständige Lizenzprüfung vorsehen.

Vor Freigabe auf Zielhardware abhaken:

- Installation mit Standardbenutzer ohne Python, deutsche Assistenten,
  optionale Desktop-Verknüpfung, Startmenü, Start und Deinstallation.
- WAV 44,1/48 kHz, Mono/Stereo und MP3 laden; zehn Minuten Material darstellen.
- Zwei Spuren abspielen, Startposition wechseln, schneiden, verschieben,
  kopieren/löschen und Undo/Redo hörbar prüfen.
- Mikrofon auswählen, 60 Sekunden beim Playback aufnehmen, Take sichern,
  Eingang richtig gepegelt; kein digitales Ausgangssignal in der Aufnahme.
- Aufnahmeversatz mit Klatschen/Loopback messen und dokumentieren; noch keine
  automatische Latenzkompensation behaupten.
- Mehrere Takes, Mute/Solo, Panorama, Referenzpegel und Referenzausschluss prüfen.
- Projekt speichern, Anwendung beenden, Projekt inkl. Audioordner auf anderen
  Pfad kopieren, öffnen, Ergebnisse vergleichen. .bak und Autosave laden.
- WAV Song/Bereich/Spur exportieren; 48 kHz, 24 Bit, Länge und Clipping prüfen.
- Import/Export abbrechen, nicht beschreibbaren Datenträger und fehlende Dateien
  testen. 30 Minuten Aufnahme und längere Wiedergabe auf Aussetzer prüfen.
- Netzwerkverbindung trennen: alle implementierten Funktionen müssen bleiben.
- Modell im Dialog herunterladen, Hashprüfung und Download-Abbruch prüfen.
  Danach offline einen Song trennen: zwei gleich lange Spuren, Original erhalten,
  Referenz nicht im Export. Trennung während aktiver Modellrechnung abbrechen;
  Kindprozess muss enden und die Oberfläche weiter funktionieren.
- DLLs/Notices/LGPL-Austauschbarkeit im tatsächlichen Installer kontrollieren.

Diese Prüfungen wurden hier nicht als Windows-Hardwaretests durchgeführt.

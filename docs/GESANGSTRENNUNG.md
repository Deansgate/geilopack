# Lokale Gesangstrennung in Version 0.2

1. **KI-Modell einrichten** anklicken und den einmaligen Download bestätigen.
   Es werden etwa 84 MB Modellgewichte von `dl.fbaipublicfiles.com` geladen.
   Keine Audiodatei wird übertragen. Nach dem Download wird die vollständige
   SHA-256-Prüfsumme gegen den festgelegten Wert geprüft.
2. Einen Song importieren und den gewünschten Clip in der Timeline auswählen.
3. **Gewählten Clip in Gesang / Instrumental trennen** starten. Der gewählte
   Quellbereich wird verarbeitet; Spurlautstärke und Panorama werden nicht in
   die Quelldaten eingerechnet.
4. Der Fortschritt folgt abgeschlossenen Verarbeitungsfenstern und der
   Ergebnisübernahme. Beim Modellstart und innerhalb eines Fensters kann er
   länger stehen bleiben. **Abbrechen** beendet den separaten Rechenprozess.
5. Nach erfolgreicher Prüfung erscheinen zwei neue, zeitlich passende Spuren:
   **Instrumental** und **Referenzgesang**. Die gesamte Originalspur wird stumm
   geschaltet und bleibt unverändert erhalten. Enthält sie weitere Clips,
   betrifft die Stummschaltung auch diese. Solo wird auf die Ergebnisse übertragen.
6. Referenzgesang startet mit 50 % Spurpegel und wird beim Export ausgeschlossen.
   Er kann separat ein-/ausgeschaltet und geregelt werden. Eigene Takes wie
   gewohnt mit Kopfhörern aufnehmen. Undo nimmt die gesamte Spurenübernahme zurück.

Das Original wird erst nach vollständiger Übernahme beider Ergebnisse
stummgeschaltet. Abbruch oder Fehler verändert das Projekt nicht.

## Technik und Grenzen

- Demucs 4.0.1 / HTDemucs, Modell `955717e8`, CPU-PyTorch 2.6, ohne CUDA.
- Native Modellrate 44,1 kHz; hochwertige Polyphasenkonvertierung vom/zum
  48-kHz-Projekt. Kein verkleinertes/quantisiertes Modell und keine reduzierte
  Ausgaberate als Geschwindigkeitsmodus.
- 20-Sekunden-Fenster mit 50 % Überlappung und gewichteter Überblendung, intern
  Demucs-Standardsegmentierung und ein Shift. Dadurch bleibt der RAM-Bedarf der
  Modellberechnung unabhängig von der Songlänge begrenzt. Bis zu acht CPU-Threads.
- Diskbasierte Akkumulatoren und Float-WAVs; vorab Prüfung auf freien Speicher.
  Instrumental ist die Summe der drei Nicht-Gesangsquellen des Modells.
- Das ist echte Modellinferenz. Wie gut Gesang und Instrumente getrennt werden,
  hängt vom Song ab; Hallreste, verschwundene Instrumentanteile und andere
  Artefakte sind möglich. Kein Qualitätsversprechen für reale Songs.
- CPU-Verarbeitung kann erheblich länger als Echtzeit dauern. Der kurze
  Funktionstest ist kein Leistungsbenchmark für den Ryzen 7 7735U.
- Keine automatische Tonhöhenkorrektur, kein Timingabgleich und kein Automix.
- Windows-Installer, eingefrorener KI-Unterprozess und Zielhardware müssen noch
  unter Windows getestet werden. Das Build-Skript nimmt die CPU-Laufzeit mit auf.

Das Modell wird unter dem lokalen Datenordner `models/` aufbewahrt; Deinstallation
löscht es ebenso wie eigene Projekte nicht automatisch. Das Quellcodepaket
enthält Modellkennung, URL, Größe, Hash und Lizenzhinweise, keine Gewichtsdatei.

# Klangwerk 0.2 – Bedienung

Diese Entwicklungsstufe ergänzt lokale Gesangstrennung. Automatische
Gesangskorrektur und Effekte sind noch nicht vorhanden.
Siehe [Gesangstrennung](GESANGSTRENNUNG.md) für Einrichtung und Verwendung.

1. Nach einem Windows-Build `Setup.exe` öffnen, Ziel bestätigen, optional eine
   Desktop-Verknüpfung wählen. Python ist im fertigen Paket enthalten.
2. Klangwerk im Startmenü öffnen. **Audio importieren** liest WAV/MP3 und stellt
   eine neue Spur in der Timeline dar. Alle Importe beginnen bei Sekunde null.
3. Ausgabe und Mikrofon auswählen. Für Aufnahmen Kopfhörer verwenden und in den
   Windows-Datenschutzeinstellungen Mikrofonzugriff für Desktop-Apps zulassen.
4. Im Lineal die Startposition anklicken. **Aufnahme** spielt vorhandene Spuren
   ab und zeichnet nur das Mikrofon auf. **Stoppen** übernimmt den Take auf eine
   neue Spur. Weitere Aufnahmen erzeugen weitere Takes; ältere Takes bei Bedarf
   stummschalten. Direktes Mithören des Mikrofons und Aufnahmepause fehlen noch.
5. **Wiedergabe** spielt alle hörbaren Spuren synchron. **Stoppen** hält an der
   aktuellen Position. Zum Ändern der Abspielposition erst stoppen. Lautstärke,
   Panorama, Stumm und Solo sind im Mixer veränderbar.
6. Einen Clip anklicken und ziehen, um ihn zu verschieben. Im Lineal eine Position
   setzen und `S` drücken, um den gewählten Clip zu teilen. Teile mit `Entf`
   löschen. `Strg+C` kopiert den Clip; `Strg+V` fügt ihn auf der gewählten Spur an
   der Abspielposition ein. `Strg+Z`/`Strg+Y` machen Änderungen rückgängig/wieder.
7. Mit **+ / −** zoomen und mit den Bildlaufleisten scrollen.
   `Umschalt+Ziehen` markiert einen Exportbereich. `Esc` hebt ihn auf.
8. Als Orientierung importierte Gesangsspur im Mixer **Referenz** markieren.
   Sie ist normal abspielbar, separat regel-/stummschaltbar und wird beim Export
   ausgeschlossen. Der Ausgang wird softwareseitig nie auf die Aufnahme gelegt.
   Akustische Übersprechung ist trotzdem möglich.
9. Mit `Strg+S` speichern. **Die .klang-Datei und ihren .klang.audio-Ordner immer
   gemeinsam verschieben/kopieren.** Die vorherige Manifestversion liegt in
   `.klang.bak`. Originaldateien werden nicht überschrieben.
10. **Datei → Song/Bereich/Spur als WAV exportieren** schreibt 48 kHz / 24 Bit.
    Stumm/Solo, Spurpegel, Panorama und Master gelten auch beim Export.
    Referenzspuren bleiben ausgeschlossen. Falls nötig wird der komplette Export
    leiser gerechnet, damit keine Sample-Spitzen abgeschnitten werden.

Alle zwei Minuten im Leerlauf entsteht eine automatische Sicherung. Über
**Datei → Letzte automatische Sicherung öffnen** lässt sie sich laden.
Sie ist kein Ersatz für regelmäßiges Speichern und externe Sicherungskopien.
Die Deinstallation entfernt eigene Projekte und Aufnahmen nicht.

## Häufige Probleme

- **Kein Ton/keine Aufnahme:** Geräte neu suchen, Systemstandard ausprobieren,
  Windows-Geräte auf 48 kHz einstellen und andere exklusiv zugreifende Apps
  schließen. Kombinierte Ein-/Ausgabe kann bei verschiedenen Treibern scheitern;
  dann dasselbe Audiointerface für beide verwenden.
- **Gesang ist zeitlich versetzt:** Geräte-Latenz ist noch nicht automatisch
  kompensiert. Den Take in der Timeline passend verschieben. Für präzise
  Produktion wird die geplante Latenzkalibrierung benötigt.
- **Knacken/Übersteuerung:** Spur-/Masterpegel senken; laufende Mixeränderungen
  sind noch nicht geglättet. CPU-intensive Programme schließen.
- **Aufnahmefehler:** Der bisherige rohe Take liegt im lokalen Datenordner als
  `cache/aufnahme-*.wav` und kann erneut importiert werden.
- **Speicher wird voll:** Interner Stereo-Cache benötigt etwa 23 MB pro Minute
  und Asset, zusätzlich Projektkopien und Aufnahmen. Cache erst nach vollständiger
  Projektsicherung manuell bereinigen. Er wird in 0.1 nicht automatisch gelöscht.
- **MP3 kann nicht geöffnet werden:** Das Paket benötigt die mitgelieferte
  libsndfile mit MP3-Unterstützung. Alternative: als WAV importieren.

Lokaler Datenordner unter Windows typischerweise:
`%LOCALAPPDATA%\KlangwerkLocal\Klangwerk`.
Die Anwendung enthält keine Upload-, Telemetrie- oder Cloud-Funktion.

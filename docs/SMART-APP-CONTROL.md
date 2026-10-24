# Prüfung der Smart-App-Control-Blockierung

Stand: 24. Oktober 2026. Verglichen wurden die veröffentlichten Originaldateien
aus `v0.2.0-dev.2.1` und `v0.2.1-dev.4.1`. Installer-Prüfsummen wurden vor der
Installation auf einer isolierten Windows-2025-Buildmaschine geprüft.

## Ergebnis des Dateivergleichs

| Merkmal | 0.2.0 | 0.2.1 |
| --- | --- | --- |
| Authenticode von Setup.exe | NotSigned | NotSigned |
| Authenticode von Klangwerk.exe | NotSigned | NotSigned |
| PE-Dateien einschließlich Deinstaller | 266 | 266 |
| Gültig signierte PE-Dateien | 128 | 128 |
| Unsignierte PE-Dateien | 138 | 138 |
| Zusätzliche/entfernte PE-Dateien | keine | keine |
| UPX-Sektionsmarkierungen | keine | keine |
| Historisches numpy.core.multiarray im PYZ | fehlt | vorhanden |
| pip im PYZ | nein | nein |
| pytest / filelock im PYZ | ja / ja | ja / ja |
| OpenSSL -x64 DLL-Version | 3.5.9 | 3.5.5 |

Bei den PE-Dateien haben sich nur Klangwerk.exe, unins000.exe und
`libcrypto-3-x64.dll`/`libssl-3-x64.dll` verändert. Die beiden OpenSSL-Dateien
haben in beiden Builds gültige Oracle-America-Herstellersignaturen. Ihre
unterschiedlichen Versionen zeigen eine unerwünschte Abhängigkeit von der
Build-Umgebung. Eine gültige Signatur ist kein Beleg, dass jede Bibliotheksversion
aktuell oder frei von Sicherheitsproblemen ist.

SHA-256 der installierten Klangwerk.exe:

- 0.2.0: `ddf2cdf933512667eb281b9baf5bbca8251c1c5b03da2e93b1531dea6eb83fab`
- 0.2.1: `51d5307decc40183dba2046dbefb78ee72d9feada14625b940f887ffca71e4dc`

Die Haupt-EXE hat bislang weder digitale Herausgebersignatur noch Windows-
Dateiversionsressource. Der Installer hat eine Produktversionsangabe, aber keine
Authenticode-Signatur. Beide verwenden PyInstaller 6.12.0 im Onedir-/Windowed-
Modus; die NumPy-Korrektur hat nicht auf einen selbstentpackenden Onefile-Build
umgestellt. NumPy 2.2.4, Torch/TorchAudio 2.6.0+cpu und Demucs 4.0.1 bleiben
zwischen diesen Veröffentlichungen gleich. Der Build-Rechner wechselte von
Windows Server 2022 auf 2025, damit die Installationsprüfung die Win11-
Mindestbuildnummer erfüllt.

## Aussage zur Blockierung

Das konkrete CodeIntegrity-Ereignis vom betroffenen Windows-11-Gerät liegt
nicht vor. Die genaue lokale SAC-Entscheidung kann deshalb nicht rekonstruiert
werden. Eine unbekannte, unsignierte EXE mit neuem Hash ist jedoch eine
plausible Erklärung. Die Reputation des alten Dateihashes wird durch einen
Neubau nicht automatisch auf den neuen übertragen. Auch ein Wechsel von SAC-
Auswertung auf Durchsetzung oder eine aktualisierte Cloudentscheidung wäre
ohne Geräteeintrag nicht auszuschließen.

Die blockierte Haupt-EXE ist tatsächlich unsigniert; das wurde unter Windows
geprüft. Eine erfolgreich gestartete EXE auf einem CI-Server prüft ihre Funktion,
aber nicht ihre Zulassung durch SAC auf einem persönlichen Windows-11-PC.

## Sicherheitsprüfung und Grenzen

Der Quellcode verwendet beim Modellladen SHA-256-Prüfung, eine feste Quelle und
`weights_only=True` mit begrenzten erlaubten Typen. NumPy-Dateien werden ohne
Pickle geladen. Der Unterprozess startet mit Argumentliste ohne Shell.
Audiomaterial wird nicht an externe Dienste gesendet.

Der Versionsabgleich mit pip-audit meldet dennoch bekannte Schwachstellen:

- Torch 2.6.0: darunter CVE-2026-24747 / GHSA-63cw-57p8-fm3p im weights_only-
  Unpickler, behoben ab 2.10.0. Der feste Modellhash schließt den üblichen
  Angriffsweg über einen beliebigen manipulierten Checkpoint aus; ein getestetes
  Sicherheitsupdate bleibt erforderlich. Die CPU-Versionsendung +cpu wird beim
  Advisory-Abgleich transparent auf die Basisversion 2.6.0 abgebildet.
- Filelock 3.32.3: drei gemeldete Advisories, Korrekturen ab 4.2.1; Ausnutzbarkeit
  hängt von Plattform, verwendeter Lock-Klasse und Verzeichnisrechten ab.
- pytest 8.3.5: ein Unix-bezogener Advisory-Treffer, derzeit unnötigerweise auch
  im Programmpaket vorhanden. Das ist kein Nachweis einer Windows-Ausnutzung.
- pip-Treffer betreffen die lokale Build-/Prüfumgebung; pip ist in den geprüften
  EXE-Archiven nicht enthalten.

Diese Treffer sind keine Malware-Erkennung und kein Nachweis der Ursache der
SAC-Meldung. Der Scanner enthält teils überlappende und breit gefasste Einträge;
es wird keine bestätigte Ausnutzbarkeit sämtlicher Treffer in Klangwerk behauptet.
Vor einer neuen vertrauenswürdigen Freigabe müssen Laufzeitupdates und ein
kleinerer Paketumfang mit den Modell-/Exporttests geprüft werden.

Microsoft Defender wurde auf der Windows-Prüfmaschine aktualisiert und über
MpCmdRun als abgeschlossener benutzerdefinierter Scan ausgeführt. Ergebnis:
Exitcode 0, »found no threats«, keine neu protokollierten Bedrohungen. Engine
1.1.26090.9, Signaturen 1.461.186.0. Das Ergebnis ist auf diesen Prüflauf begrenzt
und kein Nachweis allgemeiner Schadsoftwarefreiheit oder SAC-Vertrauenswürdigkeit.
Die neue Signatur-Freigabeprüfung wurde mit den veröffentlichten Dateien geprüft
und hat die unsignierte Ausgabe erwartungsgemäß zurückgewiesen. Die Windows-
Versionsressource wurde nativ auf dem Windows-Runner eingelesen und geprüft.

## Änderungen am künftigen Build-Prozess

- Explizit kein UPX und weiterhin Onedir, um die Ausgabe eindeutig festzulegen.
- Windows-Produkt-/Dateiversionsressource ergänzt. Diese ersetzt keine Signatur.
- PATH für PyInstaller auf Python/venv/Systemverzeichnisse begrenzt, um DLLs aus
  fremden installierten Programmen nicht zufällig einzusammeln. Ein vollständiger
  Kandidaten-Neubau muss diese Änderung noch mit dem DLL-Manifest verifizieren.
- Neue lesende Prüfung aller installierten EXE/DLL/PYD einschließlich Deinstaller
  sowie des Installers. Keine Root-Zertifikate, Ausnahmen oder Richtlinien werden
  geändert. Ungültige/fehlende Signaturen sperren die öffentliche Freigabe.
- Der Signaturstatus ist eine notwendige Release-Prüfung; er garantiert keine
  Zulassung durch SAC und ersetzt keine Malware- und Abhängigkeitsprüfung.

Diese Änderungen wurden vorbereitet; es wird kein weiterer unsignierter
Installer als Lösung für die SAC-Blockierung veröffentlicht. Ein geeigneter
öffentlicher Codesigning-Dienst beziehungsweise ein Zertifikat mit verifizierter
Herausgeberidentität ist aktuell nicht konfiguriert. Es wurde kein kostenpflichtiger
Dienst beauftragt und kein Zertifikat gekauft oder selbst ausgestellt.

## Vertrauenswürdige Veröffentlichung ohne Abschalten von SAC

1. Herausgeberidentität über einen geeigneten Anbieter verifizieren, z. B.
   Microsoft Artifact Signing oder eine anerkannte Code-Signing-CA. Kosten,
   regionale Verfügbarkeit und Identitätsanforderungen vorher prüfen. Private
   Schlüssel gehören in einen geschützten Signierdienst/HSM, nicht in den Chat
   oder ins öffentliche GitHub-Repository.
2. Abhängigkeiten aktualisieren und testen; alle PE-Dateien inventarisieren und
   ihre Herkunft festlegen. Gültige Herstellersignaturen erhalten.
3. Eigene sowie benötigte bisher unsignierte PE-Dateien vertrauenswürdig signieren
   und zeitstempeln. Auch den Inno-Deinstaller über dessen SignedUninstaller/
   SignTool-Integration signieren, dann den fertigen Installer signieren.
4. Signaturen auf einer sauberen Maschine prüfen; funktionale Offline-Tests und
   einen Test auf Windows 11 mit aktivem SAC durchführen. Erst dann freigeben.
5. Alternativ kommt eine korrekt eingerichtete Microsoft-Store-Verteilung infrage.
   Sie ist nicht implementiert und erfordert eigene Paket-/Update-/Datentests.
6. Eine Fehlklassifizierung kann Microsoft zur Prüfung gemeldet werden. Das ist
   keine sofortige Freigabe und keine Garantie für eine andere SAC-Entscheidung.

Ein selbstsigniertes Zertifikat, Zertifikatimport beim Benutzer, Umbenennen der
EXE oder Abschalten/Umgehen von Schutzfunktionen ist hier keine Lösung.

## Was der Benutzer jetzt tun kann

1. SAC eingeschaltet lassen und keine Ausnahme für Klangwerk einrichten.
2. Eigene `.klang`-Dateien und die jeweils zugehörigen `.klang.audio`-Ordner
   sichern. Auch `%LOCALAPPDATA%\KlangwerkLocal\Klangwerk` aufbewahren: dort liegen
   Modell, Cache, rohe Takes und Wiederherstellung. Die Dateien nicht löschen.
3. Die Details der Blockierung festhalten. Bei Bedarf in der Ereignisanzeige
   unter **Anwendungs- und Dienstprotokolle → Microsoft → Windows → CodeIntegrity
   → Operational** den Eintrag zur betreffenden Klangwerk-Datei lesen.
4. Für eine Microsoft-Prüfung das offizielle Einreichungsportal verwenden; dabei
   die blockierte Programmdatei auswählen, keine persönlichen Songs/Projekte.
5. Erst einen entsprechend signierten und geprüften Neubau über die vorhandene
   Installation installieren. Eine Datei lediglich neu herunterzuladen oder
   nochmals unsigniert zu bauen erzeugt keinen verlässlichen Vertrauensnachweis.

## Nachweise und offizielle Quellen

- Vergleich: https://github.com/Deansgate/geilopack/actions/runs/40134996088
- Ergänzte Defender-/Signatur-Gate-Prüfung: https://github.com/Deansgate/geilopack/actions/runs/40135589770
- Microsoft SAC-Übersicht: https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/overview
- Code-Signierung: https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/code-signing-for-smart-app-control
- Microsoft-Dateiprüfung: https://www.microsoft.com/wdsi/filesubmission
- PyTorch-Advisory: https://github.com/advisories/GHSA-63cw-57p8-fm3p

# Windows-Installer über GitHub Actions

Der Workflow `.github/workflows/windows-installer.yml` baut auf einem
Windows-2022-x64-Runner mit Python 3.12. Endbenutzer brauchen Python nicht.
Es wird keine Veröffentlichung als GitHub Release vorgenommen.

Der Workflow läuft beim Push auf den Branch `klangwerk-windows-build` oder
manuell über **Actions → Windows-Installer → Run workflow**.
Der Repository-Inhalt muss dem Projektordner entsprechen: `pyproject.toml`,
`klangwerk/`, `packaging/` und `.github/` liegen direkt im Repository-Stamm.

Nach erfolgreichem Lauf liegt unter **Artifacts → Klangwerk-Windows-Setup**
ein ZIP mit `Setup.exe`, SHA-256-Prüfsumme und kurzem Hinweis bereit.
ZIP entpacken und `Setup.exe` starten. GitHub verlangt für den Artifact-Download
in der Regel eine Anmeldung. Die Artefakte werden 14 Tage aufbewahrt.

Der Build führt die Softwaretests aus, sammelt Lizenzbeilagen und erstellt den
Installer mit PyInstaller und Inno Setup. Der große KI-Checkpoint wird nicht
auf dem Runner heruntergeladen; die Anwendung bietet den Modellassistenten an.
Der echte Modelltest ist deshalb im Standard-Build übersprungen.

Ein erfolgreicher Build ersetzt keine Prüfung mit einem physischen Mikrofon,
Lautsprechern und der Zielhardware. Der Installer ist zunächst eine unsignierte
Entwicklungsfassung. Eventuelle Windows-Sicherheitshinweise dürfen nicht als
erfolgreiche Hersteller-/Signaturprüfung dargestellt werden.

Voraussetzung zum Ausführen: ein geeignetes Repository mit aktivierten Actions
und verfügbarem Runner-Kontingent. Bei privaten Repositories können die
Kontingente des jeweiligen GitHub-Tarifs gelten; dieser Workflow erhöht keine
Ausgabenlimits und aktiviert keine kostenpflichtigen Zusatzleistungen.

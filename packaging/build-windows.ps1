# Nur für Entwickler. Endbenutzer verwenden das daraus erzeugte Setup.exe.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
function Assert-Exit([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step fehlgeschlagen (Exitcode $LASTEXITCODE)." }
}
if (-not $IsWindows -and $PSVersionTable.PSEdition -eq "Core") {
    throw "Der Windows-Build muss unter Windows 11 x64 ausgeführt werden."
}
if (-not (Test-Path ".build-venv\Scripts\python.exe")) {
    py -3.12 -m venv .build-venv
    Assert-Exit "Python-Umgebung"
}
$Python = Join-Path $PWD ".build-venv\Scripts\python.exe"
& $Python -m pip install --requirement packaging/requirements-windows.txt
Assert-Exit "Abhängigkeiten"
& $Python -m pip install "torch==2.6.0+cpu" "torchaudio==2.6.0+cpu" --index-url https://download.pytorch.org/whl/cpu
Assert-Exit "CPU-KI-Laufzeit"
& $Python -m pip install --requirement packaging/requirements-ai.txt
Assert-Exit "Demucs-Abhängigkeiten"
& $Python -m pip install --no-deps --no-build-isolation -e .
Assert-Exit "Klangwerk installieren"
$env:QT_QPA_PLATFORM = "offscreen"
& $Python -m pytest -q
Assert-Exit "Tests"
Remove-Item Env:QT_QPA_PLATFORM
& $Python packaging/collect-licenses.py
Assert-Exit "Lizenzsammlung"
$QtTranslation = & $Python -c "from PySide6.QtCore import QLibraryInfo; from pathlib import Path; print(Path(QLibraryInfo.path(QLibraryInfo.TranslationsPath)) / 'qtbase_de.qm')"
Assert-Exit "Qt-Übersetzung suchen"
if (-not (Test-Path $QtTranslation)) { throw "Die deutsche Qt-Übersetzung fehlt im Build-Paket." }
& $Python -m PyInstaller --noconfirm --clean --windowed --onedir --name Klangwerk `
    --paths . --collect-all sounddevice --collect-all soundfile `
    --collect-all demucs --collect-all torch --collect-all torchaudio `
    --collect-all dora --collect-all julius --collect-all openunmix `
    --hidden-import klangwerk.ai.worker --hidden-import demucs.htdemucs `
    --add-data "LICENSE;." --add-data "THIRD_PARTY.md;." `
    --add-data "$QtTranslation;PySide6/translations" `
    --add-data "build/licenses;licenses" packaging/entry.py
Assert-Exit "PyInstaller"
$Compiler = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
if (-not $Compiler) { $Compiler = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
if (-not (Test-Path $Compiler)) {
    throw "Inno Setup 6 installieren. Die portable Anwendung liegt bereits in dist\Klangwerk."
}
& $Compiler packaging/installer.iss
Assert-Exit "Inno Setup"
Write-Host "Fertig: dist\installer\Setup.exe. Vor Freigabe Windows-Abnahme durchführen."

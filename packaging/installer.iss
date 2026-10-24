#define AppName "Klangwerk"
#define AppVersion "0.2.1"

[Setup]
AppId={{BDCE680C-B409-4EAE-A729-91ECD889DA23}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Klangwerk Local
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.22000
OutputDir=..\dist\installer
OutputBaseFilename=Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\LICENSE
UninstallDisplayIcon={app}\Klangwerk.exe
SetupLogging=yes

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Verknüpfungen:"; Flags: unchecked

[Files]
Source: "..\dist\Klangwerk\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\docs\BEDIENUNG.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Klangwerk"; Filename: "{app}\Klangwerk.exe"
Name: "{group}\Klangwerk deinstallieren"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Klangwerk"; Filename: "{app}\Klangwerk.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Klangwerk.exe"; Description: "Klangwerk starten"; Flags: nowait postinstall skipifsilent

; Projekte, Cache und Aufnahmen sind Nutzerdaten und werden NICHT deinstalliert.

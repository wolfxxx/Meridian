; Inno Setup script for the Meridian desktop app.
;   iscc packaging\meridian.iss        (run from the meridian\ folder after PyInstaller)
; Produces dist\Meridian-Setup-<version>.exe: a per-user install (no administrator rights),
; Start-menu and optional desktop shortcuts, an uninstaller, and "launch Meridian" at the end.

#ifndef AppVersion
  #define AppVersion "0.2.0"
#endif

[Setup]
AppId={{6F1C2B8E-7D4A-4E53-9A1F-3C5D8E2B7A91}
AppName=Meridian
AppVersion={#AppVersion}
AppVerName=Meridian {#AppVersion}
AppPublisher=Meridian prototype
AppComments=Actuarial modelling: projections, reconciliation and SAM-style capital in one app.
DefaultDirName={autopf}\Meridian
DefaultGroupName=Meridian
DisableProgramGroupPage=yes
DisableDirPage=yes
DisableReadyPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename=Meridian-Setup-{#AppVersion}
SetupIconFile=meridian.ico
UninstallDisplayIcon={app}\Meridian.exe
UninstallDisplayName=Meridian
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\Meridian\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; a clean folder on upgrade, so files removed from a newer build do not linger
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{autoprograms}\Meridian"; Filename: "{app}\Meridian.exe"; Comment: "Actuarial modelling"
Name: "{autodesktop}\Meridian"; Filename: "{app}\Meridian.exe"; Tasks: desktopicon; Comment: "Actuarial modelling"

[Run]
Filename: "{app}\Meridian.exe"; Description: "Open Meridian now"; Flags: nowait postinstall skipifsilent

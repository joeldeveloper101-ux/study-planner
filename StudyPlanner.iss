; ------------------------------------------------------------
;  Study Planner - Inno Setup script
;  Run build.bat first (it creates dist\StudyPlanner\), then
;  compile this file (Ctrl+F9) or let build.bat do it for you.
; ------------------------------------------------------------
#define MyAppName "Study Planner"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Joel Kyaligamba"
#define MyAppExeName "StudyPlanner.exe"

[Setup]
AppId={{B7C1D3A2-5E4F-4A8B-9C21-6D0F3E8A7B15}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=StudyPlanner_Setup_{#MyAppVersion}
SetupIconFile=app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Lets the user choose "just for me" (no admin needed) or "all users"
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "dist\StudyPlanner\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

; NOTE: tasks, units and settings live in %USERPROFILE%\.study_planner and are
; intentionally NOT removed on uninstall, so user data survives updates.

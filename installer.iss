; Installer script for ReelsMaker Pro. Build with:
;   ISCC.exe /DAppVersion=1.1.0 installer.iss
; Expects a finished PyInstaller build in dist\ReelsMakerPro\.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define AppName "ReelsMaker Pro"
#define AppShortName "ReelsMakerPro"
#define AppPublisher "Magerko"
#define AppURL "https://github.com/Magerko/ReelsMaker-Pro"
#define AppExeName "ReelsMakerPro.exe"

[Setup]
; Keep this GUID stable forever - it is how Windows recognises an upgrade of an
; existing install rather than a second copy.
AppId={{7E5E5CCC-4EF2-42E8-A717-D22183A38E8B}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
VersionInfoVersion={#AppVersion}

; Install into the user profile so no admin rights and no UAC prompt are needed.
; An unsigned installer that also demands elevation is what actually scares
; people off; without it Windows shows a far milder warning.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={autopf}\{#AppShortName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

OutputDir=installer_output
OutputBaseFilename={#AppShortName}-{#AppVersion}-setup
SetupIconFile=resources\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
LicenseFile=LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "ukrainian"; MessagesFile: "compiler:Languages\Ukrainian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\ReelsMakerPro\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\ReelsMakerPro\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
; Распознавание речи — отдельный исполняемый файл со своим набором библиотек.
; Без него не работают автоматические субтитры, а установщик вышел бы неполным
; молча: разницу видно только по размеру.
Source: "dist\ReelsMakerPro\transcriber\*"; DestDir: "{app}\transcriber"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion
Source: "vendor\FFMPEG-LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

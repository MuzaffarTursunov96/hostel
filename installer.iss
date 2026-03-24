[Setup]
AppName=Hostel Manager
AppVersion=1.0.0
DefaultDirName={pf}\HostelManager
DefaultGroupName=Hostel Manager
OutputBaseFilename=HostelManager_Setup
Compression=lzma
SolidCompression=yes
SetupIconFile=assets\app_comfy.ico
WizardStyle=modern

[Files]
Source: "dist\HostelManager.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\app_comfy.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu shortcut
Name: "{group}\Hostel Manager"; Filename: "{app}\HostelManager.exe"; IconFilename: "{app}\app_comfy.ico"

; Desktop shortcut ✅
Name: "{commondesktop}\Hostel Manager"; Filename: "{app}\HostelManager.exe"; IconFilename: "{app}\app_comfy.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checked

[Run]
Filename: "{app}\HostelManager.exe"; Description: "Launch Hostel Manager"; Flags: nowait postinstall skipifsilent

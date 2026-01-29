[Setup]
AppName=Hostel Manager
AppVersion=1.0.0
DefaultDirName={pf}\HostelManager
DefaultGroupName=Hostel Manager
OutputBaseFilename=HostelManager_Setup
Compression=lzma
SolidCompression=yes
SetupIconFile=assets\app1.ico
WizardStyle=modern

[Files]
Source: "dist\HostelManager.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu shortcut
Name: "{group}\Hostel Manager"; Filename: "{app}\HostelManager.exe"

; Desktop shortcut ✅
Name: "{commondesktop}\Hostel Manager"; Filename: "{app}\HostelManager.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checkedonce

[Run]
Filename: "{app}\HostelManager.exe"; Description: "Launch Hostel Manager"; Flags: nowait postinstall skipifsilent

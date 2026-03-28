#ifndef AppName
  #define AppName "HMS"
#endif

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

#ifndef SourceExe
  #define SourceExe "OutputBuild\" + AppName + "-" + AppVersion + "-win10-11\" + AppName + ".exe"
#endif

#ifndef OutputFile
  #define OutputFile AppName + "_Setup_" + AppVersion
#endif

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={pf}\{#AppName}
DefaultGroupName={#AppName}
OutputBaseFilename={#OutputFile}
Compression=lzma
SolidCompression=yes
SetupIconFile=assets\app_comfy.ico
WizardStyle=modern

[Files]
Source: "{#SourceExe}"; DestDir: "{app}"; DestName: "{#AppName}.exe"; Flags: ignoreversion
Source: "assets\app_comfy.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppName}.exe"; IconFilename: "{app}\app_comfy.ico"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppName}.exe"; IconFilename: "{app}\app_comfy.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checked

[Run]
Filename: "{app}\{#AppName}.exe"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

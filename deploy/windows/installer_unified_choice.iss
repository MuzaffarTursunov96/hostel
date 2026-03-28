#ifndef AppName
  #define AppName "HMS"
#endif

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

#ifndef ModernExe
  #define ModernExe "OutputBuild\" + AppName + "-" + AppVersion + "-win10-11\" + AppName + ".exe"
#endif

#ifndef LegacyExe
  #define LegacyExe "OutputBuild\" + AppName + "-" + AppVersion + "-win7-8\" + AppName + ".exe"
#endif

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={pf}\{#AppName}
DefaultGroupName={#AppName}
OutputBaseFilename={#AppName}_Unified_Setup_{#AppVersion}
Compression=lzma
SolidCompression=yes
SetupIconFile=assets\app_comfy.ico
WizardStyle=modern

[Files]
Source: "{#ModernExe}"; DestDir: "{app}"; DestName: "{#AppName}.exe"; Flags: ignoreversion; Check: IsModernSelected
Source: "{#LegacyExe}"; DestDir: "{app}"; DestName: "{#AppName}.exe"; Flags: ignoreversion; Check: IsLegacySelected
Source: "assets\app_comfy.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppName}.exe"; IconFilename: "{app}\app_comfy.ico"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppName}.exe"; IconFilename: "{app}\app_comfy.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checked

[Run]
Filename: "{app}\{#AppName}.exe"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[Code]
var
  OsChoicePage: TInputOptionWizardPage;

function IsWindows10OrNewer: Boolean;
var
  V: TWindowsVersion;
begin
  GetWindowsVersionEx(V);
  Result := (V.Major >= 10);
end;

function IsModernSelected: Boolean;
begin
  Result := Assigned(OsChoicePage) and (OsChoicePage.SelectedValueIndex = 0);
end;

function IsLegacySelected: Boolean;
begin
  Result := Assigned(OsChoicePage) and (OsChoicePage.SelectedValueIndex = 1);
end;

procedure InitializeWizard;
begin
  OsChoicePage := CreateInputOptionPage(
    wpSelectDir,
    'Windows Version',
    'Choose target Windows version',
    'Select which build to install for this PC.',
    True,
    False
  );
  OsChoicePage.Add('Windows 10 / 11 (Recommended)');
  OsChoicePage.Add('Windows 7 / 8 (Legacy)');

  if IsWindows10OrNewer then
    OsChoicePage.SelectedValueIndex := 0
  else
    OsChoicePage.SelectedValueIndex := 1;
end;

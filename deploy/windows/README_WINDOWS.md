# Windows Client Compatibility

To support mixed client OS versions, ship **two builds**:

- `win10-11` (modern)
- `win7-8` (legacy compatibility package)

## Build Script

Use:

```powershell
powershell -ExecutionPolicy Bypass -File deploy\windows\build_windows_matrix_v2.ps1 -Version 1.2.3 -AppName HMS
```

This creates:

- `OutputBuild\HMS-1.2.3-win10-11.zip`
- `OutputBuild\HMS-1.2.3-win7-8.zip` (unless `-SkipLegacy`)

## Separate Installers (Recommended)

Build 2 separate setup files from those builds:

```powershell
powershell -ExecutionPolicy Bypass -File deploy\windows\build_separate_installers.ps1 -Version 1.2.3 -AppName HMS
```

This produces:
- `Output\HMS-Setup-1.2.3-win10-11.exe`
- `Output\HMS-Setup-1.2.3-win7-8.exe`

Requirements:
- Inno Setup 6 (`ISCC.exe`) installed
- both builds already created in `OutputBuild\HMS-1.2.3-win10-11\HMS.exe` and `OutputBuild\HMS-1.2.3-win7-8\HMS.exe`

## Optional Python Overrides

If you have separate Python installs:

```powershell
powershell -ExecutionPolicy Bypass -File deploy\windows\build_windows_matrix.ps1 `
  -Version 1.2.3 `
  -AppName HMS `
  -ModernPython "C:\Python311\python.exe" `
  -LegacyPython "C:\Python38\python.exe"
```

## Important Notes

- For Windows 10/11 clients, ask them to install **Microsoft Visual C++ Redistributable 2015-2022** (x64 and x86) if needed.
- Do **not** copy random DLL files from internet.
- Legacy build is intended for Windows 7/8 environments where modern build fails with missing system DLL APIs.

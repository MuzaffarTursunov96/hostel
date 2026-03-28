param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9]+\.[0-9]+\.[0-9]+$')]
    [string]$Version,

    [string]$AppName = 'HMS',

    [string]$ModernPython = '',

    [string]$LegacyPython = '',

    [switch]$SkipLegacy,

    [switch]$SkipModern
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir '..\..')

function Resolve-Python([string]$preferred) {
    if ($preferred -and (Test-Path $preferred)) {
        return (Resolve-Path $preferred).Path
    }
    $venvPy = Join-Path $repoRoot 'venv\Scripts\python.exe'
    if (Test-Path $venvPy) {
        return (Resolve-Path $venvPy).Path
    }
    return 'python'
}

function New-ZipFromDir(
    [string]$sourceDir,
    [string]$zipPath
) {
    if (Test-Path $zipPath) { Remove-Item -Force $zipPath }

    $compressCmd = Get-Command Compress-Archive -ErrorAction SilentlyContinue
    if ($compressCmd) {
        Compress-Archive -Path (Join-Path $sourceDir '*') -DestinationPath $zipPath
        return
    }

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory($sourceDir, $zipPath)
}

function Ensure-Tooling([string]$pythonExe, [string]$channel) {
    Write-Host "[$channel] Ensuring pip tooling..." -ForegroundColor Cyan
    # Keep setuptools with pkg_resources for both channels.
    & $pythonExe -m pip install --upgrade pip wheel
    if ($LASTEXITCODE -ne 0) {
        throw "[$channel] Failed to upgrade pip/wheel."
    }
    & $pythonExe -m pip install "setuptools<81"
    if ($LASTEXITCODE -ne 0) {
        throw "[$channel] Failed to install compatible setuptools."
    }

    if ($channel -eq 'legacy') {
        $pyTag = (& $pythonExe -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')").Trim()
        if (@('3.8', '3.9', '3.10') -notcontains $pyTag) {
            throw "[legacy] Python $pyTag detected. Legacy build requires Python 3.8/3.9/3.10."
        }
        & $pythonExe -m pip install "setuptools<81" "pyinstaller<6" "pyinstaller-hooks-contrib<2025" "PySide2==5.15.2.1" "shiboken2==5.15.2.1"
    } else {
        & $pythonExe -m pip install "pyinstaller>=6,<7" "PySide6" "shiboken6"
    }
    if ($LASTEXITCODE -ne 0) {
        throw "[$channel] Failed to install pyinstaller."
    }
}

function Invoke-Build(
    [string]$channel,
    [string]$pythonExe,
    [string]$osTag
) {
    Write-Host "=== [$channel] Build started ===" -ForegroundColor Yellow
    Write-Host "Python: $pythonExe"

    Ensure-Tooling -pythonExe $pythonExe -channel $channel

    $buildId = Get-Date -Format 'yyyyMMddHHmmss'
    $buildExeName = "$AppName-$channel-$buildId"
    $distPath = Join-Path $repoRoot "dist\$channel-$buildId"
    $workPath = Join-Path $repoRoot "build\$channel-$buildId"
    $specPath = Join-Path $repoRoot "build\$channel-$buildId\spec"
    $specFile = Join-Path $specPath "$buildExeName.spec"

    New-Item -ItemType Directory -Path $specPath -Force | Out-Null

    $iconPath = (Join-Path $repoRoot 'assets\app_comfy.ico')
    $assetsPath = (Join-Path $repoRoot 'assets')
    $stylePath = (Join-Path $repoRoot 'style.qss')
    $envPath = (Join-Path $repoRoot '.env')
    $entryScript = if ($channel -eq 'legacy') { 'main_qt_legacy.py' } else { 'main_qt.py' }
    $qtPkg = if ($channel -eq 'legacy') { 'PySide2' } else { 'PySide6' }
    $shibokenPkg = if ($channel -eq 'legacy') { 'shiboken2' } else { 'shiboken6' }

    $args = @(
        '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        '--name', $buildExeName,
        '--windowed',
        '--onefile',
        "--icon=$iconPath",
        '--add-data', "$assetsPath;assets",
        '--collect-all', $qtPkg,
        '--collect-all', $shibokenPkg,
        '--distpath', $distPath,
        '--workpath', $workPath,
        '--specpath', $specPath,
        $entryScript
    )

    if (Test-Path $stylePath) {
        $args += @('--add-data', "$stylePath;.")
    }
    if (Test-Path $envPath) {
        $args += @('--add-data', "$envPath;.")
    }

    & $pythonExe @args
    if ($LASTEXITCODE -ne 0) {
        throw "[$channel] PyInstaller build failed."
    }

    $builtExe = Join-Path $distPath "$buildExeName.exe"
    if (-not (Test-Path $builtExe)) {
        throw "[$channel] Built EXE not found: $builtExe"
    }

    $releaseRoot = Join-Path $repoRoot 'OutputBuild'
    $releaseDir = Join-Path $releaseRoot "$AppName-$Version-$osTag"
    $zipPath = Join-Path $releaseRoot "$AppName-$Version-$osTag.zip"

    New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null
    if (Test-Path $releaseDir) { Remove-Item -Recurse -Force $releaseDir }
    New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null

    Copy-Item -Path $builtExe -Destination (Join-Path $releaseDir "$AppName.exe") -Force
    if (Test-Path 'installer.iss') {
        Copy-Item -Path 'installer.iss' -Destination (Join-Path $releaseDir 'installer.iss') -Force
    }

    if (Test-Path $specFile) {
        Copy-Item -Path $specFile -Destination (Join-Path $releaseDir "$AppName.spec") -Force
    }

    New-ZipFromDir -sourceDir $releaseDir -zipPath $zipPath

    Write-Host "[$channel] EXE: $builtExe" -ForegroundColor Green
    Write-Host "[$channel] ZIP: $zipPath" -ForegroundColor Green
}

Push-Location $repoRoot
try {
    if (-not (Test-Path 'main_qt.py')) {
        throw 'main_qt.py not found in repository root.'
    }
    if (-not (Test-Path 'main_qt_legacy.py')) {
        throw 'main_qt_legacy.py not found in repository root.'
    }
    if (-not (Test-Path 'assets\app_comfy.ico')) {
        throw 'assets\app_comfy.ico not found.'
    }

    if (-not $SkipModern) {
        $modernPy = Resolve-Python -preferred $ModernPython
        Invoke-Build -channel 'modern' -pythonExe $modernPy -osTag 'win10-11'
    }

    if (-not $SkipLegacy) {
        $legacyPy = Resolve-Python -preferred $LegacyPython
        Invoke-Build -channel 'legacy' -pythonExe $legacyPy -osTag 'win7-8'
    }

    Write-Host ''
    Write-Host '=== WINDOWS MATRIX BUILD SUCCESS ===' -ForegroundColor Green
}
finally {
    Pop-Location
}

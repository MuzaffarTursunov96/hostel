param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9]+\.[0-9]+\.[0-9]+$')]
    [string]$Version,

    [string]$AppName = 'HMS',

    [string]$ModernPython = '',

    [string]$LegacyPython = '',

    [switch]$SkipLegacy
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

function Ensure-Tooling([string]$pythonExe, [string]$channel) {
    Write-Host "[$channel] Ensuring pip tooling..." -ForegroundColor Cyan
    & $pythonExe -m pip install --upgrade pip setuptools wheel
    if ($LASTEXITCODE -ne 0) {
        throw "[$channel] Failed to upgrade pip tooling."
    }

    if ($channel -eq 'legacy') {
        & $pythonExe -m pip install "pyinstaller<6"
    } else {
        & $pythonExe -m pip install pyinstaller
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

    $args = @(
        '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        '--name', $buildExeName,
        '--windowed',
        '--onefile',
        "--icon=$iconPath",
        '--add-data', "$assetsPath;assets",
        '--collect-all', 'PySide6',
        '--collect-all', 'shiboken6',
        '--distpath', $distPath,
        '--workpath', $workPath,
        '--specpath', $specPath,
        'main_qt.py'
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

    if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
    Compress-Archive -Path (Join-Path $releaseDir '*') -DestinationPath $zipPath

    Write-Host "[$channel] EXE: $builtExe" -ForegroundColor Green
    Write-Host "[$channel] ZIP: $zipPath" -ForegroundColor Green
}

Push-Location $repoRoot
try {
    if (-not (Test-Path 'main_qt.py')) {
        throw 'main_qt.py not found in repository root.'
    }
    if (-not (Test-Path 'assets\app_comfy.ico')) {
        throw 'assets\app_comfy.ico not found.'
    }

    $modernPy = Resolve-Python -preferred $ModernPython
    Invoke-Build -channel 'modern' -pythonExe $modernPy -osTag 'win10-11'

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

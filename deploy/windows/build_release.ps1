param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9]+\.[0-9]+\.[0-9]+$')]
    [string]$Version,

    [string]$AppName = 'HMS'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir '..\..')

Push-Location $repoRoot
try {
    Write-Host "=== HMS Windows Release Build ===" -ForegroundColor Cyan
    Write-Host "Repository: $repoRoot"
    Write-Host "Version: $Version"
    Write-Host "AppName: $AppName"

    if (-not (Test-Path 'main_qt.py')) {
        throw 'main_qt.py not found in repository root.'
    }

    $pythonExe = Join-Path $repoRoot 'venv\Scripts\python.exe'
    if (-not (Test-Path $pythonExe)) {
        $pythonExe = 'python'
        Write-Host 'venv\\Scripts\\python.exe not found, using system python.' -ForegroundColor Yellow
    }

    Write-Host 'Ensuring PyInstaller is installed...'
    & $pythonExe -m pip show pyinstaller *> $null
    if ($LASTEXITCODE -ne 0) {
        & $pythonExe -m pip install pyinstaller
        if ($LASTEXITCODE -ne 0) {
            throw 'Failed to install pyinstaller.'
        }
    }

    Write-Host 'Cleaning previous artifacts...'
    foreach ($path in @('build', 'dist', "$AppName.spec")) {
        if (Test-Path $path) {
            Remove-Item -Recurse -Force $path
        }
    }

    if (-not (Test-Path 'assets\app_comfy.ico')) {
        throw 'assets\\app_comfy.ico not found. Please place your icon there.'
    }

    Write-Host 'Running PyInstaller...' -ForegroundColor Cyan
    $args = @(
        '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        '--name', $AppName,
        '--windowed',
        '--onefile',
        '--icon=assets\app_comfy.ico',
        '--add-data', 'assets;assets',
        '--add-data', 'style.qss;.',
        '--add-data', '.env;.',
        '--collect-all', 'PySide6',
        '--collect-all', 'shiboken6',
        'main_qt.py'
    )

    & $pythonExe @args
    if ($LASTEXITCODE -ne 0) {
        throw 'PyInstaller build failed.'
    }

    $builtExe = Join-Path $repoRoot "dist\$AppName.exe"
    if (-not (Test-Path $builtExe)) {
        throw "Built EXE not found: $builtExe"
    }

    $releaseRoot = Join-Path $repoRoot 'OutputBuild'
    $releaseDir = Join-Path $releaseRoot "$AppName-$Version"
    $zipPath = Join-Path $releaseRoot "$AppName-$Version-windows.zip"

    New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null
    if (Test-Path $releaseDir) { Remove-Item -Recurse -Force $releaseDir }
    New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null

    Copy-Item -Path $builtExe -Destination (Join-Path $releaseDir "$AppName.exe") -Force

    if (Test-Path 'installer.iss') {
        Copy-Item -Path 'installer.iss' -Destination (Join-Path $releaseDir 'installer.iss') -Force
    }

    if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
    Compress-Archive -Path (Join-Path $releaseDir '*') -DestinationPath $zipPath

    Write-Host ''
    Write-Host '=== BUILD SUCCESS ===' -ForegroundColor Green
    Write-Host "EXE: $builtExe"
    Write-Host "Release Folder: $releaseDir"
    Write-Host "ZIP: $zipPath"
}
finally {
    Pop-Location
}

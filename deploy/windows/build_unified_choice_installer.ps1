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
$issFile = Join-Path $scriptDir 'installer_unified_choice.iss'

if (-not (Test-Path $issFile)) {
    throw "Installer script not found: $issFile"
}

$modernExe = Join-Path $repoRoot "OutputBuild\$AppName-$Version-win10-11\$AppName.exe"
$legacyExe = Join-Path $repoRoot "OutputBuild\$AppName-$Version-win7-8\$AppName.exe"

if (-not (Test-Path $modernExe)) {
    throw "Modern build EXE not found: $modernExe"
}
if (-not (Test-Path $legacyExe)) {
    throw "Legacy build EXE not found: $legacyExe"
}

function Resolve-Iscc {
    $cmd = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $defaultPaths = @(
        'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
        'C:\Program Files\Inno Setup 6\ISCC.exe'
    )
    foreach ($p in $defaultPaths) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

$iscc = Resolve-Iscc
if (-not $iscc) {
    throw "ISCC.exe not found. Install Inno Setup 6 or add ISCC.exe to PATH."
}

Push-Location $repoRoot
try {
    Write-Host "Building unified choice installer..." -ForegroundColor Cyan
    Write-Host "ISCC: $iscc"
    Write-Host "Version: $Version"
    Write-Host "AppName: $AppName"

    & $iscc "/DAppName=$AppName" "/DAppVersion=$Version" "$issFile"
    if ($LASTEXITCODE -ne 0) {
        throw "ISCC build failed with exit code $LASTEXITCODE"
    }

    Write-Host ''
    Write-Host '=== UNIFIED INSTALLER BUILD SUCCESS ===' -ForegroundColor Green
}
finally {
    Pop-Location
}

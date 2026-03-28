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
$issFile = Join-Path $scriptDir 'installer_separate_template.iss'

function Resolve-Iscc {
    $cmd = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($p in @(
        'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
        'C:\Program Files\Inno Setup 6\ISCC.exe'
    )) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

if (-not (Test-Path $issFile)) {
    throw "Installer template not found: $issFile"
}

$iscc = Resolve-Iscc
if (-not $iscc) {
    throw 'ISCC.exe not found. Install Inno Setup 6 or add ISCC.exe to PATH.'
}

$modernExe = Join-Path $repoRoot "OutputBuild\$AppName-$Version-win10-11\$AppName.exe"
$legacyExe = Join-Path $repoRoot "OutputBuild\$AppName-$Version-win7-8\$AppName.exe"

if (-not (Test-Path $modernExe)) { throw "Modern EXE not found: $modernExe" }
if (-not (Test-Path $legacyExe)) { throw "Legacy EXE not found: $legacyExe" }

Push-Location $repoRoot
try {
    Write-Host "Building separate installers with ISCC: $iscc" -ForegroundColor Cyan

    & $iscc "/DAppName=$AppName" "/DAppVersion=$Version" "/DSourceExe=$modernExe" "/DOutputFile=$AppName-Setup-$Version-win10-11" "$issFile"
    if ($LASTEXITCODE -ne 0) { throw "Modern installer build failed: exit code $LASTEXITCODE" }

    & $iscc "/DAppName=$AppName" "/DAppVersion=$Version" "/DSourceExe=$legacyExe" "/DOutputFile=$AppName-Setup-$Version-win7-8" "$issFile"
    if ($LASTEXITCODE -ne 0) { throw "Legacy installer build failed: exit code $LASTEXITCODE" }

    Write-Host ''
    Write-Host '=== SEPARATE INSTALLERS BUILD SUCCESS ===' -ForegroundColor Green
    Write-Host "Output folder: $repoRoot\Output"
}
finally {
    Pop-Location
}

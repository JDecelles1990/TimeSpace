#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Two-stage reproducible Windows standalone release build for TimeSpace.
    Stage 1: Compiles the Go diagnostic CLI (GOOS=windows GOARCH=amd64 CGO_ENABLED=0).
    Stage 2: Bundles Python + PySide6 + Go CLI via PyInstaller (--onedir, --noconsole).
#>
param(
    [string]$Version = "3.24.0",
    [switch]$SkipZip
)

$ErrorActionPreference = "Stop"

function Assert-LastExitCode {
    param([string]$StepName)
    if ($LASTEXITCODE -ne 0) {
        throw "$StepName failed with exit code $LASTEXITCODE"
    }
}

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$GoEngineDir = Join-Path $RepoRoot "go_engine"
$BuildRoot = Join-Path $RepoRoot "build"
$GoStageDir = Join-Path $BuildRoot "go_stage"
$StagedGoExe = Join-Path $GoStageDir "diag_windows.exe"
$PyBuildDir = Join-Path $BuildRoot "TimeSpace"
$DistRoot = Join-Path $RepoRoot "dist"
$DistAppDir = Join-Path $DistRoot "TimeSpace"
$SpecFile = Join-Path $RepoRoot "TimeSpace.spec"

Write-Host "=== TimeSpace Two-Stage Windows Release Build (v$Version) ===" -ForegroundColor Cyan

if (-not (Test-Path $VenvPython)) {
    throw "Virtual environment Python not found at '$VenvPython'. Run 'python -m venv .venv' and install requirements.txt first."
}
if (-not (Get-Command go -ErrorAction SilentlyContinue)) {
    throw "Go toolchain ('go') not found on PATH. Install Go 1.22+ from https://go.dev/dl/."
}
if (-not (Test-Path $SpecFile)) {
    throw "PyInstaller spec not found at '$SpecFile'."
}

& $VenvPython -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is not installed in .venv. Install it with: .\.venv\Scripts\python.exe -m pip install 'pyinstaller>=6.11'"
}

# Clean stale Stage 1 & Stage 2 outputs
foreach ($dir in @($GoStageDir, $PyBuildDir, $DistAppDir)) {
    if (Test-Path $dir) {
        Remove-Item -LiteralPath $dir -Recurse -Force
    }
}
New-Item -ItemType Directory -Path $GoStageDir -Force | Out-Null
New-Item -ItemType Directory -Path $DistRoot -Force | Out-Null

# ── Stage 1: Compile Go Diagnostic CLI (Windows amd64, CGO_ENABLED=0) ────────
Write-Host "`n[Stage 1/2] Compiling Go diagnostic CLI -> build/go_stage/diag_windows.exe..." -ForegroundColor Yellow
$PrevGOOS = $env:GOOS
$PrevGOARCH = $env:GOARCH
$PrevCGO = $env:CGO_ENABLED
Push-Location $GoEngineDir
try {
    $env:GOOS = "windows"
    $env:GOARCH = "amd64"
    $env:CGO_ENABLED = "0"

    & go vet ./...
    Assert-LastExitCode "go vet"

    & go build -trimpath -ldflags="-s -w" -o $StagedGoExe .
    Assert-LastExitCode "go build"
} finally {
    if ($null -eq $PrevGOOS) { Remove-Item Env:\GOOS -ErrorAction SilentlyContinue } else { $env:GOOS = $PrevGOOS }
    if ($null -eq $PrevGOARCH) { Remove-Item Env:\GOARCH -ErrorAction SilentlyContinue } else { $env:GOARCH = $PrevGOARCH }
    if ($null -eq $PrevCGO) { Remove-Item Env:\CGO_ENABLED -ErrorAction SilentlyContinue } else { $env:CGO_ENABLED = $PrevCGO }
    Pop-Location
}

if (-not (Test-Path $StagedGoExe)) {
    throw "Expected staged Go binary at '$StagedGoExe' was not created."
}
$GoSizeMB = [Math]::Round((Get-Item $StagedGoExe).Length / 1MB, 2)
Write-Host "  [OK] Staged Go binary ready ($GoSizeMB MB)" -ForegroundColor Green

# ── Stage 2: Bundle with PyInstaller (--onedir, console=False) ───────────────
Write-Host "`n[Stage 2/2] Bundling Python + PySide6 + Go CLI via PyInstaller..." -ForegroundColor Yellow
Push-Location $RepoRoot
try {
    & $VenvPython -m PyInstaller --noconfirm --clean $SpecFile
    Assert-LastExitCode "PyInstaller build"
} finally {
    Pop-Location
}

# ── Post-Build Asset Verification ────────────────────────────────────────────
$OutExe = Join-Path $DistAppDir "TimeSpace.exe"
$OutBundledGo = Join-Path $DistAppDir "_internal\bin\diag_windows.exe"
$OutIcon = Join-Path $DistAppDir "_internal\assets\timespace.ico"

foreach ($required in @($OutExe, $OutBundledGo, $OutIcon)) {
    if (-not (Test-Path $required)) {
        throw "Required release artifact missing: '$required'"
    }
}

$Files = Get-ChildItem -LiteralPath $DistAppDir -Recurse -File
$TotalBytes = ($Files | Measure-Object -Property Length -Sum).Sum
$TotalMB = [Math]::Round($TotalBytes / 1MB, 2)

Write-Host "`n[Verified] Bundle artifacts present:" -ForegroundColor Green
Write-Host "  App Exe   : $OutExe"
Write-Host "  Go CLI    : $OutBundledGo"
Write-Host "  App Icon  : $OutIcon"
Write-Host "  Bundle    : $($Files.Count) files, $TotalMB MB uncompressed"

if (-not $SkipZip) {
    $ZipName = "TimeSpace-v$Version-win64.zip"
    $ZipPath = Join-Path $DistRoot $ZipName
    $ShaPath = "$ZipPath.sha256"
    if (Test-Path $ZipPath) { Remove-Item -LiteralPath $ZipPath -Force }
    if (Test-Path $ShaPath) { Remove-Item -LiteralPath $ShaPath -Force }

    Compress-Archive -Path $DistAppDir -DestinationPath $ZipPath -CompressionLevel Optimal -Force
    $Hash = (Get-FileHash -LiteralPath $ZipPath -Algorithm SHA256).Hash.ToLowerInvariant()
    "$Hash  $ZipName" | Out-File -LiteralPath $ShaPath -Encoding ascii -NoNewline
    $ZipMB = [Math]::Round((Get-Item $ZipPath).Length / 1MB, 2)

    Write-Host "  Zip       : $ZipPath ($ZipMB MB)" -ForegroundColor Cyan
    Write-Host "  SHA-256   : $Hash" -ForegroundColor Cyan
}

Write-Host "`n=== Build Completed Successfully ===" -ForegroundColor Green

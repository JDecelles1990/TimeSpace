#!/usr/bin/env pwsh
# Cross-compile standalone Go diagnostic binaries for Windows, Linux, and macOS into /bin

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$BinDir = Join-Path $RepoRoot "bin"

if (-not (Test-Path $BinDir)) {
    New-Item -ItemType Directory -Path $BinDir | Out-Null
}

if (-not (Get-Command go -ErrorAction SilentlyContinue)) {
    Write-Error "Go toolchain ('go') is not installed or not on PATH. Install Go 1.22+ from https://go.dev/dl/ to compile binaries."
    exit 1
}

Push-Location $ScriptDir
try {
    $env:CGO_ENABLED = "0"

    Write-Host "Building Windows amd64 -> bin/diag_windows.exe ..." -ForegroundColor Cyan
    $env:GOOS = "windows"
    $env:GOARCH = "amd64"
    go build -ldflags="-s -w" -o (Join-Path $BinDir "diag_windows.exe") .

    Write-Host "Building Linux amd64 -> bin/diag_linux ..." -ForegroundColor Cyan
    $env:GOOS = "linux"
    $env:GOARCH = "amd64"
    go build -ldflags="-s -w" -o (Join-Path $BinDir "diag_linux") .

    Write-Host "Building macOS arm64 -> bin/diag_mac_arm64 ..." -ForegroundColor Cyan
    $env:GOOS = "darwin"
    $env:GOARCH = "arm64"
    go build -ldflags="-s -w" -o (Join-Path $BinDir "diag_mac_arm64") .

    Write-Host "All Go diagnostic binaries compiled successfully into $BinDir" -ForegroundColor Green
} finally {
    Remove-Item Env:\GOOS -ErrorAction SilentlyContinue
    Remove-Item Env:\GOARCH -ErrorAction SilentlyContinue
    Pop-Location
}


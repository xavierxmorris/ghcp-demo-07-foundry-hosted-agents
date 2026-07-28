<#
.SYNOPSIS
    Resets local demo state between presentations.

.DESCRIPTION
    Removes virtual environments, Python caches, and generated eval artifacts,
    then re-runs the Foundry health check.

    This does NOT touch Azure. Deployed agents stay warm, which is what you want
    between back-to-back sessions. For a full teardown run `azd down --purge`.
#>
[CmdletBinding()]
param(
    [switch]$KeepVenvs
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

Write-Host '==> Removing Python caches' -ForegroundColor Cyan
Get-ChildItem -Path $repo -Include '__pycache__', '.pytest_cache', '.ruff_cache' -Recurse -Directory -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch '\\\.venv' } |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host '==> Removing generated eval artifacts' -ForegroundColor Cyan
# Authored datasets and rubrics are committed and must survive a reset. Only the
# generated baseline configs and any downloaded results are removed.
Get-ChildItem -Path "$repo\src" -Directory | ForEach-Object {
    foreach ($leaf in '.agent_configs', '.foundry\results') {
        $target = Join-Path $_.FullName $leaf
        if (Test-Path $target) {
            Remove-Item $target -Recurse -Force
            Write-Host "    removed $target"
        }
    }
    $generated = Join-Path $_.FullName 'evaluators\smoke-core'
    if (Test-Path $generated) {
        Remove-Item $generated -Recurse -Force
        Write-Host "    removed $generated"
    }
}

if (-not $KeepVenvs) {
    Write-Host '==> Removing virtual environments' -ForegroundColor Cyan
    foreach ($venv in @("$repo\.venv", "$repo\.venv-tests", "$repo\src\devops-triage\.venv", "$repo\src\docs-qa\.venv")) {
        if (Test-Path $venv) {
            Remove-Item $venv -Recurse -Force
            Write-Host "    removed $venv"
        }
    }
} else {
    Write-Host '==> Keeping virtual environments (-KeepVenvs)' -ForegroundColor Yellow
}

Write-Host '==> Foundry health check' -ForegroundColor Cyan
azd ai agent doctor

Write-Host ''
Write-Host 'Reset complete. Azure resources were not touched.' -ForegroundColor Green
Write-Host 'Full teardown:  azd down --purge' -ForegroundColor DarkGray

# Dump the compose Postgres DB to .\backups\voiceforge_<timestamp>.sql.gz
# Reads target DB/user from compose env (defaults to voiceforge/postgres).
#
# Usage: .\scripts\db_backup.ps1
$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

if (-not (Test-Path "backups")) {
    New-Item -ItemType Directory -Path "backups" | Out-Null
}

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$OutFile = "backups\voiceforge_${Stamp}.sql.gz"

$DbName = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "voiceforge" }
$DbUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "postgres" }

Write-Host "Dumping ${DbName} as ${DbUser} to ${OutFile}..."

# Stream pg_dump | gzip | file. We pipe via cmd /c because PowerShell pipelines
# pre-7 can corrupt binary streams; on PS7+ this still works correctly.
$cmd = "docker compose exec -T postgres pg_dump -U `"$DbUser`" `"$DbName`" | gzip > `"$OutFile`""
& cmd /c $cmd
if ($LASTEXITCODE -ne 0) {
    Write-Error "pg_dump failed (exit $LASTEXITCODE)"
    exit $LASTEXITCODE
}

$SizeMb = [math]::Round((Get-Item $OutFile).Length / 1MB, 2)
Write-Host "Backup written: ${OutFile} (${SizeMb} MB)"

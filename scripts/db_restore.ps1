# Restore a Postgres dump (.sql or .sql.gz) into the compose DB.
#
# Usage: .\scripts\db_restore.ps1 backups\voiceforge_20260424_010000.sql.gz
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$DumpFile
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $DumpFile)) {
    Write-Error "Dump file not found: $DumpFile"
    exit 1
}

$DbName = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "voiceforge" }
$DbUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "postgres" }

Write-Host "Restoring ${DumpFile} into ${DbName} as ${DbUser}..."

if ($DumpFile -like "*.gz") {
    $cmd = "gzip -dc `"$DumpFile`" | docker compose exec -T postgres psql -U `"$DbUser`" -d `"$DbName`""
} else {
    $cmd = "type `"$DumpFile`" | docker compose exec -T postgres psql -U `"$DbUser`" -d `"$DbName`""
}

& cmd /c $cmd
if ($LASTEXITCODE -ne 0) {
    Write-Error "psql restore failed (exit $LASTEXITCODE)"
    exit $LASTEXITCODE
}

Write-Host "Restore complete."

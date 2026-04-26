# Bump backend\VERSION and frontend\package.json by patch|minor|major,
# rotate the CHANGELOG [Unreleased] section into a new dated section,
# and create a "release: vX.Y.Z" commit + git tag.
#
# Usage:
#   .\scripts\bump_version.ps1 patch
#   .\scripts\bump_version.ps1 minor
#   .\scripts\bump_version.ps1 major
#   .\scripts\bump_version.ps1 2.3.4
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Target
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

$Current = (Get-Content "backend\VERSION" -Raw).Trim()

switch -Regex ($Target) {
    '^(patch|minor|major)$' {
        $parts = $Current.Split('.')
        $maj = [int]$parts[0]
        $min = [int]$parts[1]
        $pat = [int]$parts[2]
        switch ($Target) {
            'patch' { $pat++ }
            'minor' { $min++; $pat = 0 }
            'major' { $maj++; $min = 0; $pat = 0 }
        }
        $New = "${maj}.${min}.${pat}"
    }
    '^\d+\.\d+\.\d+$' {
        $New = $Target
    }
    default {
        Write-Error "Invalid bump kind: $Target (expected patch|minor|major|x.y.z)"
        exit 1
    }
}

Write-Host "Bumping ${Current} -> ${New}"

# Use UTF-8 without BOM, no trailing CRLF — Linux containers parse this.
[System.IO.File]::WriteAllText(
    (Join-Path $RepoRoot "backend\VERSION"),
    "${New}`n"
)

# Update frontend\package.json "version".
$pkgPath = Join-Path $RepoRoot "frontend\package.json"
$pkg = Get-Content $pkgPath -Raw | ConvertFrom-Json
$pkg.version = $New
$pkg | ConvertTo-Json -Depth 32 | Set-Content -Path $pkgPath -NoNewline -Encoding utf8
Add-Content -Path $pkgPath -Value "" -Encoding utf8

# Rotate CHANGELOG [Unreleased] -> [NEW] - <date>.
$Today = Get-Date -Format "yyyy-MM-dd"
$cl = Get-Content "CHANGELOG.md" -Raw
# PowerShell's -replace operator only takes (pattern, replacement) — there is no
# "count" parameter like Python's re.sub(..., count=1). A trailing `, 1` would
# be parsed as the array-construction operator and corrupt the file. There is
# only ever one `## [Unreleased]` heading in the file so a global replace is
# equivalent to "first match" here.
$cl = $cl -replace [regex]::Escape("## [Unreleased]"), "## [Unreleased]`n`n## [${New}] - ${Today}"
$cl += "[${New}]: https://github.com/truongqv12/ntd_audio/releases/tag/v${New}`n"
Set-Content -Path "CHANGELOG.md" -Value $cl -NoNewline

git add backend\VERSION frontend\package.json CHANGELOG.md
git commit -m "release: v${New}"
git tag "v${New}"

Write-Host ""
Write-Host "Done. Next steps:"
Write-Host "  git push origin HEAD --tags"
Write-Host "  -> .github/workflows/release.yml will create the GitHub release."

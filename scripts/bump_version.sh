#!/usr/bin/env bash
# Bump backend/VERSION and frontend/package.json by patch|minor|major,
# rotate the CHANGELOG [Unreleased] section into a new dated section,
# and create a "release: vX.Y.Z" commit + git tag.
#
# Usage:
#   ./scripts/bump_version.sh patch
#   ./scripts/bump_version.sh minor
#   ./scripts/bump_version.sh major
#   ./scripts/bump_version.sh 2.3.4   # explicit version
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 patch|minor|major|<x.y.z>" >&2
  exit 1
fi

CURRENT="$(cat backend/VERSION | tr -d '[:space:]')"
TARGET="$1"

case "$TARGET" in
  patch|minor|major)
    IFS='.' read -r MAJ MIN PAT <<< "$CURRENT"
    case "$TARGET" in
      patch) PAT=$((PAT + 1)) ;;
      minor) MIN=$((MIN + 1)); PAT=0 ;;
      major) MAJ=$((MAJ + 1)); MIN=0; PAT=0 ;;
    esac
    NEW="${MAJ}.${MIN}.${PAT}"
    ;;
  [0-9]*.[0-9]*.[0-9]*)
    NEW="$TARGET"
    ;;
  *)
    echo "Invalid bump kind: $TARGET" >&2
    exit 1
    ;;
esac

echo "Bumping ${CURRENT} -> ${NEW}"

echo "${NEW}" > backend/VERSION

# Update frontend/package.json "version".
python3 - <<PY
import json, pathlib
pkg = pathlib.Path("frontend/package.json")
data = json.loads(pkg.read_text())
data["version"] = "${NEW}"
pkg.write_text(json.dumps(data, indent=2) + "\n")
PY

# Rotate CHANGELOG [Unreleased] -> [NEW] - <date>.
TODAY="$(date +%Y-%m-%d)"
python3 - <<PY
import pathlib, re
path = pathlib.Path("CHANGELOG.md")
text = path.read_text()
text = re.sub(
    r"## \[Unreleased\]",
    f"## [Unreleased]\n\n## [{'${NEW}'}] - {'${TODAY}'}",
    text,
    count=1,
)
text += f"[{'${NEW}'}]: https://github.com/truongqv12/ntd_audio/releases/tag/v{'${NEW}'}\n"
path.write_text(text)
PY

git add backend/VERSION frontend/package.json CHANGELOG.md
git commit -m "release: v${NEW}"
git tag "v${NEW}"

echo
echo "Done. Next steps:"
echo "  git push origin HEAD --tags"
echo "  -> .github/workflows/release.yml will create the GitHub release."

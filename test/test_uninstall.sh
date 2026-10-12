#!/usr/bin/env bash
# Dependency-light checks for uninstall entrypoint: never remove anything in dry-run.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)

bash -n "$root/uninstall.sh"

home=$(mktemp -d)
trap 'rm -rf -- "$home"' EXIT
mkdir -p "$home/.config/frametop" "$home/.local/share/applications"
printf 'retain\n' > "$home/.config/frametop-layout.json"
printf 'retain\n' > "$home/.local/share/applications/deckard-nested-desktop.desktop"

output=$(HOME="$home" FRAME_LOCAL=1 bash "$root/uninstall.sh" --dry-run --purge --remove-build-container --remove-checkout)
grep -q 'DRY RUN' <<< "$output"
grep -q 'Dry run complete' <<< "$output"
test "$(cat "$home/.config/frametop-layout.json")" = retain
test "$(cat "$home/.local/share/applications/deckard-nested-desktop.desktop")" = retain

# Destructive extras require --purge, not a casual uninstall.
if HOME="$home" FRAME_LOCAL=1 bash "$root/uninstall.sh" --yes --remove-build-container >/dev/null 2>&1; then
  echo "ERROR: container removal accepted without --purge" >&2; exit 1
fi
if HOME="$home" FRAME_LOCAL=1 bash "$root/uninstall.sh" --yes --remove-checkout >/dev/null 2>&1; then
  echo "ERROR: checkout removal accepted without --purge" >&2; exit 1
fi
echo "uninstaller syntax, dry-run and guard tests passed"

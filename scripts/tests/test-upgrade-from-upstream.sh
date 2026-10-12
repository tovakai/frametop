#!/usr/bin/env bash
# Offline migration contract tests: no SteamVR, build or installer execution.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT

home="$tmp/home"
source_dir="$tmp/upstream"
core_dir="$tmp/core"
release_dir="$home/.local/share/frametop/releases/0.2.2"
entry="$home/.local/share/applications/deckard-nested-desktop.desktop"
mkdir -p "$home/.config" "$(dirname "$entry")" "$source_dir/session" \
  "$source_dir/scripts" "$core_dir/scripts" "$core_dir/docs" "$core_dir/screens" \
  "$release_dir/pack" "$release_dir/session"
cp "$root/upgrade-from-upstream.sh" "$core_dir/scripts/upgrade-from-upstream.sh"

for name in upstream core; do
  git -C "$tmp/$name" init -q
  git -C "$tmp/$name" config user.name test
  git -C "$tmp/$name" config user.email test@example.invalid
done
for file in "$source_dir/install.sh" "$source_dir/session/frametop-session.sh" \
  "$source_dir/scripts/_env.sh" "$core_dir/install.sh" \
  "$core_dir/docs/extensions.md" "$core_dir/screens/extension-motion.h"; do
  : > "$file"
done
for name in upstream core; do
  git -C "$tmp/$name" add .
  git -C "$tmp/$name" commit -qm 'test fixture'
done
git -C "$core_dir" remote add origin https://github.com/tovakai/frametop.git
git -C "$source_dir" remote add origin https://github.com/DeeJanuz/frametop.git

for file in "$release_dir/install.sh" "$release_dir/pack/release-box.sh" \
            "$release_dir/session/frametop-session.sh"; do
  : > "$file"
done
chmod +x "$release_dir/install.sh"
{
  printf 'VERSION=0.2.2\nCHANNEL=stable\n'
  printf 'IMAGE=localhost/frametop:0.2.2\nIMAGE_ID=%064d\nBOX=frametop-123456789abc\n' 0
} > "$release_dir/.frametop-release"
ln -sfn 0.2.2 "$home/.local/share/frametop/releases/current"
printf 'preserve me\n' > "$home/.config/frametop.conf"
export HOME="$home" FT_UPSTREAM_DIR="$source_dir" \
  FT_UPGRADE_BACKUP_ROOT="$home/backups"
command=(bash "$core_dir/scripts/upgrade-from-upstream.sh")
launcher() {
  printf 'Exec=%s/session/frametop-session.sh\n' "$1" > "$entry"
}

# Source checkout: the legacy DeeJanuz remote is supported.
launcher "$source_dir"
before=$(find "$home" -type f -printf '%P %s\n' | sort)
"${command[@]}" plan > "$tmp/plan.txt"
grep -q 'Active Steam Desktop launcher: upstream-source' "$tmp/plan.txt"
grep -q 'No plugin repository, plugin features or spatial-profile migration' "$tmp/plan.txt"
after=$(find "$home" -type f -printf '%P %s\n' | sort)
[[ "$before" == "$after" ]] || { echo 'source plan mutated user data' >&2; exit 1; }
git -C "$source_dir" remote set-url origin https://github.com/tovakai/frametop.git
if "${command[@]}" plan >/dev/null 2>&1; then
  echo 'non-upstream source not rejected' >&2; exit 1
fi
git -C "$source_dir" remote set-url origin https://github.com/DeeJanuz/frametop.git

# Release install: EXACT release is rollback target, even if a stale source
# checkout exists. The release version/manifest controls this, not ~/frametop.
launcher "$release_dir"
before=$(find "$home" -type f -printf '%P %s\n' | sort)
"${command[@]}" plan > "$tmp/release-plan.txt"
grep -q 'Active Steam Desktop launcher: upstream-release' "$tmp/release-plan.txt"
grep -q "Rollback installer: $release_dir/install.sh" "$tmp/release-plan.txt"
grep -q 'Release version: 0.2.2' "$tmp/release-plan.txt"
[[ "$(find "$home" -type f -printf '%P %s\n' | sort)" == "$before" ]] ||
  { echo 'release plan mutated user data' >&2; exit 1; }
# Link to 'current' is also supported; it resolves to the specific release.
launcher "$home/.local/share/frametop/releases/current"
"${command[@]}" plan > "$tmp/current-plan.txt"
grep -q "Rollback installer: $release_dir/install.sh" "$tmp/current-plan.txt"
launcher "$release_dir"

# Release requires NO ~/frametop source checkout and isn't confused by its remote.
mv "$source_dir" "$tmp/source-parked"
"${command[@]}" plan >/dev/null
mv "$tmp/source-parked" "$source_dir"

# Refuse unrelated installation and spoofed/malformed release metadata.
printf 'Exec=/tmp/another-desktop.sh\n' > "$entry"
if "${command[@]}" plan >/dev/null 2>&1; then
  echo 'unrelated active desktop not rejected' >&2; exit 1
fi
launcher "$release_dir"
sed -i 's/VERSION=0.2.2/VERSION=0.1.0/' "$release_dir/.frametop-release"
if "${command[@]}" plan >/dev/null 2>&1; then
  echo 'malformed release metadata not rejected' >&2; exit 1
fi
sed -i 's/VERSION=0.1.0/VERSION=0.2.2/' "$release_dir/.frametop-release"

# API-missing checkout, and unsafe in-place overwrite, are rejected.
rm -f "$core_dir/screens/extension-motion.h"
if "${command[@]}" plan >/dev/null 2>&1; then
  echo 'missing extension API not rejected' >&2; exit 1
fi
if FT_UPSTREAM_DIR="$core_dir" "${command[@]}" plan >/dev/null 2>&1; then
  echo 'in-place overwrite not rejected' >&2; exit 1
fi
printf 'upgrade-from-upstream.sh: offline source + release safety tests passed\n'

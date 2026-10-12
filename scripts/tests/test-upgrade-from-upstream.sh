#!/usr/bin/env bash
# Offline contract test with fake source trees. Never runs an installer.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT
mkdir -p "$tmp/home/.local/share/applications" "$tmp/home/.config" \
  "$tmp/upstream/session" "$tmp/upstream/scripts" "$tmp/core/scripts" \
  "$tmp/core/docs" "$tmp/core/screens"
cp "$root/upgrade-from-upstream.sh" "$tmp/core/scripts/upgrade-from-upstream.sh"
for name in upstream core; do
  git -C "$tmp/$name" init -q
  git -C "$tmp/$name" config user.name test
  git -C "$tmp/$name" config user.email test@example.invalid
done
for file in "$tmp/upstream/install.sh" "$tmp/upstream/session/frametop-session.sh" \
  "$tmp/upstream/scripts/_env.sh" "$tmp/core/install.sh" \
  "$tmp/core/docs/extensions.md" "$tmp/core/screens/extension-motion.h"; do
  : > "$file"
done
for name in upstream core; do
  git -C "$tmp/$name" add .
  git -C "$tmp/$name" commit -qm 'test fixture'
done
git -C "$tmp/core" remote add origin https://github.com/tovakai/frametop.git
git -C "$tmp/upstream" remote add origin https://github.com/Frametop/frametop.git
printf 'Exec=%s/session/frametop-session.sh\n' "$tmp/upstream" > \
  "$tmp/home/.local/share/applications/deckard-nested-desktop.desktop"
printf 'preserve me\n' > "$tmp/home/.config/frametop.conf"
export HOME="$tmp/home" FT_UPSTREAM_DIR="$tmp/upstream" \
  FT_UPGRADE_BACKUP_ROOT="$tmp/home/backups"
command=(bash "$tmp/core/scripts/upgrade-from-upstream.sh")
before=$(find "$tmp/home" -type f -printf '%P %s\n' | sort)
"${command[@]}" plan > "$tmp/plan.txt"
grep -q 'Active Steam Desktop launcher: upstream' "$tmp/plan.txt"
grep -q 'No plugin repository, features or spatial-profile migration' "$tmp/plan.txt"
current=$("${command[@]}" status)
[[ "$current" == *"Active Steam Desktop launcher: upstream"* ]]
after=$(find "$tmp/home" -type f -printf '%P %s\n' | sort)
[[ "$before" == "$after" ]] || { echo 'plan mutated user data' >&2; exit 1; }
git -C "$tmp/upstream" remote set-url origin https://github.com/tovakai/frametop.git
if "${command[@]}" plan >/dev/null 2>&1; then
  echo 'non-upstream installation not rejected' >&2; exit 1
fi
git -C "$tmp/upstream" remote set-url origin https://github.com/Frametop/frametop.git
rm -f "$tmp/core/screens/extension-motion.h"
if "${command[@]}" plan >/dev/null 2>&1; then
  echo 'missing extension API not rejected' >&2; exit 1
fi
if FT_UPSTREAM_DIR="$tmp/core" "${command[@]}" plan >/dev/null 2>&1; then
  echo 'in-place overwrite not rejected' >&2; exit 1
fi
printf 'upgrade-from-upstream.sh: offline checks passed\n'

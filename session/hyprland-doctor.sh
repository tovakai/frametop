#!/usr/bin/env bash
# Read-only diagnostics in Frametop's dev container. No package installation/VR.
set -euo pipefail
here=$(dirname "$(readlink -f "$0")")
if (( $# != 0 )); then
  echo "Usage: $0" >&2
  exit 2
fi
"$here/../scripts/in-box" sh -c '
  echo "Architecture: $(uname -m)"
  if [ -r /etc/os-release ]; then
    . /etc/os-release
    echo "Container: $PRETTY_NAME"
  fi
  failure=0
  for executable in Hyprland hyprctl dbus-run-session wayland-info; do
    if command -v "$executable" >/dev/null 2>&1; then
      echo "$executable: $(command -v "$executable")"
    else
      echo "$executable: MISSING" >&2
      failure=1
    fi
  done
  if command -v Hyprland >/dev/null 2>&1; then
    Hyprland --version | head -n 3 || true
  fi
  exit "$failure"
'

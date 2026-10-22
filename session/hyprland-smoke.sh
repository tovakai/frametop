#!/usr/bin/env bash
# Isolated protocol/output smoke-test: NO SteamVR panels, no running session changes.
# Runs ft-screens --no-vr on unique sockets and a temporary Hyprland session.
set -euo pipefail
here=$(dirname "$(readlink -f "$0")")
root=$(readlink -f "$here/..")
duration=${FT_HYPRLAND_SMOKE_SECONDS:-15}
count=${FT_SCREEN_COUNT:-1}
if ! [[ $duration =~ ^[0-9]+$ ]] || (( duration < 5 || duration > 60 )); then
  echo "frametop: smoke duration must be an integer 5..60 seconds" >&2
  exit 2
fi
if ! [[ $count =~ ^[1-9][0-9]*$ ]] || (( count > 4 )); then
  echo "frametop: smoke screen count must be 1..4" >&2
  exit 2
fi

if [ "${1:-}" = --inner ]; then
  if [[ ${WAYLAND_DISPLAY:-} != /* || ! -S $WAYLAND_DISPLAY ]]; then
    echo "frametop: smoke inner needs ft-screens' absolute Wayland socket" >&2
    exit 2
  fi
  # A fresh directory, config and state: no edits to either host or Frametop
  # profiles. Closing this child makes ft-screens terminate via SIGCHLD.
  # Check the actual advertised protocols before moving XDG_RUNTIME_DIR.
  # Aquamarine 0.15.1 binds these exact versions, not lower fallbacks.
  if ! command -v wayland-info >/dev/null 2>&1; then
    echo "frametop: wayland-info required for smoke protocol audit" >&2
    exit 1
  fi
  wayland-info | python3 "$here/hyprland-protocol-check.py"
  runtime=$(mktemp -d "${XDG_RUNTIME_DIR:?}/ft-hypr-smoke.XXXXXXXX")
  trap 'rm -rf -- "$runtime"' EXIT
  mkdir -p "$runtime/config" "$runtime/state"
  export XDG_RUNTIME_DIR="$runtime"
  export XDG_CONFIG_HOME="$runtime/config"
  export XDG_STATE_HOME="$runtime/state"
  export XDG_CURRENT_DESKTOP=Hyprland XDG_SESSION_TYPE=wayland XDG_SESSION_DESKTOP=Hyprland
  export HYPRLAND_NO_SD_VARS=1 HYPRLAND_NO_SD_NOTIFY=1 HYPRLAND_NO_SD_TARGET=1
  export FT_HYPRLAND_STARTUP="$here/hyprland-on-start.sh"
  config=${FT_HYPRLAND_CONFIG:-$here/hyprland-minimal.lua}
  echo "frametop: smoke running Hyprland for ${duration}s; safe timeout is expected" >&2
  if timeout --signal=TERM --kill-after=5s "${duration}s" dbus-run-session Hyprland -c "$config"; then
    exit 0
  else
    result=$?
    if (( result == 124 )); then
      echo "frametop: smoke finished at safety timeout (expected)" >&2
      exit 0
    fi
    exit "$result"
  fi
fi

if (( $# != 0 )); then
  echo "Usage: FT_SCREEN_COUNT=1 $0" >&2
  exit 2
fi
# No default ft_screens/ft-screens-0 sockets. Never kill another instance.
# This must be launched in the container with the branch's ft-screens build.
screens=()
for ((i = 0; i < count; i++)); do
  screens+=(--screen "1280x720@1.0")
done
sock="ft-hypr-smoke-$$"
ctl="ft_hypr_smoke_$$"
echo "frametop: isolated --no-vr smoke; socket $sock, control $ctl, $count output(s)" >&2
"$root/scripts/in-box" "$root/screens/build/ft-screens" --no-vr \
  --socket "$sock" --control "$ctl" "${screens[@]}" -- env FT_SCREEN_COUNT="$count" FT_HYPRLAND_SMOKE_SECONDS="$duration" "$0" --inner

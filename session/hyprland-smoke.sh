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
  # Hyprland's socket is $XDG_RUNTIME_DIR/hypr/<abi signature>/.socket2.sock.
  # sun_path holds 108 bytes; nesting it under the user runtime directory overflows it and
  # Hyprland turns IPC off, so startup cannot add outputs.
  runtime=$(mktemp -d /tmp/ftH.XXXXXX)
  trap 'rm -rf -- "$runtime"' EXIT
  mkdir -p "$runtime/config" "$runtime/state"
  export XDG_RUNTIME_DIR="$runtime"
  export XDG_CONFIG_HOME="$runtime/config"
  export XDG_STATE_HOME="$runtime/state"
  export XDG_CURRENT_DESKTOP=Hyprland XDG_SESSION_TYPE=wayland XDG_SESSION_DESKTOP=Hyprland
  export HYPRLAND_NO_SD_VARS=1 HYPRLAND_NO_SD_NOTIFY=1 HYPRLAND_NO_SD_TARGET=1
  export FT_HYPRLAND_STARTUP="$here/hyprland-on-start.sh"
  # shellcheck disable=SC1091
  . "$here/hyprland-env.sh"
  frametop_prepend_aquamarine "$root"
  config=${FT_HYPRLAND_CONFIG:-$here/hyprland-minimal.lua}
  echo "frametop: smoke running Hyprland for ${duration}s; safe timeout is expected" >&2
  # Sample commits while Hyprland is still mapped. A query after it exits sees
  # no toplevels: destroying the client closes them before this script continues.
  if [ -n "${FT_HYPR_CONTROL:-}" ]; then
    (
      sleep $((duration - 2))
      python3 - "$FT_HYPR_CONTROL" << 'PY'
import socket, sys
sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
sock.bind("")
sock.settimeout(2)
sock.sendto(b"toplevels", b"\0" + sys.argv[1].encode())
text = sock.recv(8192).decode()
sys.stdout.write(text if text.endswith("\n") else text + "\n")
PY
    ) &
    query=$!
  fi
  set +e
  timeout --signal=TERM --kill-after=5s "${duration}s" dbus-run-session Hyprland -c "$config"
  result=$?
  set -e
  if [ -n "${query:-}" ]; then
    wait "$query" || true
  fi
  logf=$(find "$runtime" -name hyprland.log -print -quit 2>/dev/null || true)
  if [ -n "$logf" ]; then
    echo "frametop: hyprland log excerpts"
    grep -E "ERR|error|Output |failed|dmabuf|DMA" "$logf" | head -80 || true
  fi
  if (( result == 124 )); then
    echo "frametop: smoke finished at safety timeout (expected)" >&2
    exit 0
  fi
  exit "$result"
fi

if (( $# != 0 )); then
  echo "Usage: FT_SCREEN_COUNT=1 $0" >&2
  exit 2
fi
# No default ft_screens/ft-screens-0 sockets. Never kill another instance.
# This must be launched in the container with the branch's ft-screens build.
# A timeout alone is not success: Aquamarine can stay up after wlroots rejects
# its first buffer, and ft-screens exits 0 when that child ends.
width=1280
height=720
screens=()
for ((i = 0; i < count; i++)); do
  screens+=(--screen "${width}x${height}@1.0")
done
sock="ft-hypr-smoke-$$"
ctl="ft_hypr_smoke_$$"
echo "frametop: isolated --no-vr smoke; socket $sock, control $ctl, $count output(s)" >&2
log=$(mktemp)
trap 'rm -f "$log"' EXIT
set +e
"$root/scripts/in-box" "$root/screens/build/ft-screens" --no-vr \
  --socket "$sock" --control "$ctl" "${screens[@]}" -- env FT_SCREEN_COUNT="$count" FT_HYPR_CONTROL="$ctl" FT_HYPRLAND_SMOKE_SECONDS="$duration" "$0" --inner \
  >"$log" 2>&1
status=$?
set -e
cat "$log" >&2
errors=0
if (( status != 0 )); then
  echo "frametop: smoke process exited $status" >&2
  errors=1
fi
if ! grep -F "Frametop Wayland protocol version preflight: PASS" "$log" >/dev/null; then
  echo "frametop: smoke missing protocol preflight pass" >&2
  errors=1
fi
if grep -F "error in client communication" "$log" >/dev/null; then
  echo "frametop: smoke saw a Wayland client error" >&2
  errors=1
fi
for ((i = 1; i <= count; i++)); do
  if ! grep -E "^${i} ${width}x${height} [1-9][0-9]* " "$log" >/dev/null; then
    echo "frametop: smoke missing a mapped ${width}x${height} commit for screen $i" >&2
    errors=1
  fi
done
exit "$errors"

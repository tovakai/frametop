#!/usr/bin/env bash
# Stop Plasma's VR compositor only: ft-screens on ft-screens-0.
# A Hyprland panel on ft-hyprland-0 is left running. Does not touch kded6,
# gamescope, or SteamVR.
set -euo pipefail
echo "frametop: stopping Plasma VR screens (socket ft-screens-0)" >&2
for pid in /proc/[0-9]*; do
  pid=${pid#/proc/}
  [[ $pid =~ ^[0-9]+$ ]] || continue
  [ -r "/proc/$pid/cmdline" ] || continue
  cmd=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)
  case $cmd in
    *"ft-screens --socket ft-screens-0"*) kill "$pid" 2>/dev/null || true ;;
  esac
done

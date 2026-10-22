#!/usr/bin/env bash
# Stop the experimental Hyprland VR session started by frametop-session.sh.
# Kills only ft-screens bound to ft-hyprland-0 and Hyprland using this tree's
# minimal config. Other ft-screens processes are left running.
set -euo pipefail
here=$(dirname "$(readlink -f "$0")")
root=$(readlink -f "$here/..")
# shellcheck disable=SC1091
. "$here/hyprland-env.sh"
echo "frametop: stopping experimental Hyprland session (socket $FT_HYPRLAND_SOCKET)" >&2
frametop_stop_hyprland_session "$root" "$FT_HYPRLAND_SOCKET"

#!/usr/bin/env bash
# Stop whichever Frametop VR desktop is up. Scoped to its compositor socket.
# Does not signal every compositor, and does not clear the input relay's
# stored file descriptors.
set -euo pipefail
here=$(dirname "$(readlink -f "$0")")
systemctl --user stop frametop-desktop 2>/dev/null || true
"$here/hyprland-stop.sh" || true
"$here/plasma-stop.sh" || true
# gamescope backend only. The bracket keeps this shell from matching itself.
pkill -f '[v]r-overlay-key frametop ' 2>/dev/null || true

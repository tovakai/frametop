#!/usr/bin/env bash
# Stop whichever Frametop VR desktop is up. Scoped to its compositor socket.
# Does not signal every compositor, and does not clear the input relay's
# stored file descriptors.
set -euo pipefail
here=$(dirname "$(readlink -f "$0")")
systemctl --user stop frametop-desktop 2>/dev/null || true
"$here/hyprland-stop.sh" || true
"$here/plasma-stop.sh" || true
# The installed Plasma session's exit handler signals every compositor with
# this program name. Wait until that script has exited before returning, so a
# desktop that starts next is not caught by it.
for _ in $(seq 1 40); do
  pgrep -f '[/]frametop-api/session/frametop-session.sh' >/dev/null || break
  sleep 0.2
done
# gamescope backend only. The bracket keeps this shell from matching itself.
pkill -f '[v]r-overlay-key frametop ' 2>/dev/null || true

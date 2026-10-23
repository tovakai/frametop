#!/usr/bin/env bash
# SteamVR's Desktop button, and the SSH commands that choose it.
#   frametop-desktop                 launch the selected desktop (Steam runs this)
#   frametop-desktop status
#   frametop-desktop use hyprland|plasma
#   frametop-desktop rollback
#
# Hyprland is a pinned tree under ~/.local/share/frametop/hyprland-desktop.
# Plasma is always /home/steamos/frametop-api, which this script does not modify.
set -euo pipefail
here=$(dirname "$(readlink -f "$0")")
# Installed copy lives in ~/.local/bin. The repo copy finds the pin beside itself
# only when it is still inside a hyprland-desktop tree; otherwise use the pin.
home=${HOME:?}
pin=$home/.local/share/frametop/hyprland-desktop
selection_file=$home/.config/frametop/desktop-selection
plasma_session=${FT_PLASMA_SESSION:-$home/frametop-api/session/frametop-session.sh}
export XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}
export DBUS_SESSION_BUS_ADDRESS=${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}

current_root() {
  if [ -L "$pin/current" ] || [ -d "$pin/current" ]; then
    readlink -f "$pin/current"
    return
  fi
  if [ -x "$here/frametop-session.sh" ]; then
    readlink -f "$here/.."
    return
  fi
  echo ""
}

selection() {
  local value
  value=$(cat "$selection_file" 2>/dev/null || true)
  case $value in
    hyprland|plasma) printf '%s\n' "$value" ;;
    *) printf '%s\n' hyprland ;;
  esac
}

launch_hyprland() {
  local root
  root=$(current_root)
  if [ -z "$root" ] || [ ! -x "$root/session/frametop-session.sh" ]; then
    echo "frametop: Hyprland desktop is not installed (missing $pin/current)" >&2
    echo "frametop: Plasma is still $plasma_session" >&2
    exit 1
  fi
  if [ -d "$pin/config/quickshell/ii" ]; then
    export FT_USER_CONFIG_HOME=$pin/config
  fi
  export FT_DESKTOP_SESSION=hyprland
  exec "$root/session/frametop-session.sh"
}

launch_plasma() {
  local root
  root=$(current_root)
  if [ -n "$root" ] && [ -x "$root/session/hyprland-stop.sh" ]; then
    "$root/session/hyprland-stop.sh" || true
  fi
  if [ ! -x "$plasma_session" ]; then
    echo "frametop: Plasma session is missing: $plasma_session" >&2
    exit 1
  fi
  export FT_DESKTOP_SESSION=plasma
  exec "$plasma_session"
}

status() {
  local root sel relay fds
  sel=$(selection)
  root=$(current_root)
  echo "selection: $sel"
  echo "hyprland: ${root:-not installed}"
  if [ -n "$root" ] && [ -f "$root/VERSION" ]; then
    sed 's/^/  /' "$root/VERSION"
  fi
  echo "plasma: $plasma_session"
  if [ -x "$plasma_session" ]; then echo "plasma session: present"; else echo "plasma session: MISSING"; fi
  relay=$(systemctl --user is-active frametop-input-relay.service 2>/dev/null || true)
  fds=$(systemctl --user show -p NFileDescriptorStore --value frametop-input-relay.service 2>/dev/null || true)
  echo "input relay: ${relay:-unknown}  fdstore: ${fds:-unknown}"
  if pgrep -f '[f]t-screens --socket ft-hyprland-0' >/dev/null; then
    echo "running: hyprland"
  elif pgrep -f '[f]t-screens --socket ft-screens-0' >/dev/null; then
    echo "running: plasma"
  else
    echo "running: none"
  fi
  echo "desktop entry:"
  grep '^Exec=' "$home/.local/share/applications/deckard-nested-desktop.desktop" 2>/dev/null || echo "  (not installed)"
  echo "plasma entry:"
  grep '^Exec=' "$home/.local/share/applications/frametop-plasma-desktop.desktop" 2>/dev/null || echo "  (not installed)"
}

start_unit() {
  local desktop=$1 root session
  root=$(current_root)
  systemctl --user reset-failed frametop-desktop 2>/dev/null || true
  if [ "$desktop" = hyprland ]; then
    session=$root/session/frametop-session.sh
    [ -n "$root" ] && [ -x "$session" ] || { echo "frametop: Hyprland is not installed" >&2; return 1; }
    systemd-run --user --collect --quiet --unit frametop-desktop \
      --setenv=FT_DESKTOP_SESSION=hyprland \
      ${FT_USER_CONFIG_HOME:+--setenv=FT_USER_CONFIG_HOME=$FT_USER_CONFIG_HOME} \
      "$session"
  else
    [ -x "$plasma_session" ] || { echo "frametop: Plasma session is missing" >&2; return 1; }
    systemd-run --user --collect --quiet --unit frametop-desktop \
      --setenv=FT_DESKTOP_SESSION=plasma \
      "$plasma_session"
  fi
}

use_desktop() {
  local desktop=$1 root
  case $desktop in
    hyprland|plasma) ;;
    *) echo "usage: frametop-desktop use hyprland|plasma" >&2; exit 2 ;;
  esac
  mkdir -p "$(dirname "$selection_file")"
  printf '%s\n' "$desktop" > "$selection_file"
  root=$(current_root)
  if [ -n "$root" ] && [ -x "$root/session/desktop-stop.sh" ]; then
    "$root/session/desktop-stop.sh" || true
  fi
  sleep 1
  if [ "$desktop" = hyprland ] && [ -d "$pin/config/quickshell/ii" ]; then
    export FT_USER_CONFIG_HOME=$pin/config
  fi
  start_unit "$desktop"
  echo "frametop: selected $desktop"
}

rollback() {
  local restore=$pin/rollback/latest/restore.sh
  if [ ! -x "$restore" ]; then
    echo "frametop: no rollback snapshot at $restore" >&2
    exit 1
  fi
  exec "$restore"
}

# The Plasma library entry is this file under another name, so it cannot follow
# the Hyprland selection by mistake.
if [ "$(basename "$0")" = frametop-plasma ]; then
  launch_plasma
fi

case ${1:-launch} in
  launch)
    case $(selection) in
      plasma) launch_plasma ;;
      *) launch_hyprland ;;
    esac ;;
  status) status ;;
  use) use_desktop "${2:-}" ;;
  rollback) rollback ;;
  *) echo "usage: frametop-desktop [status | use hyprland|plasma | rollback]" >&2; exit 2 ;;
esac

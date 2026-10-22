#!/usr/bin/env bash
# Experimental nested Hyprland session. Invoked only by frametop-session.sh --inner.
# Keep everything Hyprland-specific here, rather than changing the working KWin path.
set -euo pipefail
here=$(dirname "$(readlink -f "$0")")

# ft-screens is the Wayland parent, not a physical DRM/KMS device. The absolute
# path stays valid after we give Hyprland its own XDG_RUNTIME_DIR for its sockets.
parent_wayland=${WAYLAND_DISPLAY:-}
if [[ $parent_wayland != /* || ! -S $parent_wayland ]]; then
  echo "frametop: Hyprland needs the absolute ft-screens Wayland socket" >&2
  exit 2
fi

count=${FT_SCREEN_COUNT:-1}
if ! [[ $count =~ ^[1-9][0-9]*$ ]] || (( count > 24 )); then
  echo "frametop: invalid FT_SCREEN_COUNT: $count" >&2
  exit 2
fi

config=${FT_HYPRLAND_CONFIG:-$here/hyprland-minimal.lua}
if [ ! -f "$config" ]; then
  echo "frametop: Hyprland configuration not found: $config" >&2
  exit 2
fi

# Host is immutable SteamOS; source builds and optional Hyprland installation
# live in the Fedora dev container. in-box starts that container before entering
# it, so do not change the wrapper's own runtime before calling it.
host_runtime=${XDG_RUNTIME_DIR:?}
# Per-launch private runtime (no chance to delete another nested session's sockets).
runtime=$(mktemp -d "$host_runtime/frametop-hyprland.XXXXXXXX")
cleanup() { rm -rf -- "$runtime"; }
trap cleanup EXIT
mkdir -p "$HOME/.config/frametop/hyprland" "$HOME/.local/state/frametop/hyprland"

# Disabling Hyprland's systemd/DBus activation-environment imports prevents the
# nested compositor from redirecting SteamOS's own services into this session.
# dbus-run-session runs *inside* the container with the isolated session's env.
# We intentionally don't start Quickshell, portals, hypridle or other agents yet.
echo "frametop: starting experimental nested Hyprland ($count panel(s))" >&2
"$here/../scripts/in-box" env -u HYPRLAND_INSTANCE_SIGNATURE \
  XDG_RUNTIME_DIR="$runtime" \
  WAYLAND_DISPLAY="$parent_wayland" \
  XDG_CONFIG_HOME="$HOME/.config/frametop/hyprland" \
  XDG_STATE_HOME="$HOME/.local/state/frametop/hyprland" \
  XDG_CURRENT_DESKTOP=Hyprland \
  XDG_SESSION_DESKTOP=Hyprland \
  XDG_SESSION_TYPE=wayland \
  HYPRLAND_NO_SD_VARS=1 \
  HYPRLAND_NO_SD_NOTIFY=1 \
  HYPRLAND_NO_SD_TARGET=1 \
  FT_SCREEN_COUNT="$count" \
  FT_HYPRLAND_STARTUP="$here/hyprland-on-start.sh" \
  dbus-run-session Hyprland -c "$config"

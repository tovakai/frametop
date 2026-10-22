#!/usr/bin/env bash
# One desktop action for a controller chord or for a test.
# The host relay runs this script. Hyprland, qs, and the apps live in the
# Fedora container, so the first step only reads the session route and
# re-enters there. The route names one runtime directory.
set -euo pipefail
here=$(dirname "$(readlink -f "$0")")
action=${1:-}

run_app() {
  local cmd=$1
  if [ "${FT_DESKTOP_FOREGROUND:-}" = 1 ]; then
    # shellcheck disable=SC2086
    ${cmd}
    return
  fi
  # shellcheck disable=SC2086
  ${cmd} &
}

launch_first() {
  local user_script=${XDG_CONFIG_HOME:-}/hypr/hyprland/scripts/launch_first_available.sh
  if [ -x "$user_script" ]; then
    if [ "${FT_DESKTOP_FOREGROUND:-}" = 1 ]; then
      "$user_script" "$@"
    else
      "$user_script" "$@" &
    fi
    return
  fi
  local cmd
  for cmd in "$@"; do
    [ -n "$cmd" ] || continue
    # shellcheck disable=SC2086
    command -v ${cmd%% *} >/dev/null 2>&1 || continue
    run_app "$cmd"
    return
  done
  echo "frametop: none of these commands are installed: $*" >&2
}

if [ "${FT_DESKTOP_INNER:-}" != 1 ]; then
  route=${FT_HYPR_ROUTE:-${XDG_RUNTIME_DIR:-}/frametop-hyprland.route}
  if [ ! -f "$route" ]; then
    echo "frametop: no experimental Hyprland session route ($route)" >&2
    exit 2
  fi
  exported=$(python3 "$here/../input/desktop_route.py" --export "$route") || exit $?
  # shellcheck disable=SC1090
  eval "$exported"
  runner=$here/../scripts/in-box
  if [ -n "${FT_DESKTOP_RUNNER:-}" ]; then
    runner=$FT_DESKTOP_RUNNER
  fi
  exec "$runner" env \
    XDG_RUNTIME_DIR="$FT_ROUTE_RUNTIME" \
    HYPRLAND_INSTANCE_SIGNATURE="$FT_ROUTE_SIGNATURE" \
    XDG_CONFIG_HOME="$FT_ROUTE_CONFIG_HOME" \
    WAYLAND_DISPLAY="$FT_ROUTE_WAYLAND" \
    FT_DESKTOP_INNER=1 \
    "$0" "$action"
fi

case $action in
  workspace-prev) hyprctl dispatch workspace r-1 ;;
  workspace-next) hyprctl dispatch workspace r+1 ;;
  window-prev) hyprctl dispatch movetoworkspacesilent r-1 ;;
  window-next) hyprctl dispatch movetoworkspacesilent r+1 ;;
  close) hyprctl dispatch closewindow ;;
  terminal)
    launch_first foot kitty alacritty wezterm konsole kgx uxterm xterm
    ;;
  files)
    launch_first dolphin nautilus nemo thunar "kitty -1 fish -c yazi"
    ;;
  browser)
    launch_first google-chrome-stable zen-browser firefox brave chromium microsoft-edge-stable opera librewolf
    ;;
  launcher)
    if ! command -v qs >/dev/null 2>&1; then
      echo "frametop: qs is not installed; the end-4 launcher was not opened" >&2
      exit 0
    fi
    qs -c "${FT_QS_CONFIG:-ii}" ipc --any-display call search toggle
    ;;
  *)
    echo "frametop: unknown desktop action: ${action:-<none>}" >&2
    exit 2
    ;;
esac

#!/usr/bin/env bash
# One desktop action for a controller chord or for a test.
# Workspace changes show that workspace. Window moves use the silent dispatch,
# so the view stays where it is. Close is one closewindow request.
# App choices match ~/.config/hypr/hyprland/variables.lua on the reference laptop.
set -euo pipefail
here=$(dirname "$(readlink -f "$0")")
action=${1:-}
runtime=${FT_HYPR_RUNTIME:-}
if [ -z "$runtime" ]; then
  set +e
  runtime=$(ls -d /tmp/ftH.* 2>/dev/null | head -n 1)
  set -e
fi
config_home=${FT_USER_CONFIG_HOME:-$HOME/.config}
qs_config=${FT_QS_CONFIG:-ii}

run_in_hyprland() {
  if [ -n "${runtime:-}" ] && [ -d "$runtime/hypr" ]; then
    local sig
    sig=$(find "$runtime/hypr" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | head -n 1)
    if [ -n "$sig" ]; then
      export XDG_RUNTIME_DIR=$runtime HYPRLAND_INSTANCE_SIGNATURE=$sig
    fi
  fi
  if command -v hyprctl >/dev/null 2>&1; then
    hyprctl "$@"
    return
  fi
  "$here/../scripts/in-box" hyprctl "$@"
}

launch_first() {
  local user_script=$config_home/hypr/hyprland/scripts/launch_first_available.sh
  if [ -x "$user_script" ]; then
    "$user_script" "$@"
    return
  fi
  local cmd
  for cmd in "$@"; do
    [ -n "$cmd" ] || continue
    # shellcheck disable=SC2086
    command -v ${cmd%% *} >/dev/null 2>&1 || continue
    # shellcheck disable=SC2086
    ${cmd} &
    return
  done
  echo "frametop: none of these commands are installed: $*" >&2
}

case $action in
  workspace-prev) run_in_hyprland dispatch workspace r-1 ;;
  workspace-next) run_in_hyprland dispatch workspace r+1 ;;
  window-prev) run_in_hyprland dispatch movetoworkspacesilent r-1 ;;
  window-next) run_in_hyprland dispatch movetoworkspacesilent r+1 ;;
  close) run_in_hyprland dispatch closewindow ;;
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
    export XDG_CONFIG_HOME=$config_home
    if [ -n "${runtime:-}" ]; then
      export XDG_RUNTIME_DIR=$runtime
    fi
    if ! command -v qs >/dev/null 2>&1; then
      echo "frametop: qs is not installed; the end-4 launcher was not opened" >&2
      exit 0
    fi
    qs -c "$qs_config" ipc call search toggle
    ;;
  *)
    echo "frametop: unknown desktop action: ${action:-<none>}" >&2
    exit 2
    ;;
esac

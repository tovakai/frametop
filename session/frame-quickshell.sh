#!/usr/bin/env bash
# Start the existing end-4 Quickshell. A missing binary or config exits 0 so
# Hyprland keeps running. This process is not the compositor.
set -u
here=$(dirname "$(readlink -f "$0")")
cfg=${FT_QS_CONFIG:-ii}
config_home=${FT_USER_CONFIG_HOME:-$HOME/.config}
shell=$config_home/quickshell/$cfg/shell.qml
export XDG_CONFIG_HOME=$config_home
if [ -f "$shell" ] && [ -x "$here/frame-theme.sh" ]; then
  theme_env=$("$here/frame-theme.sh" "$config_home" || true)
  if [ -n "${theme_env:-}" ]; then
    # shellcheck disable=SC2086
    eval "$theme_env"
    if [ -n "${FONTCONFIG_FILE:-}" ]; then
      export FONTCONFIG_FILE
    fi
  fi
fi
if ! command -v qs >/dev/null 2>&1; then
  echo "frametop: qs is not installed; continuing without Quickshell" >&2
  exit 0
fi
if [ ! -f "$shell" ]; then
  echo "frametop: Quickshell config $shell is not on this machine; continuing without it" >&2
  exit 0
fi
if [ -n "${FT_QS_LOG:-}" ]; then
  exec qs -c "$cfg" >"$FT_QS_LOG" 2>&1
fi
exec qs -c "$cfg"

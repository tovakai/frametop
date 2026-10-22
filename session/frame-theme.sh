#!/usr/bin/env bash
# Point the staged end-4 shell at its colors, wallpaper, and fonts.
# Writes only the stage copy and this session's state directory.
set -eu
config_home=${1:-${FT_USER_CONFIG_HOME:-$HOME/.config}}
theme=$(readlink -f "$config_home/../theme" 2>/dev/null || true)
state_root=${XDG_STATE_HOME:-$HOME/.local/state}
qs_state=$state_root/quickshell
if [ -n "${theme:-}" ] && [ -d "$theme/quickshell" ] && [ ! -f "$qs_state/user/generated/colors.json" ]; then
  mkdir -p "$qs_state"
  cp -a "$theme/quickshell/." "$qs_state/"
fi
wall=${theme:-}/wallpaper.png
if [ -n "${theme:-}" ] && [ -f "$wall" ]; then
  python3 - "$config_home/illogical-impulse/config.json" "$qs_state/user/generated/wallpaper/path.txt" "$wall" <<'PY'
import json
import pathlib
import sys

cfg, path_txt, wall = map(pathlib.Path, sys.argv[1:])
if cfg.is_file():
    data = json.loads(cfg.read_text(encoding="utf-8"))
    data.setdefault("background", {})["wallpaperPath"] = str(wall)
    cfg.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
path_txt.parent.mkdir(parents=True, exist_ok=True)
path_txt.write_text(str(wall) + "\n", encoding="utf-8")
PY
fi
gtk=$config_home/gtk-3.0
mkdir -p "$gtk"
if [ ! -f "$gtk/settings.ini" ]; then
  printf '%s\n' '[Settings]' 'gtk-icon-theme-name=breeze' >"$gtk/settings.ini"
fi
if [ -n "${theme:-}" ] && [ -d "$theme/fonts" ]; then
  conf=${XDG_RUNTIME_DIR:-/tmp}/frametop-fonts.conf
  cat >"$conf" <<EOF
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>
  <dir>$theme/fonts</dir>
</fontconfig>
EOF
  printf 'FONTCONFIG_FILE=%q\n' "$conf"
fi

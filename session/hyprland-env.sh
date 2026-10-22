#!/usr/bin/env bash
# Shared by the experimental session and the no-VR smoke harness.
# Aquamarine 0.15.1 (the COPR build Hyprland 0.56.2 links) flushes a buffer from
# xdg_toplevel.configure, before xdg_surface.ack_configure. wlroots then posts
# xdg_surface error 3. session/build-aquamarine.sh installs the upstream fix
# (hyprwm/aquamarine 7bb8bdf, "wayland: fix configure not applying sometimes")
# into build/aquamarine without replacing the COPR library.

frametop_prepend_aquamarine() {
  local root=$1 dir
  if [ -n "${FT_AQUAMARINE_LIBDIR:-}" ]; then
    dir=$FT_AQUAMARINE_LIBDIR
    if [ ! -e "$dir/libaquamarine.so.14" ]; then
      echo "frametop: FT_AQUAMARINE_LIBDIR has no libaquamarine.so.14: $dir" >&2
      return 1
    fi
  else
    dir=
    for dir in "$root/build/aquamarine/lib64" "$root/build/aquamarine/lib"; do
      [ -e "$dir/libaquamarine.so.14" ] && break
      dir=
    done
    if [ -z "$dir" ]; then
      echo "frametop: patched aquamarine is not built (session/build-aquamarine.sh)" >&2
      return 1
    fi
  fi
  case :${LD_LIBRARY_PATH:-}: in
    *:"$dir":*) ;;
    *) export LD_LIBRARY_PATH="$dir${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ;;
  esac
  echo "frametop: using patched aquamarine ($dir)" >&2
}

# Experimental VR launch. One 1280x720 panel on its own sockets, never the
# saved Plasma layout (ft-layout screen-args) and never FT_SCREEN_COUNT from it.
FT_HYPRLAND_SOCKET=ft-hyprland-0
FT_HYPRLAND_CONTROL=ft_hyprland
FT_HYPRLAND_SCREEN=1280x720@1.0

frametop_hyprland_require_one_panel() {
  if [ -n "${FT_SCREEN_COUNT:-}" ] && [ "$FT_SCREEN_COUNT" != 1 ]; then
    echo "frametop: experimental Hyprland VR session is one panel; refusing FT_SCREEN_COUNT=$FT_SCREEN_COUNT" >&2
    return 2
  fi
  export FT_SCREEN_COUNT=1
}

# True when this command line is the experimental ft-screens, not another one.
frametop_cmdline_is_hyprland_screens() {
  local cmd=$1 socket=$2
  case $cmd in
    *"ft-screens --socket ${socket} "*|*"ft-screens --socket ${socket}") return 0 ;;
    *) return 1 ;;
  esac
}

# Stop this experimental session only. $1 is the repo root (for Hyprland's
# config path), $2 the Wayland socket name, $3 the optional in-box wrapper pid.
# Never uses pkill -x ft-screens.
frametop_stop_hyprland_session() {
  local root=$1 socket=$2 wrapper=${3:-} pid cmd
  local config=$root/session/hyprland-minimal.lua
  for pid in /proc/[0-9]*; do
    pid=${pid#/proc/}
    [[ $pid =~ ^[0-9]+$ ]] || continue
    [ -r "/proc/$pid/cmdline" ] || continue
    cmd=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)
    [ -n "$cmd" ] || continue
    if frametop_cmdline_is_hyprland_screens "$cmd" "$socket" ||
       [[ $cmd == *"Hyprland -c ${config}"* ]]; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  if [ -n "$wrapper" ]; then
    kill "$wrapper" 2>/dev/null || true
    local _
    for _ in 1 2 3 4 5 6 7 8 9 10; do
      kill -0 "$wrapper" 2>/dev/null || return 0
      sleep 0.1
    done
    kill -KILL "$wrapper" 2>/dev/null || true
  fi
}

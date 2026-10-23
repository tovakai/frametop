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

# Experimental VR launch. Its own sockets, never the saved Plasma layout
# (ft-layout screen-args). The default panel is still 1920x1080 at 1.5 m.
FT_HYPRLAND_SOCKET=${FT_HYPRLAND_SOCKET:-ft-hyprland-0}
FT_HYPRLAND_CONTROL=${FT_HYPRLAND_CONTROL:-ft_hyprland}
FT_HYPRLAND_SCREEN=${FT_HYPRLAND_SCREEN:-1920x1080@1.5}

# Host-side description of the one nested session. The relay and
# frame-desktop-action.sh read it; they do not search /tmp/ftH.*.
frametop_hyprland_route_path() {
  if [ -n "${FT_HYPR_ROUTE:-}" ]; then
    printf '%s\n' "$FT_HYPR_ROUTE"
    return
  fi
  printf '%s/%s\n' "${XDG_RUNTIME_DIR:?}" frametop-hyprland.route
}

frametop_hyprland_route_begin() {
  local runtime=$1 wayland=$2 config_home=$3 path tmp
  path=$(frametop_hyprland_route_path)
  umask 077
  tmp=$(mktemp "${path}.XXXXXX")
  cat > "$tmp" <<EOF
pid=$$
control=$FT_HYPRLAND_CONTROL
runtime=$runtime
wayland=$wayland
config_home=$config_home
EOF
  mv -f "$tmp" "$path"
}

frametop_hyprland_route_end() {
  local path
  path=$(frametop_hyprland_route_path)
  rm -f -- "$path"
}

# How many panels this launch will open. Unset means one, the current
# 1920x1080 panel. The layout file (when the session asks for it) can raise
# the count. 0 and anything above the compositor's slot table are refused.
frametop_hyprland_prepare_screens() {
  local count=${FT_SCREEN_COUNT:-1}
  if ! [[ $count =~ ^[1-9][0-9]*$ ]] || (( count > 24 )); then
    echo "frametop: invalid FT_SCREEN_COUNT=$count" >&2
    return 2
  fi
  export FT_SCREEN_COUNT=$count
  export FT_HYPR_OUTPUTS=${FT_HYPR_OUTPUTS:-$count}
  export FT_OUTPUT_NAMES=1
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
# Never kills every compositor by process name.
frametop_stop_hyprland_session() {
  local root=$1 socket=$2 wrapper=${3:-} pid cmd frametop_stop_pids=
  local session_dir=$root/session/
  frametop_hyprland_route_end || true
  for pid in /proc/[0-9]*; do
    pid=${pid#/proc/}
    [[ $pid =~ ^[0-9]+$ ]] || continue
    [ -r "/proc/$pid/cmdline" ] || continue
    cmd=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)
    [ -n "$cmd" ] || continue
    # Match this checkout's session path. A bare program name would also
    # match the installed pin, which is a different tree.
    if frametop_cmdline_is_hyprland_screens "$cmd" "$socket" ||
       [[ $cmd == *"${session_dir}"* ]]; then
      kill "$pid" 2>/dev/null || true
      frametop_stop_pids="${frametop_stop_pids} $pid"
    fi
  done
  # Quickshell's command line has no session path. Stop children of a
  # process this session already matched, and leave any other shell.
  if [ -n "${frametop_stop_pids}" ]; then
    for pid in /proc/[0-9]*; do
      pid=${pid#/proc/}
      [[ $pid =~ ^[0-9]+$ ]] || continue
      [ -r "/proc/$pid/stat" ] || continue
      local ppid
      ppid=$(sed -n 's/.*) [^ ]* //p' "/proc/$pid/stat" | awk '{print $1}')
      for root in $frametop_stop_pids; do
        if [ "$ppid" = "$root" ]; then
          kill "$pid" 2>/dev/null || true
        fi
      done
    done
  fi
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

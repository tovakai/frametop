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

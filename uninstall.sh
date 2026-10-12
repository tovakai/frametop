#!/usr/bin/env bash
# Uninstall Frametop on the Steam Frame or from a PC over SSH.
# --purge deletes personal data. Shared build tools are opt-in.
set -euo pipefail
root=$(cd "$(dirname "$0")" && pwd)
previous_runtime=$(printenv XDG_RUNTIME_DIR || true)
. "$root/scripts/_env.sh"

purge=0 remove_container=0 remove_checkout=0 assume_yes=0 dry_run=0
for arg in "$@"; do
  case "$arg" in
    --purge) purge=1 ;;
    --remove-build-container) remove_container=1 ;;
    --remove-checkout) remove_checkout=1 ;;
    --yes) assume_yes=1 ;;
    --dry-run) dry_run=1 ;;
    -h|--help)
      echo "Usage: ./uninstall.sh [--purge] [--remove-build-container] [--remove-checkout] [--yes] [--dry-run]"
      exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done
if [ "$purge" = 0 ] && { [ "$remove_container" = 1 ] || [ "$remove_checkout" = 1 ]; }; then
  echo "--remove-build-container and --remove-checkout require --purge" >&2
  exit 2
fi
if [ "$FRAME_LOCAL" = 1 ] && [[ "$previous_runtime" == */frametop ]] && [ "$dry_run" = 0 ]; then
  echo "Use SSH or the STOCK SteamOS desktop: stopping Frametop kills its own terminal." >&2
  exit 2
fi
echo "Frametop uninstall on $([ "$FRAME_LOCAL" = 1 ] && echo 'this headset' || echo "$FRAME_HOST")"
echo "  Remove installed services, launcher overrides, pointer driver and Bluetooth fixups."
echo "  Purge personal settings/state/backgrounds: $purge"
echo "  Remove potentially shared Fedora 'dev' build container: $remove_container"
echo "  Remove repo checkout on headset: $remove_checkout"
echo "  Stock SteamVR, Steam, Distrobox, games and external Nix modifications remain untouched."
if [ "$dry_run" = 0 ] && [ "$assume_yes" = 0 ]; then
  read -r -p "Continue? [y/N] " reply
  [[ "$reply" =~ ^[Yy] ]] || { echo "Cancelled."; exit 0; }
fi
mode=apply
[ "$dry_run" = 1 ] && mode=dry-run
status=0

# Transmit code, not files. In particular do not call sync.sh during uninstall.
on_frame_script "$mode" "$purge" "$remove_container" "$FRAME_REPO" <<'HOST' || status=1
set -euo pipefail
mode=$1 purge=$2 remove_container=$3 repo=$4
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus
shopt -s nullglob
units="frametop-pointer.service frametop-input-relay.service frametop-camd.service frametop-hands.service frametop-gaze.service"
apps="deckard-nested-desktop.desktop ft-input-settings.desktop ft-display-settings.desktop ft-layout-reset.desktop ft-screens-toggle.desktop ft-gazeprobe.desktop ft-gaze-probe.desktop"
driver="$HOME/.local/share/frametop/ft_pointer"
vrpathreg=/opt/steamvr/bin/linuxarm64/vrpathreg
errors=0
driver_safe=1
if [ "$mode" = dry-run ]; then
  echo "[DRY RUN] Stop the nested desktop, NOT steamvr.service."
  echo "[DRY RUN] Disable/remove user units: $units"
  echo "[DRY RUN] Remove launcher entries: $apps"
  echo "[DRY RUN] Unregister ft_pointer with vrpathreg, then delete its files."
  echo "[DRY RUN] Remove generated Frametop window decoration and application copies."
  [ "$purge" = 0 ] || echo "[DRY RUN] Delete layout/config/profile/instrument/cache/state files, copied backgrounds and Frametop OpenVR backups."
  [ "$remove_container" = 0 ] || echo "[DRY RUN] Destroy possibly SHARED 'dev' distrobox container."
  exit 0
fi

echo "== Stop Frametop and its services"
# Allow ft-screens to call VR_Shutdown() before tearing down its systemd unit.
pkill -TERM -x ft-screens 2>/dev/null || true
pkill -TERM -f '[v]r-overlay-key frametop ' 2>/dev/null || true
for i in $(seq 1 20); do
  if ! pgrep -x ft-screens >/dev/null && ! pgrep -f '[v]r-overlay-key frametop ' >/dev/null; then break; fi
  sleep 0.2
done
systemctl --user stop frametop-desktop.service 2>/dev/null || true
for unit in $units; do systemctl --user disable --now "$unit" >/dev/null 2>&1 || true; done
systemctl --user clean --what=fdstore frametop-input-relay.service >/dev/null 2>&1 || true
pkill -TERM -x ft-pointer 2>/dev/null || true
pkill -TERM -x ft-hands 2>/dev/null || true
pkill -TERM -x ft-camd 2>/dev/null || true
pkill -TERM -f '^ft-taskbar ' 2>/dev/null || true
pkill -TERM -f '[f]t-mpris.py' 2>/dev/null || true
pkill -TERM -f '[f]t-launch.py' 2>/dev/null || true
pkill -TERM -f '[f]t-shell-watch.sh' 2>/dev/null || true

echo "== Unregister SteamVR pointer driver"
if [ -x "$vrpathreg" ]; then
  if ! registrations=$(LD_LIBRARY_PATH=/opt/steamvr/bin/linuxarm64 "$vrpathreg" show 2>/dev/null); then
    echo "ERROR: vrpathreg show failed. Keeping driver files." >&2; errors=1; driver_safe=0
  elif grep -F "$driver" <<< "$registrations" >/dev/null; then
    paths="$HOME/.config/openvr/openvrpaths.vrpath"
    if [ -f "$paths" ]; then
      cp -a "$paths" "$paths.frametop-uninstall.$(date +%Y%m%d%H%M%S)"
    fi
    if ! LD_LIBRARY_PATH=/opt/steamvr/bin/linuxarm64 "$vrpathreg" removedriver "$driver"; then
      echo "ERROR: vrpathreg removedriver failed. Keeping driver files." >&2
      errors=1; driver_safe=0
    fi
  fi
elif [ -d "$driver" ]; then
  echo "ERROR: vrpathreg unavailable. Keeping driver files." >&2
  errors=1; driver_safe=0
fi
# A successful exit code is not proof that vrpathreg actually removed the entry.
if [ "$driver_safe" = 1 ] && [ -x "$vrpathreg" ]; then
  if ! post_paths=$(LD_LIBRARY_PATH=/opt/steamvr/bin/linuxarm64 "$vrpathreg" show 2>/dev/null); then
    echo "ERROR: cannot verify OpenVR registration after uninstall; keeping driver files." >&2
    errors=1; driver_safe=0
  elif grep -F "$driver" <<< "$post_paths" >/dev/null; then
    echo "ERROR: ft_pointer is still registered; keeping driver files." >&2
    errors=1; driver_safe=0
  fi
fi
if [ "$driver_safe" = 1 ]; then rm -rf -- "$driver"; fi

echo "== Remove Frametop desktop integration"
for unit in $units; do
  rm -f -- "$HOME/.config/systemd/user/$unit"
  rm -f -- "$HOME/.config/systemd/user/default.target.wants/$unit"
  rm -f -- "$HOME/.config/systemd/user/steamvr.service.wants/$unit"
done
systemctl --user daemon-reload || { echo "ERROR: systemd daemon-reload failed." >&2; errors=1; }
for app in $apps; do rm -f -- "$HOME/.local/share/applications/$app"; done
if [ -L "$HOME/.local/bin/ft-handsctl" ] &&
   [ "$(readlink "$HOME/.local/bin/ft-handsctl")" = "$repo/hands/ft-handsctl" ]; then
  rm -f -- "$HOME/.local/bin/ft-handsctl"
fi
deco="$HOME/.local/share/kwin/decorations/kwin4_decoration_qml_frametop"
rm -rf -- "$deco" "$deco"_try* "$HOME/.local/share/frametop/apps"
if ! pgrep -x ft-screens >/dev/null && ! pgrep -f '[v]r-overlay-key frametop ' >/dev/null; then
  rm -rf -- "$XDG_RUNTIME_DIR/frametop"
else
  echo "ERROR: compositor still running; runtime kept." >&2; errors=1
fi

if [ "$purge" = 1 ]; then
  echo "== Purge Frametop user data"
  # Never delete an active SteamVR background without first switching to stock Aurora.
  bg="$HOME/.config/openvr/config/frametop-backgrounds"
  keep_background=0
  settings="$HOME/.config/openvr/config/steamvr.vrsettings"
  if [ -d "$bg" ] && [ -f "$settings" ] && grep -F "$bg/" "$settings" >/dev/null; then
    if [ -f "$repo/scripts/frame-background" ] &&
       python3 "$repo/scripts/frame-background" aurora; then
      echo "Restored stock Aurora environment."
    else
      echo "ERROR: SteamVR may reference these background images; retaining them." >&2
      keep_background=1; errors=1
    fi
  fi
  [ "$keep_background" = 1 ] || rm -rf -- "$bg"
  rm -rf -- "$HOME/.config/frametop" "$HOME/.config/frametop-remote"
  rm -rf -- "$HOME/.config/frametop-instruments" "$HOME/.local/state/frametop" "$HOME/.cache/frametop"
  rm -f -- "$HOME/.config/frametop.conf" "$HOME/.config/frametop-input.json"
  rm -f -- "$HOME/.config/frametop-layout.json" "$HOME/.config/frametop-layout-profiles.json"
  for backup in "$HOME"/.config/openvr/openvrpaths.vrpath.frametop-*; do rm -f -- "$backup"; done
  for log in /tmp/frametop-*.log /tmp/ft-pointer.log; do [ ! -O "$log" ] || rm -f -- "$log"; done
  [ "$driver_safe" = 0 ] || rm -rf -- "$HOME/.local/share/frametop"
else
  rmdir "$HOME/.local/share/frametop" 2>/dev/null || true
fi

if [ "$remove_container" = 1 ]; then
  echo "== Remove explicitly selected dev container"
  if [ -x "$HOME/.local/bin/distrobox" ]; then
    "$HOME/.local/bin/distrobox" rm --force dev || { echo "ERROR: dev container removal failed." >&2; errors=1; }
  else
    echo "ERROR: Distrobox not present; cannot verify dev container removal." >&2; errors=1
  fi
fi

echo "== Verify user integration cleanup"
for unit in $units; do
  for file in "$HOME/.config/systemd/user/$unit" "$HOME/.config/systemd/user/steamvr.service.wants/$unit" "$HOME/.config/systemd/user/default.target.wants/$unit"; do
    if [ -e "$file" ]; then echo "ERROR: unit remains: $file" >&2; errors=1; fi
  done
  if systemctl --user is-active --quiet "$unit"; then
    echo "ERROR: service still active: $unit" >&2; errors=1
  fi
  if systemctl --user is-enabled --quiet "$unit"; then
    echo "ERROR: service still enabled: $unit" >&2; errors=1
  fi
done
if systemctl --user is-active --quiet frametop-desktop.service; then
  echo "ERROR: nested desktop service is still running." >&2; errors=1
fi
for app in $apps; do
  if [ -e "$HOME/.local/share/applications/$app" ]; then
    echo "ERROR: launcher remains: $app" >&2; errors=1
  fi
done
if [ -d "$driver" ]; then echo "ERROR: driver files remain." >&2; errors=1; fi
if [ "$purge" = 1 ]; then
  for file in "$HOME/.config/frametop" "$HOME/.config/frametop.conf" "$HOME/.config/frametop-input.json" "$HOME/.config/frametop-layout.json" "$HOME/.config/frametop-layout-profiles.json" "$HOME/.config/frametop-instruments" "$HOME/.config/frametop-remote" "$HOME/.local/state/frametop" "$HOME/.cache/frametop"; do
    if [ -e "$file" ]; then echo "ERROR: user data remains: $file" >&2; errors=1; fi
  done
fi
[ "$errors" != 0 ] || echo "User integration cleanup verified."
exit "$errors"
HOST

echo "== Remove system-level Frametop Bluetooth fixups"
if on_frame 'test -e /etc/systemd/system/steamframe-bt-fixups.service || test -e /etc/steamframe/bt-fixups.sh || test -e /etc/systemd/system/bluetooth.service.d/steamframe.conf'; then
  if [ "$dry_run" = 1 ]; then
    echo "[DRY RUN] Would sudo-disable/remove steamframe-bt-fixups service and script."
  elif ! frame_sudo 'systemctl disable --now steamframe-bt-fixups.service 2>/dev/null || true
rm -f /etc/systemd/system/steamframe-bt-fixups.service /etc/steamframe/bt-fixups.sh /etc/systemd/system/bluetooth.service.d/steamframe.conf
rmdir /etc/steamframe /etc/systemd/system/bluetooth.service.d 2>/dev/null || true
systemctl daemon-reload'; then
    echo "ERROR: Bluetooth cleanup failed; sudo may be required." >&2; status=1
  fi
fi

if [ "$dry_run" = 0 ] &&
   on_frame 'test -e /etc/systemd/system/steamframe-bt-fixups.service || test -e /etc/steamframe/bt-fixups.sh || test -e /etc/systemd/system/bluetooth.service.d/steamframe.conf'; then
  echo "ERROR: Frametop Bluetooth files remain installed." >&2
  status=1
fi

if [ "$remove_checkout" = 1 ]; then
  if [ "$dry_run" = 1 ]; then
    echo "[DRY RUN] Would delete checkout: $FRAME_REPO"
  elif [ "$status" = 0 ]; then
    on_frame_script "$FRAME_REPO" <<'HOST' || status=1
set -euo pipefail
repo=$1
case "$repo" in
  "$HOME"/frametop|"$HOME"/dev/frametop) ;;
  *) echo "ERROR: unsafe checkout path $repo; refusing." >&2; exit 1 ;;
esac
[ ! -L "$repo" ] || { echo "ERROR: checkout is symlink; refusing." >&2; exit 1; }
rm -rf -- "$repo"
HOST
  else
    echo "Skipping checkout deletion because uninstallation was incomplete." >&2
  fi
fi

if [ "$dry_run" = 1 ]; then
  echo "Dry run complete; no changes made."
elif [ "$status" = 0 ]; then
  echo "Uninstall finished. Restart SteamVR if ft_pointer was previously loaded."
else
  echo "INCOMPLETE uninstall; review errors above before restarting SteamVR." >&2
fi
echo "External Nix/Steam UI patches, Steam per-game launch options and Distrobox itself are not managed by this uninstaller."
exit "$status"

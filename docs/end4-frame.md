# end-4 on the Steam Frame

The experimental session runs the laptop's end-4 Quickshell config from a
staged copy. This file is the dependency inventory and the Frame-specific
choices. The laptop files under `~/.config` are not edited. Packages are
added in `setup/dev-container.sh` and installed only inside the Fedora
`dev` container.

Quickshell in that container is 0.2.1 (`dacfa9de`). The laptop shell is
written for 0.3.2 (`4f508be`). The first live test's broken look was the
missing theme, which is now staged. One 0.2.1 difference is still visible:
Qt's native text path drops some Material Symbol ligatures, so the staged
icon widget uses Qt's own renderer while `FT_FRAME_SESSION` is set. Building
0.3.2 is not required for the rest of the shell.

## Desktop tools

| Need | Used for | Frame |
| --- | --- | --- |
| `jq` | Wallpaper, color, and settings scripts | Install in the container |
| `curl` | Konachan and other downloads | Already in the container |
| ImageMagick, `ffmpeg-free` | Wallpaper probes and video wallpapers | ImageMagick was already installed; `ffmpeg-free` is added |
| `python3-pillow` | Image helpers under `scripts/` | Install in the container |
| `qalc` (`qalculate`) | Calculator in the launcher | Install in the container |
| `cliphist`, `wl-paste` | Clipboard history | Install `cliphist`. Startup stores one blank entry (`cliphist list` exits 1 on an empty database) and then runs `wl-paste --watch cliphist store` on this session's Wayland socket |
| `grim`, `slurp` | Region screenshots | Install in the container |
| `libnotify` | `notify-send` from scripts | Install in the container. The shell is the notification server on the session bus |
| `playerctl` | A few media fallbacks | Install in the container. Playback itself is MPRIS on the session bus |
| `xdg-user-dirs` | Wallpaper download directory | Install in the container |
| `iw` | SSID for the network status shim | Install in the container |

The Konachan and osu wallpaper scripts on the laptop read
`~/.config/illogical-impulse/config.json`. The staged copies use
`$XDG_CONFIG_HOME`, which the session sets to the staged config. They do
not read or write the host config.

## Theme

`session/frame-theme.sh` seeds colors, the wallpaper path, and fontconfig
for the staged shell. `session/frame-kde-theme.py` writes a KDE color
scheme and GTK icon settings into `~/.config/frametop/hyprland` and
`~/.local/share/frametop/hyprland`. `session/bin/dolphin` is ahead of
`/usr/bin` on the session `PATH` and points Dolphin at those directories
with `QT_QPA_PLATFORMTHEME=kde`. Host Plasma keeps `~/.config`.

The laptop's `kde-material-you-colors` step needs a virtualenv that exists
only on the laptop (`ILLOGICAL_IMPULSE_VIRTUAL_ENV`). A wallpaper change
still updates `wallpaperPath` before that step. Recoloring every Qt app
from a new download needs that tool, which is not on the Frame. Dolphin
follows the colors that were already generated and copied into the session.

## Audio

The session's `XDG_RUNTIME_DIR` is a private `/tmp/ftH.*` directory so
Hyprland's socket fits in `sun_path`. PipeWire clients would otherwise look
there and miss SteamOS. When `/run/user/<uid>/pipewire-0` exists, the
session sets `PIPEWIRE_RUNTIME_DIR` to that directory. When the Pulse
socket exists, it sets `PULSE_SERVER`. No second PipeWire is started.
The volume widget talks to the headset's existing server.

## Network, Bluetooth, power, brightness

The container can see `/run/host/run/dbus/system_bus_socket`, but a client
there fails with `Failed to get credentials`. A proxy socket hung instead
of connecting. NetworkManager, BlueZ, and UPower are therefore not usable
from the container, and their daemons are not installed beside SteamOS.

`session/bin/nmcli` is on the session `PATH` only. It answers the status
commands end-4 already runs, using the container's default route (distrobox
shares the host network namespace). `nmcli radio`, `connection`, and
`device wifi connect` exit with an error and do not change the headset
radio. The bar can show the link. Wifi scanning and radio toggles stay
inoperative on purpose.

Battery and Bluetooth widgets already hide themselves when UPower and BlueZ
are absent. Brightness and `ddcutil` have no panel backlight to drive. The
staged brightness service returns immediately when `FT_FRAME_SESSION` is
set, so those controls do not spawn missing programs. Suspend, hyprlock,
and hypridle stay out of the session launcher.

## Intentionally different

| Laptop piece | Frame |
| --- | --- |
| ChatGPT bridge at `/home/tovakai/Projects/quickshell-chatgpt` | Not started. The staged command is `/usr/bin/bash` and exits immediately when `FT_FRAME_SESSION` is set. The venv is not copied |
| Conflict killer (`killall kded6`) | Returns before doing anything when `FT_FRAME_SESSION` is set |
| Monitor brightness, DDC, suspend | No-ops or hidden |
| Host Plasma session bus | Not imported. The nested session has its own bus |
| `matugen` and the laptop color virtualenv | Not installed. Existing `colors.json` is the theme source |

## Controller

R1 is a left click. R3 is a right click. Trigger+R3 closes the focused
window once and should not also right-click. The press/release rules are
in `input/test/controller-chords-test.py`. This has not been confirmed in
the headset.

## Checks

Offline: `python3 -m unittest session.tests.test_stage_end4 session.tests.test_frame_desktop session.tests.test_frame_services` and `input/test/controller-chords-test.py`.

On the Frame, after `setup/dev-container.sh`: the new commands resolve
inside `dev`, and a `--no-vr` smoke must leave `kded6` running. Do not
restart the input relay or open a headset session until that is approved.

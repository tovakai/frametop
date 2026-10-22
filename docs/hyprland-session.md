# Experimental nested Hyprland session

This branch is a smoke test, **not** a finished end-4/Quickshell port.
No installers, live sessions or Steam launchers are modified by checking out
this branch. Plasma remains the default (`DESKTOP=plasma`).

## Architecture

```text
SteamVR
  └── ft-screens (VR surfaces, pointer/keyboard relay, DMA-BUF)
        └── Hyprland (nested Wayland backend, one output surface per panel)
              └── simple terminal (Quickshell later)
```

`FT_DESKTOP_SESSION=hyprland` chooses the experimental desktop for a
**single launch**; `DESKTOP=hyprland` in `~/.config/frametop.conf` makes it
the default (not recommended until tested). Only the `screens` backend is
supported and `FLOAT_SLOTS` becomes 0. KWin-specific layout startup,
floating windows, remote desktop and automatic SteamVR keyboard are bypassed.

## Hardware bring-up stages

1. Work in `feature/hyprland-session` **without overwriting the currently
   installed Frametop checkout**. Build that branch's `screens/build.sh` in
   Frametop's existing Fedora development container; it advertises
   `xdg_wm_base` v6 rather than v3.
2. Run `session/hyprland-doctor.sh` to check what's installed in the
   container. It may start a stopped dev container, but installs nothing.
3. Install matching **aarch64** Hyprland (target 0.56.2, Aquamarine 0.15.1),
   `dbus-run-session` and optionally `foot` **inside that dev container**.
   Fedora 44 has no official Hyprland binary. COPR `sdegler/hyprland` (a
   clone of solopasha's packaging, no homepage) publishes Fedora 44 aarch64
   RPMs: Hyprland 0.56.2-2 built from tag `v0.56.2` and Aquamarine 0.15.1-1.
   Install them with a one-shot `--repofrompath` and
   `--setopt=install_weak_deps=False`. Do not `dnf copr enable` it: a
   persistent repo would pull Hyprland into later container upgrades, and
   the weak dependencies `uwsm` and `xdg-desktop-portal-hyprland` run
   `systemd-update-helper` for user units. Hyprland itself has no scriptlet.
   Do not change the SteamOS host root.
   That Aquamarine 0.15.1 still commits a buffer from `xdg_toplevel.configure`
   before `ack_configure`, which wlroots rejects (`xdg_surface has never been
   configured`). `session/build-aquamarine.sh` builds tag `v0.15.1` plus
   upstream commit `7bb8bdf` into `build/aquamarine`. The session and the
   smoke harness prepend that directory on `LD_LIBRARY_PATH`.
4. First run `session/hyprland-smoke.sh` from the branch. It uses
   `ft-screens --no-vr` on **unique** Wayland/control socket names with an
   isolated Hyprland runtime and auto-exits after 15 seconds. It never
   registers SteamVR panels. The harness fails unless every output logs a
   mapped `screen N: commit` of the requested size and the client stays
   connected. It runs
   `wayland-info | session/hyprland-protocol-check.py` against the **actual**
   `ft-screens` socket before starting Hyprland. Protocol version checks are
   necessary but do not prove protocol behavior or DMA-BUF import. To exercise extra
   outputs without VR, set `FT_SCREEN_COUNT=2`.
5. Launch the experimental branch only when you're ready to test. From that
   checkout, `FT_DESKTOP_SESSION=hyprland ./session/frametop-session.sh`
   starts **one** 1280×720 panel on sockets `ft-hyprland-0` and
   `ft_hyprland`. It does not read `ft-layout screen-args` and does not
   change `~/.config/frametop-layout.json`. `FT_SCREEN_COUNT` other than 1
   is rejected. Cleanup kills only the `ft-screens` whose command line
   carries `ft-hyprland-0`, and Hyprland started with this tree's minimal
   config (`session/hyprland-stop.sh` does the same). The Plasma path still
   uses the saved layout and its own `ft-screens-0` process. There is no
   separate Steam launcher: run this checkout's session script. Do not
   symlink it over the installed one.
6. Collect `/tmp/frametop-hyprland-screens.log` (not the Plasma
   `/tmp/frametop-screens.log`); check SteamVR
   frame timing and Plasma fallback before expanding to multiple outputs.

The smoke harness may start Frametop's container and will create temporary
runtime paths; it does **not** stop or modify the existing Frametop process.
It verifies host protocol negotiation and surface commits but **cannot**
validate SteamVR buffer import, panel rendering or controller interaction.

## Session mechanics

Hyprland is launched through `scripts/in-box` with an absolute Wayland
socket path, separate config/state folders (`~/.config/frametop/hyprland`
and `~/.local/state/frametop/hyprland`) and a per-launch isolated runtime.
The nested runtime directory is a short `/tmp/ftH.*` path. Hyprland's
instance socket is `$XDG_RUNTIME_DIR/hypr/<abi signature>/.socket2.sock`,
and `sockaddr_un.sun_path` holds 108 bytes; the user runtime directory
makes that path too long and Hyprland disables IPC.
`dbus-run-session` owns the nested bus; `HYPRLAND_NO_SD_VARS=1` and
`HYPRLAND_NO_SD_TARGET=1` prevent nested Hyprland from importing variables
or activating/stopping SteamOS user graphical session targets. The current
compositor runs inside the Fedora dev container, not directly on the host.

`session/hyprland-frame.lua` is the config the experimental session loads.
When `~/.config/hypr/hyprland.lua` is present it runs that file, so the
laptop's keybinds stay in force. `session/frame-hypr/` is ahead of it on
`package.path` and replaces startup only: Quickshell via
`session/frame-quickshell.sh`, and no hypridle, brightness agent, or login
autostart. A missing `qs` or a missing `~/.config/quickshell/ii` exits that
helper with status 0; Hyprland keeps running. Without the laptop config,
the same file falls back to one terminal and `SUPER+Return` /
`SUPER+SHIFT+E`. `session/hyprland-minimal.lua` remains that fallback's
reference. `FT_HYPRLAND_CONFIG` still selects another file.

The installed input relay sends keys to `@ft_screens`. The experimental
compositor listens on `@ft_hyprland`, and `session/hyprland-key-forward.py`
forwards key, click, and chord messages while `@ft_screens` is free. It
does not start when Plasma's compositor already holds that name.

## Remaining gates

- [x] Live protocol audit for Aquamarine `wl_compositor` 6,
      `wl_seat` 9, `xdg_wm_base` 6, `wl_shm` 1, and
      `zwp_linux_dmabuf_v1` 4 with feedback. ft-screens on wlroots 0.20.2
      advertises each of those versions; `wayland-info` against a `--no-vr`
      socket matches. Version checks do not prove DMA-BUF import.
- [x] `--no-vr` DMA-BUF commits from nested Hyprland. One 1280×720 output
      and two 1280×720 outputs both map `aquamarine - WAYLAND-N` toplevels
      and report buffer commits on the control socket. This does not import
      those buffers into SteamVR.
- [x] SteamVR `ImportDmabuf` and one 1280×720 panel. The first live session
      mapped `aquamarine - WAYLAND-1`, logged modifiers SteamVR can import,
      and did not log `ImportDmabuf failed`. Frame pacing followed the
      existing in-view rate until the panel was focused.
- [x] Controller click, keyboard focus, and scroll on that one-terminal
      session. Keyboard shortcuts needed the `@ft_screens` forwarder; the
      session starts it now. `SUPER+Return` and `SUPER+SHIFT+E` are Hyprland
      binds and do nothing until the key arrives at this compositor.
- [ ] Additional outputs and correct output-to-panel mapping. `ft-screens`
      currently assigns indices by initial creation order and reads
      KWin-specific spare output titles; removal/recreation isn't safe yet.
- [ ] Pause/resume, clean shutdown, Plasma fallback and frame pacing.
- [ ] Hyprland adapters for KWin-specific floating windows, screen management,
      remote desktop and automatic VR keyboard.
- [ ] Frame-specific end-4/Quickshell profile. The session launches the
      laptop's existing `~/.config/quickshell/ii` when `qs` and that tree
      are on the machine. It does not copy or edit that tree. Battery,
      brightness, and suspend modules are still in the shell; a module
      error stays inside the Quickshell process. The right-controller
      profile is `session/frame-controller-profile.json`. It is not merged
      into `~/.config/frametop-input.json`, and the installed input relay
      is not restarted by these changes. R1, R3, and stick scroll stay
      SteamVR's click and scroll. Trigger is a modifier only after that
      profile is active: face buttons change workspace or move the focused
      window, and trigger plus a face button or R1 launches an app or
      sends one `closewindow`.

## Controller chords

`input/controller_chords.py` decides a press. The trigger never launches
anything. Releasing the trigger and the other button in either order does
not launch a second action. Trigger+R1 does not bind the bumper, so the
normal left click remains; ft-screens swallows that click only while
`chord-click 1` is set and asks the relay to run the close action once.
A VR game, pause, or typing leaving the desktop clears the modifier.
Applying the profile and restarting the relay needs approval. Set
`FT_CONTROL_SOCKET=ft_hyprland` on that relay so chord messages reach this
compositor, or leave the forwarder in the session path.

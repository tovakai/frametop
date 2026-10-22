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
`FT_HYPR_CONFIG_ROOT` selects the Hyprland tree (the staged copy under
`stage/config/hypr`). When that file is absent it falls back to
`~/.config/hypr/hyprland.lua`, then to one terminal and `SUPER+Return` /
`SUPER+SHIFT+E`. `session/frame-hypr/` is ahead of the selected tree on
`package.path` and replaces startup only: Quickshell via
`session/frame-quickshell.sh`, and no hypridle, brightness agent, or login
autostart. Quickshell reads `FT_USER_CONFIG_HOME` (the staged
`stage/config`, whose `quickshell/ii` is the end-4 copy). A missing `qs`
or a missing shell exits that helper with status 0; Hyprland keeps running.
`session/hyprland-minimal.lua` remains the fallback's reference.
`FT_HYPRLAND_CONFIG` still selects another file. The session does not write
`~/.config/hypr` or `~/.config/quickshell`. `session/frame-hypr/hyprland/services/create_custom_config.lua`
replaces the laptop startup hook that would create `~/.config/hypr/custom`.

Before Hyprland starts, the session writes
`$XDG_RUNTIME_DIR/frametop-hyprland.route` with its pid, the exact runtime
directory, the Wayland socket, the control name `ft_hyprland`, and the
staged config home. The exit trap and `hyprland-stop.sh` remove that file.
A dead pid is not a session. `frame-desktop-action.sh` refuses to run when
the route's runtime has zero or more than one Hyprland signature directory.
Host commands re-enter the Fedora container through `scripts/in-box` with
that runtime and signature. The script name is `frame-desktop-action.sh`.
Launcher IPC is `qs -c ii ipc --any-display call search toggle` so it can
see the shell when the caller is not the same display connection.
The Fedora container has Quickshell 0.2.1
(`dacfa9de829ac7cb173825f593236bf2c21f637e`). The laptop shell was written
for 0.3.2 (`4f508be`). The 0.2.1 package is what the isolated smoke loaded.

The installed input relay sends keys to `@ft_screens`. The experimental
compositor listens on `@ft_hyprland`, and `session/hyprland-key-forward.py`
forwards key, click, and chord messages while `@ft_screens` is free. It
does not start when Plasma's compositor already holds that name. The relay
in this checkout, once it is the running unit, sends desktop input to the
route's control socket while the route is live and Plasma's `ft-screens` is
not running. Chord buttons are requested only in that same case, and only
while typing is going to the desktop.

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
- [ ] Frame-specific end-4/Quickshell profile loaded in VR. A staged copy
      lives under `stage/config` and is not the user's `~/.config`. Battery,
      brightness, and suspend modules are still in the shell; a module
      error stays inside the Quickshell process. The right-controller
      profile is `session/frame-controller-profile.json`. It is not merged
      into `~/.config/frametop-input.json`, and the installed input relay
      is not restarted by these changes. R1, R3, and stick scroll stay
      SteamVR's click and scroll. Trigger is a modifier only after that
      profile is active: face buttons change workspace or move the focused
      window, and trigger plus a face button or R1 launches an app or
      sends one `closewindow`. Trigger+R1 does not become a left click when
      the trigger is released first.

## Controller chords

`input/controller_chords.py` decides a press. The trigger never launches
anything. Releasing the trigger and the other button in either order does
not launch a second action. Trigger+R1 does not bind the bumper, so the
normal left click remains; ft-screens swallows that click only while
`chord-click 1` is set and asks the relay to run the close action once.
Disarming leaves an already swallowed press swallowed, so releasing the
trigger before R1 does not deliver the button-up. A VR game, pause, typing
leaving the desktop, or the route file disappearing clears the modifier and
drops the buttons from the helper's bind list. They are also left unbound
while `controller_in_games` is set. The commands are
`command:frame-desktop-action.sh`, the file on `PATH`.

## Relay deployment (not applied)

The user unit `frametop-input-relay.service` is `Type=notify` with
`FileDescriptorStorePreserve=yes`. Its `ExecStart` is
`/usr/bin/python3 /home/steamos/frametop-api/input/input-relay.py`.
Restarting that unit keeps the virtual mouse and keyboard file descriptors
in systemd's store, so SteamVR does not have to reopen them.

This checkout's relay is not the running process. Switching it, merging
`controller_chords` into `~/.config/frametop-input.json`, and restarting
the unit are separate steps and are not done here. After a switch, chords
still stay idle until the experimental session writes the route file.

Rollback, after a switch that has been approved and performed:

1. Point `ExecStart` back at `/home/steamos/frametop-api/input/input-relay.py`.
2. `systemctl --user daemon-reload` and `systemctl --user restart frametop-input-relay`.
3. Restore `~/.config/frametop-input.json` from the copy made before the merge.
4. Do not `systemctl --user clean --what=fdstore frametop-input-relay` unless
   the virtual devices themselves must be recreated. Cleaning the store makes
   SteamVR lose those devices until SteamVR is restarted.

Stopping the experimental session removes the route file. With the new relay,
that releases the chord buttons without another edit. The installed relay is
unchanged by removing the file.

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
   Fedora 44 has no official Hyprland binary. COPR `sdegler/hyprland` had
   Fedora 44 aarch64 RPMs for both target versions in September 2026. It is
   a third-party source: review provenance and versions first. A possible
   explicitly approved, **container-only** install is
   `dnf copr enable sdegler/hyprland` then `dnf install hyprland`.
   Do not enable the COPR automatically or change the SteamOS host root.
   Inspect current dependencies and the chosen repository before installing.
4. First run `session/hyprland-smoke.sh` from the branch. It uses
   `ft-screens --no-vr` on **unique** Wayland/control socket names with an
   isolated Hyprland runtime and auto-exits after 15 seconds. It never
   registers SteamVR panels. The test is still unvalidated on the Frame;
   use SSH to capture its output and check for Wayland bind failures,
   `screen 1: commit`, and any DMA-BUF errors. The harness also runs
   `wayland-info | session/hyprland-protocol-check.py` against the **actual**
   `ft-screens` socket before starting Hyprland. Protocol version checks are
   necessary but do not prove protocol behavior or DMA-BUF import. To exercise extra
   outputs without VR, set `FT_SCREEN_COUNT=2`.
5. Launch the experimental branch only when you're ready to test. Start with
   `FT_DESKTOP_SESSION=hyprland FT_SCREEN_COUNT=1` on a disposable
   test session and verify a single panel renders and accepts input.
   The branch currently has no separate Steam launcher: the caller must
   explicitly select the branch's session script rather than running the
   installed one. Do not symlink this branch over the active installation.
6. Collect session logs and `/tmp/frametop-screens.log`; check SteamVR
   frame timing and Plasma fallback before expanding to multiple outputs.

The smoke harness may start Frametop's container and will create temporary
runtime paths; it does **not** stop or modify the existing Frametop process.
It verifies host protocol negotiation and surface commits but **cannot**
validate SteamVR buffer import, panel rendering or controller interaction.

## Session mechanics

Hyprland is launched through `scripts/in-box` with an absolute Wayland
socket path, separate config/state folders (`~/.config/frametop/hyprland`
and `~/.local/state/frametop/hyprland`) and a per-launch isolated runtime.
`dbus-run-session` owns the nested bus; `HYPRLAND_NO_SD_VARS=1` and
`HYPRLAND_NO_SD_TARGET=1` prevent nested Hyprland from importing variables
or activating/stopping SteamOS user graphical session targets. The current
compositor runs inside the Fedora dev container, not directly on the host.

The shipped **Lua** file `session/hyprland-minimal.lua` targets Hyprland
0.56.2, using its `hl.*` configuration API. Its startup event launches
`session/hyprland-on-start.sh` to add only the extra Wayland-backed outputs
via `hyprctl output create wayland` and start one terminal if installed.
`SUPER+SHIFT+E` exits the nested compositor. No wallpaper daemon, portal,
hypridle, system agents, laptop shortcuts or Quickshell are started.

`FT_HYPRLAND_CONFIG=/absolute/path/to/config.lua` overrides the minimal
config, provided the container can see that same absolute path.

## Remaining gates

- [ ] Live protocol audit for Aquamarine `wl_compositor` 6,
      `wl_seat` 9, `xdg_wm_base` 6, `wl_shm` 1, and
      `zwp_linux_dmabuf_v1` 4 with feedback. Only xdg-shell
      advertisement changed; exact compatibility still requires a Frame run.
- [ ] First successful DMA-BUF buffer import from nested Hyprland.
- [ ] Input: controller click, keyboard focus, mouse and scroll.
- [ ] Additional outputs and correct output-to-panel mapping. `ft-screens`
      currently assigns indices by initial creation order and reads
      KWin-specific spare output titles; removal/recreation isn't safe yet.
- [ ] Pause/resume, clean shutdown, Plasma fallback and frame pacing.
- [ ] Hyprland adapters for KWin-specific floating windows, screen management,
      remote desktop and automatic VR keyboard.
- [ ] Frame-specific end-4/Quickshell profile.

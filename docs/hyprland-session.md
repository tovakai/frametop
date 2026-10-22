# Experimental nested Hyprland session

Branch: `feature/hyprland-session`, based on `rebuild/extension-api`.

This is a **smoke-test scaffold**, not a complete Hyprland/Quickshell port. The
stock Plasma path stays the default. No installer or Steam launcher is changed.

## Initial design

```text
SteamVR
  └── ft-screens (SteamVR panels, input relay, DMA-BUF)
        └── Hyprland (Wayland backend, one toplevel per output)
              └── terminal (Quickshell later)
```

`DESKTOP=plasma|hyprland` in `~/.config/frametop.conf` selects the nested desktop
independently from `BACKEND=screens|gamescope`. For a one-time experiment,
`FT_DESKTOP_SESSION=hyprland` overrides the config. Hyprland currently requires
`BACKEND=screens`. `FLOAT_SLOTS` is forced to zero; the Plasma-specific layout
startup, floating daemon, remote desktop and text-input method are not launched.

## Before a first launch on Frame

1. Build **this branch** of `ft-screens` inside the Fedora container using the
   normal build workflow (`screens/build.sh`). This advertises `xdg_wm_base` v6
   rather than v3. It still needs runtime validation on the Frame.
2. Install a compatible **aarch64** Hyprland (target 0.56.2, Aquamarine 0.15.1),
   `hyprctl`, `dbus-run-session`, and optionally `foot` **inside the same Fedora
   development container**. Do not modify SteamOS's read-only root. Check
   package versions/availability before installing.
3. Use `FT_DESKTOP_SESSION=hyprland` for a disposable session, and keep the
   ordinary Plasma launcher/checkout available for recovery. No Quickshell or
   laptop autostarts should run at this stage.
4. Check the session output, `/tmp/frametop-screens.log`, and the container
   logs. Do not claim hardware support before verifying buffer import and input.

The new `session/frametop-hyprland.sh` launches Hyprland **inside the container**
with a dedicated runtime/config/state path, and leaves the parent Wayland socket
reachable by absolute path. It uses `HYPRLAND_NO_SD_VARS=1` and its own D-Bus
session so that nested Hyprland does not rewrite SteamOS's user environment.

Set `FT_HYPRLAND_CONFIG=/path/to/config` to use a different experimental
Hyprland config. This variable is optional and is **not** the laptop config by
default. Its path must also be visible inside the container.

## Validation milestones

- [ ] Confirm wl_compositor v6, wl_seat v9, xdg_wm_base v6 and linux-dmabuf v4
      bindings from Aquamarine; `xdg_wm_base` was changed but other globals
      still need a live compatibility audit.
- [ ] Render ONE Wayland output to ONE Frametop panel with DMA-BUF import.
- [ ] Verify controller pointer clicks, mouse movement, keyboard focus and scroll.
- [ ] Create a second Wayland-backed output and validate size + panel mapping.
- [ ] Test output removal/recreation: `ft-screens` currently assigns indices by
      toplevel creation order and reads KWin-specific titles for spare outputs.
- [ ] Test clean shutdown, pause/resume and ordinary Plasma fallback.
- [ ] Integrate a Frame-specific end-4/Quickshell profile after those gates.

Important: Hyprland's automatic keyboard, `ft-floatd`, KScreen integration,
remote desktop and application restore are intentionally **not implemented**.
The experimental startup also bypasses Frametop's KWin-aware layout initializer.

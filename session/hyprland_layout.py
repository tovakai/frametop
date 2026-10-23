#!/usr/bin/env python3
"""Spatial layout for the Hyprland desktop.

The file is ~/.config/frametop/hyprland-layout.json (FT_HYPRLAND_LAYOUT
overrides it). Plasma's ~/.config/frametop-layout.json is never read or
written. Screen identity is the id (hypr-1, hypr-2, ...). The slot is the
Frametop panel number and stays put when another screen is removed.

Aquamarine names monitors WAYLAND-N in creation order. That number is not
the slot. assign_monitors() keeps a session map so a recreated monitor
takes the slot whose previous monitor disappeared, and a monitor that is
still alive keeps its slot even if the list arrives in another order.

Poses from a saved arrangement are relative to the headset heading at the
time they were saved. Restoring them uses the heading now. Nothing here
anchors a panel to a fixed point in the room.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "layout"))
import ft_layout  # noqa: E402

PRIMARY_SIZE = (1920, 1080)
PRIMARY_METRES = 1.5
MAX_SCREENS = 24

LIMITATIONS = (
    "Hyprland session. KWin floating windows are not screens.",
    "Remote desktop and krdp are not available on this desktop.",
    "Profiles that reopen Plasma windows are not used here.",
    "A saved pose is relative to the headset heading when it was saved, not a fixed point in the room.",
    "Pointer crossing follows the left-to-right monitor row. A second VR row does not add a vertical crossing.",
    "Named layouts stay in this file. They are not Steam library entries.",
)


def layout_path():
    override = os.environ.get("FT_HYPRLAND_LAYOUT")
    if override:
        return Path(override)
    return Path.home() / ".config" / "frametop" / "hyprland-layout.json"


def _screen(slot, ident=None, size=PRIMARY_SIZE, metres=PRIMARY_METRES):
    return {
        "id": ident or f"hypr-{slot}",
        "slot": slot,
        "size": [int(size[0]), int(size[1])],
        "metres": float(metres),
        "scale": 1.0,
        "curve": 0.0,
    }


def default_layout():
    return {
        "screens": [_screen(1)],
        "primary": "hypr-1",
        "mode": "preset",
        "auto": False,
        "preset": {"kind": "curved", "distance": 2.0, "gap": 0.05, "rows": 1, "height": 0.0},
        "layouts": {},
    }


def load(path=None):
    path = Path(path) if path else layout_path()
    layout = default_layout()
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return layout
    if not isinstance(saved, dict):
        return layout
    screens = []
    for entry in saved.get("screens") or []:
        if not isinstance(entry, dict) or "slot" not in entry or "id" not in entry:
            continue
        slot = int(entry["slot"])
        if slot < 1 or slot > MAX_SCREENS:
            continue
        size = entry.get("size") or list(PRIMARY_SIZE)
        screens.append({
            "id": str(entry["id"]),
            "slot": slot,
            "size": [int(size[0]), int(size[1])],
            "metres": float(entry.get("metres", PRIMARY_METRES)),
            "scale": float(entry.get("scale", 1.0)),
            "curve": float(entry.get("curve", 0.0)),
            **{k: entry[k] for k in ("pos", "face", "roll", "hidden") if k in entry},
        })
    if screens:
        layout["screens"] = screens
    if saved.get("primary"):
        layout["primary"] = saved["primary"]
    layout["mode"] = saved.get("mode") or "preset"
    layout["auto"] = bool(saved.get("auto", False))
    preset = saved.get("preset")
    if isinstance(preset, dict):
        layout["preset"].update(preset)
    named = saved.get("layouts")
    if isinstance(named, dict):
        layout["layouts"] = named
    if saved.get("active"):
        layout["active"] = saved["active"]
    return layout


def save(layout, path=None):
    path = Path(path) if path else layout_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(layout, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def screens_by_slot(layout):
    return sorted(layout.get("screens") or [], key=lambda s: int(s["slot"]))


def max_slot(layout):
    screens = screens_by_slot(layout)
    return max((int(s["slot"]) for s in screens), default=1)


def screen_specs(layout):
    """One ft-screens --screen value per slot, including gaps."""
    by_slot = {int(s["slot"]): s for s in layout.get("screens") or []}
    specs = []
    for slot in range(1, max_slot(layout) + 1):
        screen = by_slot.get(slot)
        if not screen:
            specs.append(f"{PRIMARY_SIZE[0]}x{PRIMARY_SIZE[1]}@{PRIMARY_METRES:.3f}")
            continue
        w, h = screen["size"]
        specs.append(f"{int(w)}x{int(h)}@{float(screen['metres']):.3f}")
    return specs


def shell_export(layout=None):
    layout = layout or load()
    specs = screen_specs(layout)
    lines = [
        f"count={max_slot(layout)}",
        f"outputs={len(layout.get('screens') or [])}",
        "screens=" + " ".join(specs),
    ]
    return "\n".join(lines)


def _monitor_number(name):
    digits = ""
    for ch in reversed(str(name)):
        if ch.isdigit():
            digits = ch + digits
        else:
            break
    return int(digits) if digits else 0


def assign_monitors(layout, live_names, previous):
    """Map live Aquamarine names onto stable slots.

    previous is {monitor_name: screen_id}. Monitors that are still listed
    keep that id's slot. A name that disappeared frees its slot. A new name
    takes the lowest freed slot, not the next integer in its own name.
    The order of live_names does not matter.
    """
    previous = dict(previous or {})
    by_id = {s["id"]: s for s in screens_by_slot(layout)}
    live = list(dict.fromkeys(live_names))
    kept = {}
    used_ids = set()
    for name in live:
        ident = previous.get(name)
        screen = by_id.get(ident) if ident else None
        if screen and ident not in used_ids:
            kept[name] = screen
            used_ids.add(ident)
    free = [s for s in screens_by_slot(layout) if s["id"] not in used_ids]
    fresh = [name for name in live if name not in kept]
    fresh.sort(key=_monitor_number)
    claims = []
    released = [name for name in previous if name not in live]
    for name, screen in kept.items():
        claims.append((name, int(screen["slot"]), screen["id"]))
    for name, screen in zip(fresh, free):
        claims.append((name, int(screen["slot"]), screen["id"]))
    claims.sort(key=lambda item: item[1])
    mapping = {name: ident for name, _slot, ident in claims}
    return {"claims": claims, "mapping": mapping, "released": released}


def poses_for(layout):
    """Head-frame poses for the enabled screens, in slot order."""
    enabled = screens_by_slot(layout)
    synthetic_screens = []
    for screen in enabled:
        entry = {
            "size": list(screen["size"]),
            "metres": float(screen["metres"]),
            "scale": float(screen.get("scale", 1.0)),
            "curve": float(screen.get("curve", 0.0)),
        }
        if layout.get("mode") == "custom" and "pos" in screen:
            entry["pos"] = list(screen["pos"])
            entry["face"] = list(screen.get("face") or [0, 0])
            entry["roll"] = float(screen.get("roll", 0))
        synthetic_screens.append(entry)
    synthetic = {
        "mode": "custom" if layout.get("mode") == "custom" and all("pos" in s for s in synthetic_screens) else "preset",
        "preset": dict(layout.get("preset") or default_layout()["preset"]),
        "screens": synthetic_screens,
    }
    original = ft_layout.backend
    ft_layout.backend = lambda: "screens"
    try:
        return ft_layout.plan(synthetic, len(synthetic_screens))
    finally:
        ft_layout.backend = original


def monitor_row(layout):
    """Left to right. Saved poses order the row; otherwise the slot order."""
    screens = screens_by_slot(layout)
    if layout.get("mode") == "custom" and all("pos" in s for s in screens):
        return sorted(screens, key=lambda s: float(s["pos"][0]))
    return screens


def monitor_commands(layout, mapping):
    """Hyprland monitor rules, one row, edges touching, so the pointer can cross."""
    by_id = {ident: name for name, ident in mapping.items()}
    x = 0
    commands = []
    for screen in monitor_row(layout):
        name = by_id.get(screen["id"])
        if not name:
            continue
        w, h = int(screen["size"][0]), int(screen["size"][1])
        scale = float(screen.get("scale", 1.0))
        scale_text = f"{scale:g}"
        lua = (
            "hl.monitor({"
            f'output="{name}", mode="{w}x{h}@60", position="{x}x0", scale={scale_text}'
            "})"
        )
        commands.append({"monitor": name, "slot": int(screen["slot"]), "x": x, "eval": lua})
        x += w
    return commands


def place_commands(layout, eye, heading):
    """World-space place commands. eye is (x, y, z), heading is degrees."""
    enabled = screens_by_slot(layout)
    poses = poses_for(layout)
    commands = []
    for screen, pose in zip(enabled, poses):
        world = ft_layout.turn_yaw(pose["pos"], heading)
        center = tuple(e + v for e, v in zip(eye, world))
        slot = int(screen["slot"])
        commands.append({
            "slot": slot,
            "id": screen["id"],
            "width": f"width {slot} {float(screen['metres']):.4f}",
            "curve": f"curve {slot} {float(screen.get('curve', 0)):.3f}",
            "place": "place %d %.4f %.4f %.4f %.3f %.3f %.3f" % (
                slot, *center, pose["face"][0] + heading, pose["face"][1], pose["roll"]),
            "size": "slot %d %d %d %.3f" % (
                slot, int(screen["size"][0]), int(screen["size"][1]), float(screen["metres"])),
        })
    return commands


def sync_actions(layout, live_names, previous, placed_ids, baseline=0):
    """What a poll should do. place only for a screen that was not placed yet.

    A panel the user has already placed is listed in placed_ids, so a later
    poll does not move it. That is what keeps a panel the user dragged in VR
    where they left it. `baseline` is how many monitors startup already
    asked Hyprland to create; the poll does not create those again.
    """
    live = list(dict.fromkeys(live_names))
    assigned = assign_monitors(layout, live, previous)
    mapping = assigned["mapping"]
    claimed = {name for name, _slot, _ident in assigned["claims"]}
    new_ids = [ident for _name, _slot, ident in assigned["claims"] if ident not in set(placed_ids)]
    floor = max(len(live), int(baseline or 0))
    return {
        "claims": [(name, slot) for name, slot, _ident in assigned["claims"]],
        "released": list(assigned["released"]),
        "mapping": mapping,
        "monitors": monitor_commands(layout, mapping),
        "place_ids": new_ids,
        "create": max(0, len(screens_by_slot(layout)) - floor),
        "remove": [name for name in live if name not in claimed],
    }


def add_screen(layout, size=PRIMARY_SIZE, metres=PRIMARY_METRES):
    screens = screens_by_slot(layout)
    if len(screens) >= MAX_SCREENS:
        raise RuntimeError(f"frametop: at most {MAX_SCREENS} Hyprland screens")
    used_slots = {int(s["slot"]) for s in screens}
    slot = next(i for i in range(1, MAX_SCREENS + 1) if i not in used_slots)
    numbers = []
    for screen in screens:
        tail = screen["id"].rsplit("-", 1)[-1]
        if tail.isdigit():
            numbers.append(int(tail))
    ident = f"hypr-{max(numbers, default=0) + 1}"
    screens.append(_screen(slot, ident, size, metres))
    layout["screens"] = screens
    return layout


def remove_screen(layout, slot):
    screens = screens_by_slot(layout)
    if len(screens) <= 1:
        raise RuntimeError("frametop: the last Hyprland screen stays")
    slot = int(slot)
    kept = [s for s in screens if int(s["slot"]) != slot]
    if len(kept) == len(screens):
        raise RuntimeError(f"frametop: no Hyprland screen {slot}")
    removed = next(s for s in screens if int(s["slot"]) == slot)
    layout["screens"] = kept
    if layout.get("primary") == removed["id"]:
        layout["primary"] = kept[0]["id"]
    return removed


def screen_by_index(layout, index):
    """index is the 0-based slot, which is what Display Settings sends."""
    slot = int(index) + 1
    for screen in layout.get("screens") or []:
        if int(screen["slot"]) == slot:
            return screen
    raise RuntimeError(f"frametop: no Hyprland screen {slot}")


def save_named(layout, name):
    name = " ".join(name.split())
    if not name:
        raise RuntimeError("frametop: the layout needs a name")
    snapshot = []
    for screen in screens_by_slot(layout):
        snapshot.append({k: screen[k] for k in screen if k in ("id", "slot", "size", "metres", "scale", "curve", "pos", "face", "roll")})
    layout.setdefault("layouts", {})[name] = {"screens": snapshot, "primary": layout.get("primary")}
    layout["active"] = name
    return name


def use_named(layout, name):
    named = (layout.get("layouts") or {}).get(name)
    if not named:
        raise RuntimeError(f"frametop: no Hyprland layout called {name!r}")
    by_id = {s["id"]: s for s in screens_by_slot(layout)}
    for saved in named.get("screens") or []:
        screen = by_id.get(saved.get("id"))
        if not screen:
            continue
        for key in ("size", "metres", "scale", "curve", "pos", "face", "roll"):
            if key in saved:
                screen[key] = saved[key]
    if named.get("primary"):
        layout["primary"] = named["primary"]
    layout["mode"] = "custom"
    layout["active"] = name


def active():
    """True when Display Settings should edit this layout instead of Plasma's."""
    forced = os.environ.get("FT_DISPLAY_COMPOSITOR", "")
    if forced == "hyprland":
        return True
    if forced == "plasma":
        return False
    runtime = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    return os.path.exists(os.path.join(runtime, "ft-hyprland-0"))


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "status"
    layout = load()
    if cmd == "shell-export":
        print(shell_export(layout))
        return 0
    if cmd == "status":
        print(shell_export(layout))
        print("primary=" + str(layout.get("primary")))
        print("path=" + str(layout_path()))
        return 0
    if cmd == "add":
        add_screen(layout)
        save(layout)
        print(shell_export(layout))
        return 0
    if cmd == "remove" and len(argv) == 3:
        remove_screen(layout, int(argv[2]))
        save(layout)
        print(shell_export(layout))
        return 0
    if cmd == "limitations":
        for line in LIMITATIONS:
            print(line)
        return 0
    print("usage: hyprland_layout.py shell-export|status|add|remove SLOT|limitations", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))

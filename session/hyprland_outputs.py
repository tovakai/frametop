#!/usr/bin/env python3
"""Keep Hyprland monitors matched to Frametop slots.

Runs inside the nested Hyprland process. A missing hyprctl or a refused
command is logged and the compositor stays up. This process does not stop
Hyprland, Quickshell, or any other desktop.
"""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import hyprland_layout as layout


def map_path():
    runtime = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    return Path(runtime) / "frametop-output-map.json"


def load_state():
    try:
        data = json.loads(map_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    return {
        "mapping": data.get("mapping") or {},
        "placed": list(data.get("placed") or []),
        "rules": data.get("rules") or {},
    }


def save_state(state):
    path = map_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"frametop: output map not saved: {exc}", file=sys.stderr)


def hyprctl(args, runner=None):
    if runner:
        return runner(args)
    proc = subprocess.run(["hyprctl", *args], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "hyprctl failed").strip())
    return proc.stdout


def monitors_from_json(text):
    data = json.loads(text)
    names = []
    for entry in data:
        name = entry.get("name")
        if name:
            names.append(name)
    return names


def step(live_names, state, screens, baseline):
    """One poll. Returns the commands a caller can apply, and the next state.

    `screens` is a layout dict. State keeps the session map and which ids
    have already been placed, so a later poll does not move those panels.
    """
    actions = layout.sync_actions(screens, live_names, state.get("mapping") or {}, state.get("placed") or [], baseline)
    commands = []
    for name in actions["remove"]:
        commands.append(("remove", name))
    for _ in range(actions["create"]):
        commands.append(("create", "wayland"))
    for name, slot in actions["claims"]:
        commands.append(("claim", f"claim {name} {slot}"))
    for rule in actions["monitors"]:
        if state.get("rules", {}).get(rule["monitor"]) == rule["eval"]:
            continue
        commands.append(("monitor", rule["eval"]))
    place_ids = []
    if actions["place_ids"]:
        # Poses are filled in by the caller when a head pose exists. The ids
        # are recorded only after the caller places them.
        place_ids = list(actions["place_ids"])
    next_state = {
        "mapping": {name: screens_id for name, screens_id in actions["mapping"].items()},
        "placed": list(state.get("placed") or []),
        "rules": dict(state.get("rules") or {}),
    }
    for rule in actions["monitors"]:
        if any(cmd[0] == "monitor" and cmd[1] == rule["eval"] for cmd in commands):
            next_state["rules"][rule["monitor"]] = rule["eval"]
    return {
        "commands": commands,
        "place_ids": place_ids,
        "state": next_state,
        "actions": actions,
        "create": actions["create"],
        "remove": actions["remove"],
    }


def note_placed(state, ids):
    placed = list(state.get("placed") or [])
    for ident in ids:
        if ident not in placed:
            placed.append(ident)
    state["placed"] = placed
    return state


def send_control(text, name=None):
    """One datagram to ft-screens. False when the compositor is not up yet."""
    name = name or os.environ.get("FT_HYPR_CONTROL") or "ft_hyprland"
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.settimeout(0.5)
    try:
        sock.bind("")
        sock.sendto(text.encode(), b"\0" + name.encode())
        return True
    except OSError:
        return False
    finally:
        sock.close()


def main():
    baseline = int(os.environ.get("FT_HYPR_OUTPUTS") or os.environ.get("FT_SCREEN_COUNT") or "1")
    state = load_state()
    while True:
        try:
            raw = hyprctl(["monitors", "-j"])
            live = monitors_from_json(raw)
            screens = layout.load()
            result = step(live, state, screens, baseline)
            for kind, arg in result["commands"]:
                if kind == "create":
                    hyprctl(["output", "create", "wayland"])
                elif kind == "remove":
                    hyprctl(["output", "remove", arg])
                elif kind == "monitor":
                    hyprctl(["eval", arg])
                elif kind == "claim":
                    send_control(arg)
            # New screens get their first pose from ft-screens (a row in front
            # of the headset). This loop does not send place: a poll must not
            # pull a panel back after the user moves it. Arrange does that.
            state = result["state"]
            state["placed"] = list(dict.fromkeys([*(state.get("placed") or []), *result["place_ids"]]))
            save_state(state)
            if len(live) >= baseline:
                baseline = max(baseline, len(screens.get("screens") or []))
        except Exception as exc:
            print(f"frametop: output sync: {exc}", file=sys.stderr)
        time.sleep(1)


if __name__ == "__main__":
    main()

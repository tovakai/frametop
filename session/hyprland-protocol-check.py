#!/usr/bin/env python3
"""Check ft-screens' advertised Wayland globals against Aquamarine 0.15.1.

Run with: wayland-info | python3 session/hyprland-protocol-check.py
Only checks global *versions*, not DMA-BUF feedback/import correctness.
"""
import re
import sys

REQUIRED = {
    "wl_compositor": 6,
    "wl_seat": 9,
    "wl_shm": 1,
    "xdg_wm_base": 6,
    "zwp_linux_dmabuf_v1": 4,
}
GLOBAL = re.compile(r"interface:\s*'([^']+)'\s*,\s*version:\s*(\d+)")


def inspect(text: str) -> list[str]:
    offered = {}
    for name, version in GLOBAL.findall(text):
        offered[name] = max(offered.get(name, 0), int(version))
    errors = []
    for name, required in REQUIRED.items():
        current = offered.get(name)
        if current is None:
            errors.append(f"MISSING {name} (requires >= {required})")
        elif current < required:
            errors.append(f"TOO OLD {name}: offered {current}, needs {required}")
        else:
            print(f"OK {name}: offered {current} (needs {required})")
    return errors


if __name__ == "__main__":
    errors = inspect(sys.stdin.read())
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        raise SystemExit(1)
    print("Frametop Wayland protocol version preflight: PASS")

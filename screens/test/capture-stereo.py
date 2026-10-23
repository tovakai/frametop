#!/usr/bin/env python3
"""One-shot Frametop/KWin screen capture to a bounded binary PPM for ft-handtest.

A snapshot is taken from the existing private Plasma session over KWin's
ScreenShot2 D-Bus interface. The script does NOT bypass KWin capture permissions,
touch compositor settings, change the desktop, or keep a recording running.

  python3 screens/test/capture-stereo.py --screen 1 --output ~/Pictures/ft-screen.ppm

If KWin refuses a non-privileged D-Bus client, capture normally through
Spectacle instead and convert that image with ImageMagick in the dev container.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import tempfile
from typing import BinaryIO

MAX_WIDTH, MAX_HEIGHT = 2048, 1152
MAX_INPUT_PIXELS = 4096 * 2304

# Qt QImage::Format (SteamOS/KWin format IDs as used by headless.sh).
BGRA = (4, 5, 6)  # RGB32, ARGB32, ARGB32_Premultiplied in little-endian memory
RGBA = (16, 17, 18)  # RGBA8888, RGBA8888_Premultiplied, RGBX8888


def find_nested_bus() -> str:
    """Read only the session bus address of our own user's nested Plasma."""
    runtime = f"/run/user/{os.getuid()}/frametop"
    for entry in Path("/proc").iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            if (entry / "comm").read_text().strip() not in (
                "plasmashell", "kwin_wayland", "startplasma-wayland"
            ):
                continue
            variables = (entry / "environ").read_bytes().split(b"\0")
            env = dict(v.split(b"=", 1) for v in variables if b"=" in v)
            if env.get(b"XDG_RUNTIME_DIR", b"").decode(errors="replace") != runtime:
                continue
            address = env.get(b"DBUS_SESSION_BUS_ADDRESS", b"").decode(errors="replace")
            if address:
                return address
        except (OSError, PermissionError, ValueError):
            continue
    raise RuntimeError(
        "Cannot locate the active Frametop Plasma D-Bus session. "
        "Start the normal Frametop desktop first, or use Spectacle to save a screenshot."
    )


def read_exact(stream: BinaryIO, amount: int) -> bytes:
    chunks = []
    remaining = amount
    while remaining:
        block = stream.read(remaining)
        if not block:
            raise ValueError("KWin screenshot ended before the expected pixel data")
        chunks.append(block)
        remaining -= len(block)
    return b"".join(chunks)


def convert_stream(
    src: BinaryIO, dst: BinaryIO, width: int, height: int, stride: int, qt_format: int,
    max_width: int = MAX_WIDTH, max_height: int = MAX_HEIGHT,
) -> tuple[int, int]:
    """Convert KWin's raw QImage rows to RGB P6, optionally nearest-downscaled.

    Read the input once, a scanline at a time. No extra libraries, no
    unbounded allocation, and no interpretation of PNG/JPEG payloads.
    """
    if (qt_format not in BGRA + RGBA or width < 1 or height < 1 or
            max_width < 1 or max_height < 1 or
            width * height > MAX_INPUT_PIXELS or
            stride < width * 4 or stride > width * 8):
        raise ValueError("unsupported KWin pixel format or screenshot dimensions")

    scale = min(1.0, max_width / width, max_height / height)
    out_w = max(1, int(width * scale))
    out_h = max(1, int(height * scale))
    dst.write(f"P6\n{out_w} {out_h}\n255\n".encode("ascii"))

    order = (2, 1, 0) if qt_format in BGRA else (0, 1, 2)
    sample_x = [4 * min(width - 1, (x * width) // out_w) for x in range(out_w)]
    out_y = 0
    for y in range(height):
        row = read_exact(src, stride)
        if out_y >= out_h or y != (out_y * height) // out_h:
            continue
        rgb = bytearray(out_w * 3)
        if out_w == width:
            rgb[0::3] = row[order[0]:width * 4:4]
            rgb[1::3] = row[order[1]:width * 4:4]
            rgb[2::3] = row[order[2]:width * 4:4]
        else:
            for x, pos in enumerate(sample_x):
                rgb[x * 3:x * 3 + 3] = bytes((row[pos + order[0]],
                                             row[pos + order[1]],
                                             row[pos + order[2]]))
        dst.write(rgb)
        out_y += 1
    if out_y != out_h:
        raise ValueError("not enough screenshot rows to fill output")
    return out_w, out_h


def capture(screen: int, output: Path) -> tuple[int, int]:
    import dbus  # SteamOS host's python3-dbus; optional in offline tests

    bus = dbus.bus.BusConnection(find_nested_bus())
    shot = dbus.Interface(
        bus.get_object("org.kde.KWin", "/org/kde/KWin/ScreenShot2"),
        "org.kde.KWin.ScreenShot2",
    )
    r, w = os.pipe()
    result = None
    try:
        fd = dbus.types.UnixFd(w)
        os.close(w)
        w = -1
        opts = dbus.Dictionary(
            {"include-cursor": False, "native-resolution": True}, signature="sv"
        )
        # KWin is free to deny this request. We deliberately do not change
        # KWIN_SCREENSHOT_NO_PERMISSION_CHECKS or modify the running process.
        result = shot.CaptureScreen(f"WL-{screen - 1}", opts, fd, timeout=15)
        del fd  # allow KWin to close its write end; headless.sh does the same
        width = int(result["width"])
        height = int(result["height"])
        stride = int(result["stride"])
        fmt = int(result["format"])

        output.parent.mkdir(parents=True, exist_ok=True)
        with os.fdopen(r, "rb") as source:
            r = -1
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=".framedepth-", suffix=".ppm",
                dir=output.parent, delete=False
            ) as tmp:
                temp_path = Path(tmp.name)
                try:
                    size = convert_stream(source, tmp, width, height, stride, fmt)
                    tmp.flush()
                    os.fsync(tmp.fileno())
                except Exception:
                    temp_path.unlink(missing_ok=True)
                    raise
        temp_path.replace(output)
        return size
    finally:
        if w >= 0:
            os.close(w)
        if r >= 0:
            os.close(r)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screen", type=int, default=1, help="1-based Frametop screen")
    parser.add_argument(
        "--output", type=Path,
        default=Path.home() / "Pictures" / "frametop-stereo-screen1.ppm",
        help="destination P6 image (private local file)",
    )
    args = parser.parse_args()
    if not 1 <= args.screen <= 9:
        parser.error("--screen must be in 1..9")
    try:
        w, h = capture(args.screen, args.output.expanduser())
        print(f"Captured screen {args.screen} to {args.output.expanduser()} ({w}x{h}, P6)")
    except Exception as exc:
        print(f"FrameDepth screenshot failed: {exc}", file=sys.stderr)
        print(
            "KWin may require an authorized screenshot client. Alternative: "
            "save a screenshot with Spectacle inside the running Frametop desktop, "
            "then convert it to binary PPM using the dev container's magick. "
            "Do not disable KWin's screenshot permission checks.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

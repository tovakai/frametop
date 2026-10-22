"""Hardware-free preflight tests for the experimental Hyprland session.

These must never start SteamVR, a container, or a nested compositor.
"""

import os
import socket
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENTRY = ROOT / "session" / "frametop-session.sh"
HYPRLAND = ROOT / "session" / "frametop-hyprland.sh"


def run(script: Path, tmp_path: Path, **values: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["HOME"] = str(tmp_path)
    env["XDG_RUNTIME_DIR"] = str(tmp_path)
    env.update(values)
    return subprocess.run(
        ["bash", str(script)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )


def test_unknown_desktop_rejected_without_starting_desktop(tmp_path: Path):
    result = run(ENTRY, tmp_path, FT_DESKTOP_SESSION="bogus")
    assert result.returncode == 2
    assert "unknown desktop session" in result.stderr


def test_hyprland_rejects_gamescope_before_start(tmp_path: Path):
    result = run(
        ENTRY, tmp_path, FT_DESKTOP_SESSION="hyprland", FT_BACKEND="gamescope"
    )
    assert result.returncode == 2
    assert "requires BACKEND=screens" in result.stderr


def test_hyprland_requires_ft_screens_socket(tmp_path: Path):
    result = run(
        HYPRLAND,
        tmp_path,
        WAYLAND_DISPLAY=str(tmp_path / "does-not-exist"),
    )
    assert result.returncode == 2
    assert "Wayland socket" in result.stderr


def test_hyprland_rejects_invalid_screen_counts(tmp_path: Path):
    sock_path = tmp_path / "ft-screens-0"
    with socket.socket(socket.AF_UNIX) as sock:
        sock.bind(str(sock_path))
        for count in ("0", "-1", "nope", "25"):
            result = run(
                HYPRLAND,
                tmp_path,
                WAYLAND_DISPLAY=str(sock_path),
                FT_SCREEN_COUNT=count,
            )
            assert result.returncode == 2
            assert "invalid FT_SCREEN_COUNT" in result.stderr


def test_hyprland_requires_config_file(tmp_path: Path):
    sock_path = tmp_path / "ft-screens-0"
    with socket.socket(socket.AF_UNIX) as sock:
        sock.bind(str(sock_path))
        result = run(
            HYPRLAND,
            tmp_path,
            WAYLAND_DISPLAY=str(sock_path),
            FT_SCREEN_COUNT="1",
            FT_HYPRLAND_CONFIG=str(tmp_path / "missing.conf"),
        )
    assert result.returncode == 2
    assert "configuration not found" in result.stderr

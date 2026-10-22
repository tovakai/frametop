"""Offline preflight tests for the experimental Hyprland session.

They must never start SteamVR, a container, or a nested compositor.
"""

import os
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENTRY = ROOT / "session" / "frametop-session.sh"
HYPRLAND = ROOT / "session" / "frametop-hyprland.sh"


def run(script: Path, home: Path, **values: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["XDG_RUNTIME_DIR"] = str(home)
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


class HyprlandPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)

    def socket_path(self):
        sock_path = self.home / "ft-screens-0"
        sock = socket.socket(socket.AF_UNIX)
        sock.bind(str(sock_path))
        self.addCleanup(sock.close)
        return sock_path

    def test_unknown_desktop_rejected_before_start(self):
        result = run(ENTRY, self.home, FT_DESKTOP_SESSION="bogus")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("unknown desktop session", result.stderr)

    def test_hyprland_rejects_gamescope_before_start(self):
        result = run(
            ENTRY, self.home, FT_DESKTOP_SESSION="hyprland", FT_BACKEND="gamescope"
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("requires BACKEND=screens", result.stderr)

    def test_hyprland_requires_ft_screens_socket(self):
        result = run(
            HYPRLAND, self.home, WAYLAND_DISPLAY=str(self.home / "does-not-exist")
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("Wayland socket", result.stderr)

    def test_hyprland_rejects_invalid_screen_counts(self):
        sock_path = self.socket_path()
        for count in ("0", "-1", "nope", "25"):
            with self.subTest(count=count):
                result = run(
                    HYPRLAND, self.home, WAYLAND_DISPLAY=str(sock_path),
                    FT_SCREEN_COUNT=count
                )
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("invalid FT_SCREEN_COUNT", result.stderr)

    def test_hyprland_requires_config_file(self):
        sock_path = self.socket_path()
        result = run(
            HYPRLAND, self.home, WAYLAND_DISPLAY=str(sock_path),
            FT_SCREEN_COUNT="1", FT_HYPRLAND_CONFIG=str(self.home / "missing.conf")
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("configuration not found", result.stderr)

    def test_minimal_config_uses_lua(self):
        config = (ROOT / "session" / "hyprland-minimal.lua").read_text()
        self.assertIn("hl.monitor(", config)
        self.assertIn('hl.on("hyprland.start"', config)
        self.assertIn("hl.bind(", config)
        launcher = HYPRLAND.read_text()
        self.assertIn("hyprland-minimal.lua", launcher)
        self.assertIn("HYPRLAND_NO_SD_VARS=1", launcher)
        self.assertIn("HYPRLAND_NO_SD_TARGET=1", launcher)
        self.assertIn("mktemp -d", launcher)

    def test_output_startup_rejects_bad_count(self):
        script = ROOT / "session" / "hyprland-on-start.sh"
        result = run(script, self.home, FT_SCREEN_COUNT="0")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("invalid FT_SCREEN_COUNT", result.stderr)

    def test_output_startup_creates_only_extra_wayland_outputs(self):
        binpath = self.home / "bin"
        binpath.mkdir()
        log = self.home / "calls.log"
        hyprctl = binpath / "hyprctl"
        hyprctl.write_text('#!/bin/sh\necho "$*" >> "$FT_TEST_LOG"\n')
        hyprctl.chmod(0o755)
        foot = binpath / "foot"
        foot.write_text('#!/bin/sh\necho "terminal" >> "$FT_TEST_LOG"\n')
        foot.chmod(0o755)
        script = ROOT / "session" / "hyprland-on-start.sh"
        result = run(
            script, self.home, FT_SCREEN_COUNT="3",
            PATH=str(binpath) + os.pathsep + os.environ.get("PATH", ""),
            FT_TEST_LOG=str(log),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            log.read_text().splitlines(),
            ["output create wayland", "output create wayland", "terminal"],
        )


if __name__ == "__main__":
    unittest.main()

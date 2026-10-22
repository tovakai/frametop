"""Offline checks for the Frame end-4 session and controller action script.

These do not start Hyprland, Quickshell, SteamVR, or the input relay.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "input"))
import controller_chords  # noqa: E402

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

hyprland_key_forward = _load("hyprland_key_forward", ROOT / "session" / "hyprland-key-forward.py")

SESSION = ROOT / "session"


def run(script: Path, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
    merged = dict(os.environ)
    merged.update(env)
    return subprocess.run(
        ["bash", str(script), *args],
        cwd=ROOT,
        env=merged,
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )


class FrameDesktopTests(unittest.TestCase):
    def test_profile_matches_the_right_controller_layout(self):
        profile = json.loads((SESSION / "frame-controller-profile.json").read_text())
        self.assertFalse(profile["controller_in_games"])
        chords = controller_chords.ControllerChords(profile["controller_chords"])
        self.assertEqual(
            chords.bind_names(),
            ["right/trigger", "right/x", "right/b", "right/a", "right/y"],
        )
        self.assertNotIn("right/bumper", chords.bind_names())
        self.assertEqual(chords.event("right/x", 1), ["command:frame-desktop-action workspace-prev"])
        self.assertEqual(chords.event("right/b", 1), ["command:frame-desktop-action workspace-next"])
        chords.event("right/x", 0)
        chords.event("right/b", 0)
        self.assertEqual(chords.event("right/a", 1), ["command:frame-desktop-action window-next"])
        chords.event("right/a", 0)
        self.assertEqual(chords.event("right/y", 1), ["command:frame-desktop-action window-prev"])
        chords = controller_chords.ControllerChords(profile["controller_chords"])
        chords.event("right/trigger", 1)
        self.assertEqual(chords.event("right/a", 1), ["command:frame-desktop-action files"])
        chords.event("right/a", 0)
        self.assertEqual(chords.event("right/b", 1), ["command:frame-desktop-action browser"])
        chords.event("right/b", 0)
        self.assertEqual(chords.event("right/x", 1), ["command:frame-desktop-action terminal"])
        chords.event("right/x", 0)
        self.assertEqual(chords.event("right/y", 1), ["command:frame-desktop-action launcher"])
        self.assertEqual(chords.click_down(), ["command:frame-desktop-action close"])

    def test_keyboard_shortcuts_stay_in_the_user_config(self):
        frame = (SESSION / "hyprland-frame.lua").read_text()
        self.assertIn('dofile(user_entry)', frame)
        self.assertNotIn("hl.bind(", (SESSION / "frame-hypr" / "hyprland" / "execs.lua").read_text())
        startup = (SESSION / "frame-hypr" / "hyprland" / "execs.lua").read_text()
        code = "\n".join(line for line in startup.splitlines() if not line.strip().startswith("--"))
        self.assertNotIn("hypridle", code)
        self.assertNotIn("systemctl", code)
        self.assertNotIn("brightnessctl", code)
        self.assertIn("frame-quickshell.sh", code)

    def test_quickshell_absence_does_not_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            result = run(
                SESSION / "frame-quickshell.sh",
                HOME=str(home),
                FT_USER_CONFIG_HOME=str(home / "config"),
                PATH="/usr/bin:/bin",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(
            "qs is not installed" in result.stderr or "is not on this machine" in result.stderr,
            result.stderr,
        )

    def test_actions_are_single_hyprctl_requests(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = root / "ftH.test"
            (runtime / "hypr" / "sig").mkdir(parents=True)
            log = root / "hyprctl.log"
            bindir = root / "bin"
            bindir.mkdir()
            hyprctl = bindir / "hyprctl"
            hyprctl.write_text('#!/bin/sh\necho "$@" >> "$FT_TEST_LOG"\n')
            hyprctl.chmod(0o755)
            env = dict(
                HOME=str(root),
                FT_HYPR_RUNTIME=str(runtime),
                FT_TEST_LOG=str(log),
                FT_USER_CONFIG_HOME=str(root / "unused"),
                PATH=str(bindir) + os.pathsep + "/usr/bin:/bin",
            )
            for action, line in (
                ("workspace-prev", "dispatch workspace r-1"),
                ("workspace-next", "dispatch workspace r+1"),
                ("window-prev", "dispatch movetoworkspacesilent r-1"),
                ("window-next", "dispatch movetoworkspacesilent r+1"),
                ("close", "dispatch closewindow"),
            ):
                with self.subTest(action=action):
                    log.write_text("")
                    result = run(SESSION / "frame-desktop-action.sh", action, **env)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(log.read_text().strip(), line)
            log.write_text("")
            qs = bindir / "qs"
            qs.write_text('#!/bin/sh\necho "$@" >> "$FT_TEST_LOG"\n')
            qs.chmod(0o755)
            result = run(SESSION / "frame-desktop-action.sh", "launcher", **env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(log.read_text().strip(), "-c ii ipc call search toggle")
            result = run(SESSION / "frame-desktop-action.sh", "nope", **env)
            self.assertEqual(result.returncode, 2)

    def test_forwarder_keeps_keys_and_drops_layout_commands(self):
        self.assertTrue(hyprland_key_forward.allowed(b"key 28 1"))
        self.assertTrue(hyprland_key_forward.allowed(b"click frametop.screen.1"))
        self.assertTrue(hyprland_key_forward.allowed(b"chord-click 1"))
        self.assertTrue(hyprland_key_forward.allowed(b"up"))
        self.assertFalse(hyprland_key_forward.allowed(b"size 1 1280 720"))
        self.assertFalse(hyprland_key_forward.allowed(b"pause on"))


if __name__ == "__main__":
    unittest.main()

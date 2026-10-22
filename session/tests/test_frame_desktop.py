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
        script = SESSION / "frame-desktop-action.sh"
        self.assertTrue(script.is_file() and os.access(script, os.X_OK))
        self.assertEqual(chords.event("right/x", 1), ["command:frame-desktop-action.sh workspace-prev"])
        self.assertEqual(chords.event("right/b", 1), ["command:frame-desktop-action.sh workspace-next"])
        chords.event("right/x", 0)
        chords.event("right/b", 0)
        self.assertEqual(chords.event("right/a", 1), ["command:frame-desktop-action.sh window-next"])
        chords.event("right/a", 0)
        self.assertEqual(chords.event("right/y", 1), ["command:frame-desktop-action.sh window-prev"])
        chords = controller_chords.ControllerChords(profile["controller_chords"])
        chords.event("right/trigger", 1)
        self.assertEqual(chords.event("right/a", 1), ["command:frame-desktop-action.sh files"])
        chords.event("right/a", 0)
        self.assertEqual(chords.event("right/b", 1), ["command:frame-desktop-action.sh browser"])
        chords.event("right/b", 0)
        self.assertEqual(chords.event("right/x", 1), ["command:frame-desktop-action.sh terminal"])
        chords.event("right/x", 0)
        self.assertEqual(chords.event("right/y", 1), ["command:frame-desktop-action.sh launcher"])
        self.assertEqual(chords.click_down(), ["command:frame-desktop-action.sh close"])
        action = (SESSION / "frame-desktop-action.sh").read_text()
        self.assertNotIn("ftH.*", action)
        self.assertNotIn("ls -d", action)
        self.assertIn("scripts/in-box", action)

    def test_keyboard_shortcuts_stay_in_the_user_config(self):
        frame = (SESSION / "hyprland-frame.lua").read_text()
        self.assertIn("FT_HYPR_CONFIG_ROOT", frame)
        self.assertIn('dofile(user_entry)', frame)
        self.assertNotIn("hl.bind(", (SESSION / "frame-hypr" / "hyprland" / "execs.lua").read_text())
        startup = (SESSION / "frame-hypr" / "hyprland" / "execs.lua").read_text()
        code = "\n".join(line for line in startup.splitlines() if not line.strip().startswith("--"))
        self.assertNotIn("hypridle", code)
        self.assertNotIn("systemctl", code)
        self.assertNotIn("brightnessctl", code)
        self.assertIn("frame-quickshell.sh", code)
        launcher = (SESSION / "frametop-session.sh").read_text()
        self.assertIn("ft-hyprland-0", launcher)
        self.assertIn("FT_OVERLAY_PREFIX=frametop.hypr", launcher)
        self.assertIn("Plasma's ft-screens", launcher)
        self.assertIn("keyboard hyprland", (ROOT / "screens" / "compositor.c").read_text())
        guard = (SESSION / "frame-hypr" / "hyprland" / "services" / "create_custom_config.lua").read_text()
        guard_code = "\n".join(line for line in guard.splitlines() if not line.strip().startswith("--"))
        self.assertNotIn("os.execute", guard_code)
        self.assertNotIn("HOME", guard_code)

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

    def test_actions_use_the_route_and_the_container_runner(self):
        import desktop_route

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = root / "runtime"
            (runtime / "hypr" / "sig").mkdir(parents=True)
            config_home = root / "stage"
            config_home.mkdir()
            route = root / "frametop-hyprland.route"
            route.write_text(
                f"pid={os.getpid()}\ncontrol=ft_hyprland\nruntime={runtime}\n"
                f"wayland=/tmp/ft-hyprland-test\nconfig_home={config_home}\n"
            )
            self.assertEqual(desktop_route.signature(str(runtime)), ("sig", None))
            self.assertIsNotNone(desktop_route.desktop_target(str(route), plasma=False))
            self.assertIsNone(desktop_route.desktop_target(str(route), plasma=True))
            log = root / "calls.log"
            bindir = root / "bin"
            bindir.mkdir()
            tool = '#!/bin/sh\necho "$0 $*" >> "$FT_TEST_LOG"\necho "runtime=$XDG_RUNTIME_DIR sig=$HYPRLAND_INSTANCE_SIGNATURE config=$XDG_CONFIG_HOME" >> "$FT_TEST_LOG"\n'
            for name in ("hyprctl", "qs", "foot", "dolphin", "google-chrome-stable"):
                path = bindir / name
                path.write_text(tool)
                path.chmod(0o755)
            runner = root / "runner"
            runner.write_text("#!/bin/sh\nexec \"$@\"\n")
            runner.chmod(0o755)
            env = dict(
                HOME=str(root),
                FT_HYPR_ROUTE=str(route),
                FT_TEST_LOG=str(log),
                FT_DESKTOP_RUNNER=str(runner),
                FT_DESKTOP_FOREGROUND="1",
                PATH=str(bindir) + os.pathsep + "/usr/bin:/bin",
            )
            expected = {
                "workspace-prev": "dispatch workspace r-1",
                "workspace-next": "dispatch workspace r+1",
                "window-prev": "dispatch movetoworkspacesilent r-1",
                "window-next": "dispatch movetoworkspacesilent r+1",
                "close": "dispatch closewindow",
                "terminal": None,
                "files": None,
                "browser": None,
                "launcher": "-c ii ipc --any-display call search toggle",
            }
            for action, line in expected.items():
                with self.subTest(action=action):
                    log.write_text("")
                    result = run(SESSION / "frame-desktop-action.sh", action, **env)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    text = log.read_text()
                    self.assertIn(f"runtime={runtime}", text)
                    self.assertIn("sig=sig", text)
                    self.assertIn(f"config={config_home}", text)
                    if line:
                        self.assertIn(line, text)
                    elif action == "terminal":
                        self.assertIn("foot", text)
                    elif action == "files":
                        self.assertIn("dolphin", text)
                    else:
                        self.assertIn("google-chrome-stable", text)
            log.write_text("")
            result = run(SESSION / "frame-desktop-action.sh", "nope", **env)
            self.assertEqual(result.returncode, 2)
            route.write_text(route.read_text().replace(f"pid={os.getpid()}", "pid=99999999"))
            log.write_text("")
            result = run(SESSION / "frame-desktop-action.sh", "close", **env)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(log.read_text(), "")
            (runtime / "hypr" / "other").mkdir()
            route.write_text(
                f"pid={os.getpid()}\ncontrol=ft_hyprland\nruntime={runtime}\n"
                f"wayland=/tmp/ft-hyprland-test\nconfig_home={config_home}\n"
            )
            result = run(SESSION / "frame-desktop-action.sh", "close", **env)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("more than one", result.stderr)
            missing = root / "missing.route"
            result = run(SESSION / "frame-desktop-action.sh", "close", FT_HYPR_ROUTE=str(missing), HOME=str(root))
            self.assertEqual(result.returncode, 2, result.stderr)

    def test_forwarder_keeps_keys_and_drops_layout_commands(self):
        self.assertTrue(hyprland_key_forward.allowed(b"key 28 1"))
        self.assertTrue(hyprland_key_forward.allowed(b"click frametop.screen.1"))
        self.assertTrue(hyprland_key_forward.allowed(b"chord-click 1"))
        self.assertTrue(hyprland_key_forward.allowed(b"up"))
        self.assertFalse(hyprland_key_forward.allowed(b"size 1 1280 720"))
        self.assertFalse(hyprland_key_forward.allowed(b"pause on"))


if __name__ == "__main__":
    unittest.main()

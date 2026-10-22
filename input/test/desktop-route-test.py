#!/usr/bin/env python3
"""Route file and chord-binding policy. No compositor and no input relay."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import desktop_route  # noqa: E402


class DesktopRouteTests(unittest.TestCase):
    def write_route(self, root, pid, runtime, extra=""):
        (runtime / "hypr" / "sig").mkdir(parents=True)
        route = root / "frametop-hyprland.route"
        route.write_text(
            f"pid={pid}\ncontrol=ft_hyprland\nruntime={runtime}\n"
            f"wayland=/tmp/ft-hyprland-test\nconfig_home={root}/stage\n{extra}"
        )
        return route

    def test_live_route_is_one_session(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = root / "runtime"
            route = self.write_route(root, os.getpid(), runtime)
            info = desktop_route.desktop_target(route, plasma=False)
            self.assertEqual(info["control"], "ft_hyprland")
            self.assertEqual(info["runtime"], str(runtime))
            self.assertEqual(desktop_route.signature(str(runtime))[0], "sig")
            self.assertIsNone(desktop_route.desktop_target(route, plasma=True))
            self.assertEqual(desktop_route.live_route(route)["control"], "ft_hyprland")

    def test_dead_pid_and_ambiguous_signature_are_not_a_session(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = root / "runtime"
            route = self.write_route(root, 2**30, runtime)
            self.assertIsNone(desktop_route.desktop_target(route, plasma=False))
            (runtime / "hypr" / "other").mkdir()
            route.write_text(route.read_text().replace(f"pid={2**30}", f"pid={os.getpid()}"))
            self.assertIsNone(desktop_route.signature(str(runtime))[0])
            self.assertIn("more than one", desktop_route.signature(str(runtime))[1])
            with self.assertRaises(SystemExit) as caught:
                desktop_route.export_lines(route)
            self.assertEqual(caught.exception.code, 2)

    def test_chords_bind_only_for_the_experimental_desktop(self):
        ok = dict(route_ok=True, desktop_focused=True, paused=False, game=False,
                  capturing=False, controller_in_games=False)
        self.assertTrue(desktop_route.chords_should_bind(**ok))
        for key in ("route_ok", "desktop_focused"):
            blocked = dict(ok)
            blocked[key] = False
            self.assertFalse(desktop_route.chords_should_bind(**blocked))
        for key in ("paused", "game", "capturing", "controller_in_games"):
            blocked = dict(ok)
            blocked[key] = True
            self.assertFalse(desktop_route.chords_should_bind(**blocked))


if __name__ == "__main__":
    unittest.main()

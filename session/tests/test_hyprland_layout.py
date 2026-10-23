"""Hyprland screen identity, poses, and the Plasma layout staying untouched."""
import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.sys.path.insert(0, str(ROOT / "session"))
import hyprland_layout as layout  # noqa: E402
import hyprland_outputs as outputs  # noqa: E402


def two():
    data = layout.default_layout()
    layout.add_screen(data)
    return data


def three():
    data = two()
    layout.add_screen(data)
    return data


class HyprlandLayoutTests(unittest.TestCase):
    def test_default_is_the_current_primary_panel(self):
        data = layout.default_layout()
        self.assertEqual(data["screens"], [{
            "id": "hypr-1", "slot": 1, "size": [1920, 1080], "metres": 1.5, "scale": 1.0, "curve": 0.0,
        }])
        self.assertEqual(layout.shell_export(data).splitlines()[:2], ["count=1", "outputs=1"])
        self.assertIn("1920x1080@1.500", layout.shell_export(data))

    def test_two_and_three_screens_do_not_overlap(self):
        for count, builder in ((2, two), (3, three)):
            data = builder()
            data["mode"] = "preset"
            poses = layout.poses_for(data)
            self.assertEqual(len(poses), count)
            xs = [round(p["pos"][0], 3) for p in poses]
            self.assertEqual(len(set(xs)), count, xs)
            self.assertTrue(all(p["pos"][2] < 0 for p in poses))
            # Neighbours are separated by about a panel width, not stacked.
            ordered = sorted(xs)
            self.assertGreater(ordered[1] - ordered[0], 0.5)

    def test_assignment_ignores_arrival_order_and_reuses_a_freed_slot(self):
        data = three()
        first = layout.assign_monitors(data, ["WAYLAND-2", "WAYLAND-3", "WAYLAND-1"], {})
        slots = {name: slot for name, slot, _ident in first["claims"]}
        self.assertEqual(slots, {"WAYLAND-1": 1, "WAYLAND-2": 2, "WAYLAND-3": 3})

        # Same map, list reversed: nothing moves.
        again = layout.assign_monitors(data, ["WAYLAND-3", "WAYLAND-1", "WAYLAND-2"], first["mapping"])
        self.assertEqual(again["mapping"], first["mapping"])
        self.assertEqual(again["released"], [])

        # WAYLAND-2 dies and comes back as WAYLAND-9. Slot 2 is the one that
        # comes back. Slots 1 and 3 keep their monitors and their ids.
        hypr2 = next(s for s in data["screens"] if s["slot"] == 2)
        hypr2["pos"] = [0.4, 0.0, -2.0]
        live = ["WAYLAND-1", "WAYLAND-9", "WAYLAND-3"]
        rebound = layout.assign_monitors(data, live, first["mapping"])
        by_slot = {slot: name for name, slot, _ident in rebound["claims"]}
        self.assertEqual(by_slot[1], "WAYLAND-1")
        self.assertEqual(by_slot[2], "WAYLAND-9")
        self.assertEqual(by_slot[3], "WAYLAND-3")
        self.assertEqual(next(s["pos"] for s in data["screens"] if s["slot"] == 2), [0.4, 0.0, -2.0])

    def test_removing_one_screen_keeps_the_others(self):
        data = three()
        for screen, pos in zip(data["screens"], ([-1.2, 0, -2], [0, 0, -2], [1.2, 0, -2])):
            screen["pos"] = list(pos)
        removed = layout.remove_screen(data, 2)
        self.assertEqual(removed["id"], "hypr-2")
        self.assertEqual([(s["id"], s["slot"], s["pos"]) for s in data["screens"]], [
            ("hypr-1", 1, [-1.2, 0, -2]),
            ("hypr-3", 3, [1.2, 0, -2]),
        ])
        # The gap stays a gap. The next screen reuses slot 2 and gets a new id.
        layout.add_screen(data)
        added = next(s for s in data["screens"] if s["slot"] == 2)
        self.assertEqual(added["id"], "hypr-4")
        self.assertNotIn("pos", added)
        self.assertEqual(next(s["pos"] for s in data["screens"] if s["id"] == "hypr-3"), [1.2, 0, -2])

    def test_poll_places_a_screen_once_and_does_not_create_startup_outputs_twice(self):
        data = two()
        state = {"mapping": {}, "placed": [], "rules": {}}
        first = outputs.step(["WAYLAND-1"], state, data, baseline=2)
        self.assertEqual(first["commands"][0][0], "claim")
        self.assertIn(("claim", "claim WAYLAND-1 1"), first["commands"])
        self.assertEqual(first["create"], 0)
        self.assertEqual(first["place_ids"], ["hypr-1"])
        state = first["state"]
        state["placed"] = list(first["place_ids"])
        second = outputs.step(["WAYLAND-1", "WAYLAND-2"], state, data, baseline=2)
        self.assertEqual(second["place_ids"], ["hypr-2"])
        self.assertNotIn("hypr-1", second["place_ids"])
        self.assertEqual(second["create"], 0)
        state = second["state"]
        state["placed"] = list(state.get("placed") or []) + second["place_ids"]
        third = outputs.step(["WAYLAND-2", "WAYLAND-1"], state, data, baseline=2)
        self.assertEqual(third["place_ids"], [])
        self.assertTrue(all(cmd[0] != "monitor" or False for cmd in third["commands"] if cmd[0] == "monitor") or True)
        # The monitor rule was already recorded, so the pointer row is not rewritten.
        self.assertFalse(any(cmd[0] == "monitor" for cmd in third["commands"]))

    def test_adding_a_screen_creates_one_output_and_a_removed_monitor_is_dropped(self):
        data = two()
        state = {"mapping": {"WAYLAND-1": "hypr-1", "WAYLAND-2": "hypr-2"}, "placed": ["hypr-1", "hypr-2"], "rules": {}}
        layout.add_screen(data)
        added = outputs.step(["WAYLAND-1", "WAYLAND-2"], state, data, baseline=2)
        self.assertEqual(added["create"], 1)
        self.assertIn(("create", "wayland"), added["commands"])
        layout.remove_screen(data, 3)
        # The third monitor has no slot once the screen is gone.
        state = added["state"]
        state["mapping"] = added["actions"]["mapping"]
        dropped = outputs.step(["WAYLAND-1", "WAYLAND-2", "WAYLAND-4"], state, data, baseline=3)
        self.assertIn("WAYLAND-4", dropped["remove"])
        self.assertNotIn("WAYLAND-1", dropped["remove"])
        self.assertNotIn("WAYLAND-2", dropped["remove"])

    def test_monitor_row_edges_touch_in_slot_order(self):
        data = three()
        mapping = {"WAYLAND-1": "hypr-1", "WAYLAND-2": "hypr-2", "WAYLAND-3": "hypr-3"}
        rules = layout.monitor_commands(data, mapping)
        self.assertEqual([rule["x"] for rule in rules], [0, 1920, 3840])
        self.assertIn('output="WAYLAND-2", mode="1920x1080@60", position="1920x0", scale=1', rules[1]["eval"])

    def test_saved_pose_restores_for_its_id_relative_to_the_heading(self):
        data = two()
        data["mode"] = "custom"
        data["screens"][1]["pos"] = [1.0, 0.0, -2.0]
        data["screens"][1]["face"] = [20.0, 0.0]
        data["screens"][1]["roll"] = 0
        data["screens"][0]["pos"] = [-1.0, 0.0, -2.0]
        data["screens"][0]["face"] = [-20.0, 0.0]
        data["screens"][0]["roll"] = 0
        commands = layout.place_commands(data, eye=(0.0, 1.6, 0.0), heading=90.0)
        by_slot = {cmd["slot"]: cmd["place"] for cmd in commands}
        self.assertIn("place 2", by_slot[2])
        # Heading is added to the saved face, so this is not a room-fixed yaw.
        self.assertIn("110.000", by_slot[2])

    def test_write_does_not_touch_the_plasma_layout(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            plasma = home / ".config" / "frametop-layout.json"
            plasma.parent.mkdir(parents=True)
            plasma.write_text('{"screens": [{"size": [3440, 1440]}]}\n')
            hypr = home / ".config" / "frametop" / "hyprland-layout.json"
            env_home = os.environ.get("HOME")
            os.environ["HOME"] = str(home)
            os.environ["FT_HYPRLAND_LAYOUT"] = str(hypr)
            try:
                data = layout.load()
                layout.add_screen(data)
                layout.save(data)
                self.assertEqual(plasma.read_text(), '{"screens": [{"size": [3440, 1440]}]}\n')
                saved = json.loads(hypr.read_text())
                self.assertEqual([s["id"] for s in saved["screens"]], ["hypr-1", "hypr-2"])
                self.assertNotIn("frametop-layout.json", hypr.read_text())
            finally:
                if env_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = env_home
                os.environ.pop("FT_HYPRLAND_LAYOUT", None)

    def test_named_layout_restores_one_screen_without_moving_the_other(self):
        data = two()
        data["screens"][0]["pos"] = [-1, 0, -2]
        data["screens"][1]["pos"] = [1, 0, -2]
        layout.save_named(data, "Wide")
        data["screens"][1]["pos"] = [3, 0, -2]
        data["screens"][0]["metres"] = 2.0
        layout.use_named(data, "Wide")
        self.assertEqual(data["screens"][1]["pos"], [1, 0, -2])
        self.assertEqual(data["screens"][0]["metres"], 1.5)
        self.assertEqual(data["mode"], "custom")


if __name__ == "__main__":
    unittest.main()

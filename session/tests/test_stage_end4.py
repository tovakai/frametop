"""The end-4 stage copy stays out of ~/.config and skips secrets."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "stage_end4", Path(__file__).resolve().parents[1] / "stage-end4.py"
)
stage_end4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stage_end4)


class StageEnd4Tests(unittest.TestCase):
    def test_copy_keeps_internal_links_and_skips_secrets(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            hypr = root / "hypr"
            (hypr / "hyprland").mkdir(parents=True)
            (hypr / "hyprland.lua").write_text("hl = {}\n")
            (hypr / "backup-old.lua").write_text("nope\n")
            (hypr / "token.pem").write_text("secret\n")
            (hypr / "key.lua").write_text('local x = "BEGIN PRIVATE KEY"\n')
            icon = hypr / "hyprland" / "icon.svg"
            icon.write_text("<svg/>\n")
            link = hypr / "alias.svg"
            link.symlink_to("hyprland/icon.svg")
            outside = root / "outside.txt"
            outside.write_text("nope\n")
            (hypr / "escape.svg").symlink_to(outside)
            qs = root / "ii"
            (qs / ".chatgpt-integration").mkdir(parents=True)
            (qs / ".chatgpt-integration" / "manifest.json").write_text("{}\n")
            (qs / "shell.qml").write_text("import Quickshell\n")
            dest = root / "repo" / "stage" / "config"
            notes = stage_end4.stage(hypr, qs, dest, replace=False)
            self.assertTrue((dest / "hypr" / "hyprland.lua").is_file())
            self.assertTrue((dest / "hypr" / "alias.svg").is_symlink())
            self.assertEqual(os.readlink(dest / "hypr" / "alias.svg"), "hyprland/icon.svg")
            self.assertFalse((dest / "hypr" / "escape.svg").exists())
            self.assertFalse((dest / "hypr" / "backup-old.lua").exists())
            self.assertFalse((dest / "hypr" / "token.pem").exists())
            self.assertFalse((dest / "hypr" / "key.lua").exists())
            self.assertFalse((dest / "quickshell" / "ii" / ".chatgpt-integration").exists())
            self.assertTrue((dest / "quickshell" / "ii" / "shell.qml").is_file())
            self.assertTrue(any("secret" in note or "skip" in note for note in notes))
            with self.assertRaises(SystemExit):
                stage_end4.stage(hypr, qs, dest, replace=False)
            home_dest = Path.home() / ".config" / "hypr"
            self.assertTrue(stage_end4.user_config_blocked(home_dest))


if __name__ == "__main__":
    unittest.main()

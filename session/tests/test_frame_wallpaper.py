"""Offline checks for the Frame wallpaper helper.

These do not download an image, open a dialog, or talk to Hyprland.
"""
import importlib.util
import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "session" / "frame-wallpaper.sh"


def _load_stage():
    spec = importlib.util.spec_from_file_location("stage_end4", ROOT / "session" / "stage-end4.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _bash(script: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    merged = dict(os.environ)
    merged.update(env)
    return subprocess.run(
        ["bash", "-c", script],
        env=merged,
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )


class FrameWallpaperTests(unittest.TestCase):
    def test_small_image_is_scaled_to_the_panel(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bindir = root / "bin"
            bindir.mkdir()
            log = root / "magick.log"
            image = root / "small.png"
            image.write_bytes(b"png")
            (bindir / "identify").write_text(
                "#!/bin/sh\ncase $2 in %w) echo 10;; %h) echo 20;; esac\n"
            )
            (bindir / "magick").write_text(
                "#!/bin/bash\nprintf '%s\\n' \"$*\" > \"$FT_MAGICK_LOG\"\ntouch \"${@: -1}\"\n"
            )
            for name in ("identify", "magick"):
                path = bindir / name
                path.chmod(path.stat().st_mode | stat.S_IEXEC)
            state = root / "state"
            result = _bash(
                textwrap.dedent(f"""
                set -euo pipefail
                . "{HELPER}"
                frame_scale_wallpaper "{image}"
                """),
                {
                    "PATH": f"{bindir}:{os.environ.get('PATH', '')}",
                    "FT_FRAME_SCREEN_WIDTH": "1920",
                    "FT_FRAME_SCREEN_HEIGHT": "1080",
                    "FT_MAGICK_LOG": str(log),
                    "XDG_STATE_HOME": str(state),
                    "HOME": str(root),
                },
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            scaled = state / "quickshell/user/generated/wallpaper/frame-scaled.png"
            self.assertEqual(result.stdout.strip(), str(scaled))
            self.assertIn("1920x1080^", log.read_text())
            self.assertTrue(scaled.is_file())

    def test_large_image_is_left_alone(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bindir = root / "bin"
            bindir.mkdir()
            image = root / "big.png"
            image.write_bytes(b"png")
            (bindir / "identify").write_text("#!/bin/sh\ncase $2 in %w) echo 4000;; %h) echo 3000;; esac\n")
            (bindir / "magick").write_text("#!/bin/sh\necho magick-called > \"$FT_MAGICK_LOG\"\n")
            for name in ("identify", "magick"):
                path = bindir / name
                path.chmod(path.stat().st_mode | stat.S_IEXEC)
            log = root / "magick.log"
            result = _bash(
                f'. "{HELPER}"\nframe_scale_wallpaper "{image}"\n',
                {
                    "PATH": f"{bindir}:{os.environ.get('PATH', '')}",
                    "FT_FRAME_SCREEN_WIDTH": "1920",
                    "FT_FRAME_SCREEN_HEIGHT": "1080",
                    "FT_MAGICK_LOG": str(log),
                    "HOME": str(root),
                },
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(image))
            self.assertFalse(log.exists())

    def test_missing_download_is_rejected(self):
        result = _bash(
            f'. "{HELPER}"\nframe_image_ext "" || exit 3\n',
            {"PATH": "/usr/bin:/bin", "HOME": "/tmp"},
        )
        self.assertEqual(result.returncode, 3)
        result = _bash(
            f'. "{HELPER}"\nframe_image_ext "https://example.test/a.JPG?x=1"\n',
            {"PATH": "/usr/bin:/bin"},
        )
        self.assertEqual(result.stdout.strip(), "jpg")
        with tempfile.TemporaryDirectory() as temp:
            empty = Path(temp) / "empty.jpg"
            empty.write_bytes(b"")
            result = _bash(
                f'. "{HELPER}"\nframe_require_download "{empty}"\n',
                {"PATH": "/usr/bin:/bin"},
            )
            self.assertEqual(result.returncode, 1)
            full = Path(temp) / "full.jpg"
            full.write_bytes(b"jpeg")
            result = _bash(
                f'. "{HELPER}"\nframe_require_download "{full}"\n',
                {"PATH": "/usr/bin:/bin"},
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_file_button_uses_kdialog(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bindir = root / "bin"
            bindir.mkdir()
            (bindir / "xdg-user-dir").write_text("#!/bin/sh\necho \"$FT_PICTURES\"\n")
            (bindir / "kdialog").write_text("#!/bin/sh\nprintf '%s\\n' \"$2\"\n")
            for name in ("xdg-user-dir", "kdialog"):
                path = bindir / name
                path.chmod(path.stat().st_mode | stat.S_IEXEC)
            pictures = root / "Pictures"
            result = _bash(
                f'. "{HELPER}"\nframe_pick_wallpaper\n',
                {"PATH": f"{bindir}:/usr/bin:/bin", "FT_PICTURES": str(pictures), "HOME": str(root)},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(pictures / "Wallpapers"))
            self.assertTrue((pictures / "Wallpapers").is_dir())

    def test_stage_patch_hooks_the_helper(self):
        stage = _load_stage()
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            switch = dest / "quickshell/ii/scripts/colors/switchwall.sh"
            kona = dest / "quickshell/ii/scripts/colors/random/random_konachan_wall.sh"
            osu = dest / "quickshell/ii/scripts/colors/random/random_osu_wall.sh"
            for path in (switch, kona, osu):
                path.parent.mkdir(parents=True, exist_ok=True)
            switch.write_text(
                '        check_and_prompt_upscale "$imgpath" &\n'
                '        cd "$(xdg-user-dir PICTURES)/Wallpapers/showcase" 2>/dev/null || '
                'cd "$(xdg-user-dir PICTURES)/Wallpapers" 2>/dev/null || '
                'cd "$(xdg-user-dir PICTURES)" || return 1\n'
                '        imgpath="$(kdialog --getopenfilename . --title \'Choose wallpaper\')"\n'
            )
            kona.write_text(
                "ext=$(echo \"$link\" | awk -F. '{print $NF}')\n"
                'curl -A "$userAgent" "$link" -o "$downloadPath"\n'
            )
            osu.write_text(
                "ext=$(echo \"$link\" | awk -F. '{print $NF}')\n"
                'curl "$link" -o "$downloadPath"\n'
            )
            notes = stage.apply_frame_patches(dest)
            self.assertIn("patch quickshell/ii/scripts/colors/switchwall.sh", notes)
            text = switch.read_text()
            self.assertIn("frame_scale_wallpaper", text)
            self.assertIn("frame_pick_wallpaper", text)
            self.assertIn('ext=$(frame_image_ext "$link") || exit 1', kona.read_text())
            self.assertIn("frame_require_download", osu.read_text())
            self.assertEqual(stage.apply_frame_patches(dest), [])


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Copy the laptop Hyprland and end-4 trees into an explicit stage directory.

The copy is what the experimental session reads. It does not write
~/.config/hypr or ~/.config/quickshell. Symlinks that leave the source tree
are skipped. Files that contain a private key are skipped.
"""
import argparse
import os
import shutil
import sys
from pathlib import Path

SKIP_DIRS = {".chatgpt-integration", "__pycache__", ".venv", "venv", ".git"}
SKIP_SUFFIXES = (".old", ".bak", ".pem")
SECRET_MARKERS = ("BEGIN PRIVATE KEY", '"private_key"', "BEGIN OPENSSH PRIVATE KEY")


def user_config_blocked(dest: Path) -> bool:
    home = Path.home().resolve()
    try:
        resolved = dest.resolve()
    except OSError:
        resolved = dest
    blocked = home / ".config"
    return resolved == blocked or blocked in resolved.parents


def _skip_name(name: str) -> bool:
    if name in SKIP_DIRS or name.startswith("backup-"):
        return True
    return name.endswith(SKIP_SUFFIXES)


def _has_secret(path: Path) -> bool:
    try:
        if path.stat().st_size > 1_000_000:
            return False
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return any(marker in text for marker in SECRET_MARKERS)


def copy_tree(src: Path, dest: Path) -> list[str]:
    """Copy src into dest. Returns notes for skipped paths."""
    src = src.resolve()
    notes = []
    if not src.is_dir():
        raise SystemExit(f"frametop: stage source is not a directory: {src}")
    for dirpath, dirnames, filenames in os.walk(src, followlinks=False):
        kept = []
        for name in dirnames:
            child = Path(dirpath) / name
            if _skip_name(name):
                notes.append(f"skip {child}")
                continue
            if child.is_symlink():
                target = child.resolve()
                if not target.is_relative_to(src):
                    notes.append(f"skip symlink {child}")
                    continue
            kept.append(name)
        dirnames[:] = kept
        rel = Path(dirpath).relative_to(src)
        (dest / rel).mkdir(parents=True, exist_ok=True)
        for name in filenames:
            child = Path(dirpath) / name
            if _skip_name(name):
                notes.append(f"skip {child}")
                continue
            target = dest / rel / name
            if child.is_symlink():
                link = os.readlink(child)
                resolved = (child.parent / link).resolve()
                if not resolved.is_relative_to(src):
                    notes.append(f"skip symlink {child}")
                    continue
                if target.is_symlink() or target.exists():
                    target.unlink()
                target.symlink_to(link)
                continue
            if _has_secret(child):
                notes.append(f"skip secret {child}")
                continue
            shutil.copy2(child, target, follow_symlinks=False)
    return notes


FONT_FAMILIES = (
    "Google Sans Flex",
    "Readex Pro",
    "Space Grotesk",
    "Material Symbols Rounded",
    "JetBrainsMono Nerd Font",
)

SHELL_PATCHES = (
    (
        "quickshell/ii/modules/ii/notificationPopup/NotificationPopup.qml",
        "Config.options.notifications.forceMonitor",
        "Config.options.notifications.monitor",
    ),
    (
        "quickshell/ii/modules/ii/bar/BarContent.qml",
        "padding: workspacesWidget.widgetPadding",
        "padding: 5",
    ),
    (
        "quickshell/ii/modules/common/widgets/ToolbarTabBar.qml",
        "property Item targetItem: contentItem.children[root.currentIndex]\n",
        "property Item targetItem: contentItem.children[root.currentIndex] ?? null\n",
    ),
    (
        "quickshell/ii/modules/common/widgets/ToolbarTabBar.qml",
        "index: activeIndicator.targetItem.x\n",
        "index: activeIndicator.targetItem?.x ?? 0\n",
    ),
    (
        "quickshell/ii/modules/common/widgets/ToolbarTabBar.qml",
        "index: activeIndicator.targetItem.x + activeIndicator.targetItem.width",
        "index: (activeIndicator.targetItem?.x ?? 0) + (activeIndicator.targetItem?.width ?? 0)",
    ),
    (
        "quickshell/ii/services/ConflictKiller.qml",
        "            if (Config.ready) checkConflictsProc.running = true",
        "            if (Quickshell.env(\"FT_FRAME_SESSION\")) return\n"
        "            if (Config.ready) checkConflictsProc.running = true",
    ),
)


def apply_frame_patches(dest: Path) -> list[str]:
    """Correct staged shell bugs without editing the laptop copy."""
    notes = []
    for rel, old, new in SHELL_PATCHES:
        path = dest / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if old not in text or new in text:
            continue
        path.write_text(text.replace(old, new), encoding="utf-8")
        notes.append(f"patch {rel}")
    return notes


def copy_impulse(src: Path, dest: Path) -> list[str]:
    """Shell settings live beside the Quickshell tree, not inside it."""
    notes = []
    dest.mkdir(parents=True, exist_ok=True)
    config = src / "config.json"
    if config.is_file() and not _has_secret(config):
        shutil.copy2(config, dest / "config.json")
    elif config.is_file():
        notes.append(f"skip secret {config}")
    for name in ("actions", "translations"):
        child = src / name
        if child.is_dir():
            notes.extend(copy_tree(child, dest / name))
    return notes


def copy_theme_state(src: Path, dest: Path) -> list[str]:
    """Wallpaper-derived colors and the shell's state files. Not the AI venv."""
    wanted = (
        "states.json",
        "user/first_run.txt",
        "user/generated/colors.json",
        "user/generated/wallpaper/category.txt",
        "user/generated/wallpaper/path.txt",
    )
    notes = []
    for rel in wanted:
        child = src / rel
        if not child.is_file():
            notes.append(f"missing theme {rel}")
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(child, target)
    return notes


def font_files_for_families(families: tuple[str, ...] | list[str]) -> list[Path]:
    import subprocess

    found: list[Path] = []
    seen: set[str] = set()
    for family in families:
        try:
            out = subprocess.check_output(["fc-list", family, "file"], text=True)
        except (OSError, subprocess.CalledProcessError):
            continue
        for line in out.splitlines():
            raw = line.split(":", 1)[0].strip()
            if not raw:
                continue
            path = Path(raw)
            if path.name in seen or not path.is_file():
                continue
            seen.add(path.name)
            found.append(path)
    return found


def copy_font_files(files: list[Path], dest: Path) -> list[str]:
    dest.mkdir(parents=True, exist_ok=True)
    notes = []
    for path in files:
        if path.is_file():
            shutil.copy2(path, dest / path.name)
            notes.append(f"font {path.name}")
    return notes


def stage(hypr: Path, quickshell: Path, dest: Path, replace: bool,
          impulse: Path | None = None, theme_state: Path | None = None,
          wallpaper: Path | None = None, font_files: list[Path] | None = None) -> list[str]:
    if user_config_blocked(dest):
        raise SystemExit(f"frametop: refusing to write a Frame or user config directory: {dest}")
    if dest.exists() and any(dest.iterdir()) and not replace:
        raise SystemExit(f"frametop: stage destination already has files: {dest}")
    if replace and dest.exists() and "/stage/" not in f"{dest}/":
        raise SystemExit(f"frametop: --replace is only for a stage/ directory: {dest}")
    dest.mkdir(parents=True, exist_ok=True)
    notes = []
    notes.extend(copy_tree(hypr, dest / "hypr"))
    notes.extend(copy_tree(quickshell, dest / "quickshell" / "ii"))
    notes.extend(apply_frame_patches(dest))
    if impulse is not None:
        notes.extend(copy_impulse(impulse, dest / "illogical-impulse"))
    theme = dest.parent / "theme"
    if theme_state is not None:
        notes.extend(copy_theme_state(theme_state, theme / "quickshell"))
    if wallpaper is not None and wallpaper.is_file():
        theme.mkdir(parents=True, exist_ok=True)
        shutil.copy2(wallpaper, theme / "wallpaper.png")
    if font_files:
        notes.extend(copy_font_files(font_files, theme / "fonts"))
    return notes


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Stage Hyprland and end-4 configs")
    parser.add_argument("--hypr", type=Path, required=True)
    parser.add_argument("--quickshell", type=Path, required=True)
    parser.add_argument("--dest", type=Path, required=True)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--impulse", type=Path)
    parser.add_argument("--theme-state", type=Path)
    parser.add_argument("--wallpaper", type=Path)
    parser.add_argument("--fonts", action="store_true")
    args = parser.parse_args(argv)
    fonts = font_files_for_families(FONT_FAMILIES) if args.fonts else None
    notes = stage(
        args.hypr, args.quickshell, args.dest, args.replace,
        impulse=args.impulse, theme_state=args.theme_state,
        wallpaper=args.wallpaper, font_files=fonts,
    )
    for note in notes:
        print(note, file=sys.stderr)
    print(f"staged {args.dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

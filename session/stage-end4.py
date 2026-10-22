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


def stage(hypr: Path, quickshell: Path, dest: Path, replace: bool) -> list[str]:
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
    return notes


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Stage Hyprland and end-4 configs")
    parser.add_argument("--hypr", type=Path, required=True)
    parser.add_argument("--quickshell", type=Path, required=True)
    parser.add_argument("--dest", type=Path, required=True)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args(argv)
    notes = stage(args.hypr, args.quickshell, args.dest, args.replace)
    for note in notes:
        print(note, file=sys.stderr)
    print(f"staged {args.dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

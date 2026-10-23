#!/usr/bin/env python3
"""Write the experimental session's KDE and GTK theme from end-4 colors.

Dolphin and other Qt apps launched by Hyprland read this session's
XDG_CONFIG_HOME and XDG_DATA_HOME. The host's ~/.config is not a destination.
"""
import hashlib
import json
import sys
from pathlib import Path


def _allowed(path: Path) -> bool:
    """Session directories and test temps. Not the host config or data root."""
    home = Path.home().resolve()
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    for blocked in (home / ".config", home / ".local" / "share"):
        if resolved == blocked:
            return False
        if blocked in resolved.parents and "frametop" not in resolved.parts:
            return False
    return True


def _rgb(data: dict, key: str, fallback: str) -> str:
    raw = str(data.get(key) or fallback).lstrip("#")
    if len(raw) != 6 or any(c not in "0123456789abcdefABCDEF" for c in raw):
        raw = fallback.lstrip("#")
    return f"{int(raw[0:2], 16)},{int(raw[2:4], 16)},{int(raw[4:6], 16)}"


def _group(data: dict, background: str, foreground: str, accent: str) -> str:
    bg = _rgb(data, background, "#13121a")
    fg = _rgb(data, foreground, "#e5e1ec")
    accent_rgb = _rgb(data, accent, "#90d6a0")
    return "\n".join((
        f"BackgroundNormal={bg}",
        f"BackgroundAlternate={bg}",
        f"ForegroundNormal={fg}",
        f"ForegroundInactive={fg}",
        f"ForegroundActive={fg}",
        f"ForegroundLink={accent_rgb}",
        f"DecorationFocus={accent_rgb}",
        f"DecorationHover={accent_rgb}",
    ))


def _preview_groups() -> str:
    """KFileDialog's icon view. View Style 8 is KFile::PreviewContents."""
    plugins = (
        "imagethumbnail",
        "jpegthumbnail",
        "pngthumbnail",
        "webpthumbnail",
        "svgthumbnail",
        "windowsimagethumbnail",
        "directorythumbnail",
    )
    lines = [
        "[KFileDialog Settings]",
        "Show Preview=true",
        "Show Preview Panel=true",
        "View Style=8",
        "",
        "[PreviewSettings]",
        "MaximumSize=10485760",
    ]
    lines.extend(f"{name}=true" for name in plugins)
    return "\n".join(lines)


def ensure_previews(config_home: Path) -> None:
    """Add thumbnail settings without replacing a scheme already written."""
    if not _allowed(config_home):
        raise SystemExit(f"frametop: refusing to write a host theme directory: {config_home}")
    config_home.mkdir(parents=True, exist_ok=True)
    path = config_home / "kdeglobals"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if "Show Preview=true" in text and "View Style=8" in text and "[PreviewSettings]" in text:
        return
    if text and not text.endswith("\n"):
        text += "\n"
    path.write_text(text + _preview_groups() + "\n", encoding="utf-8")


def write_theme(colors_path: Path, config_home: Path, data_home: Path) -> None:
    if not _allowed(config_home) or not _allowed(data_home):
        raise SystemExit(f"frametop: refusing to write a host theme directory: {config_home}")
    try:
        data = json.loads(colors_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    scheme = data_home / "color-schemes" / "FrametopEnd4.colors"
    scheme.parent.mkdir(parents=True, exist_ok=True)
    window = _group(data, "surface", "on_surface", "primary")
    button = _group(data, "surface_container", "on_surface", "primary")
    view = _group(data, "surface_container_high", "on_surface", "primary")
    selection = _group(data, "primary_container", "on_primary_container", "primary")
    scheme.write_text(
        "\n".join((
            "[General]",
            "Name=Frametop End-4",
            "ColorScheme=FrametopEnd4",
            "",
            "[Colors:Window]",
            window,
            "",
            "[Colors:Button]",
            button,
            "",
            "[Colors:View]",
            view,
            "",
            "[Colors:Selection]",
            selection,
            "",
        )) + "\n",
        encoding="utf-8",
    )
    # KColorScheme compares this to the scheme file and reloads a running app.
    scheme_hash = hashlib.sha1(scheme.read_bytes()).hexdigest()
    config_home.mkdir(parents=True, exist_ok=True)
    (config_home / "kdeglobals").write_text(
        "\n".join((
            "[General]",
            "ColorScheme=FrametopEnd4",
            f"ColorSchemeHash={scheme_hash}",
            "",
            "[Icons]",
            "Theme=breeze",
            "",
            "[KDE]",
            "widgetStyle=Breeze",
            "",
            _preview_groups(),
            "",
        )),
        encoding="utf-8",
    )
    for name in ("gtk-3.0", "gtk-4.0"):
        gtk = config_home / name
        gtk.mkdir(parents=True, exist_ok=True)
        (gtk / "settings.ini").write_text(
            "\n".join((
                "[Settings]",
                "gtk-icon-theme-name=breeze",
                "gtk-application-prefer-dark-theme=1",
                "",
            )),
            encoding="utf-8",
        )


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "--previews":
        ensure_previews(Path(argv[1]))
        return 0
    if len(argv) != 3:
        print("usage: frame-kde-theme.py COLORS.json CONFIG_HOME DATA_HOME", file=sys.stderr)
        print("       frame-kde-theme.py --previews CONFIG_HOME", file=sys.stderr)
        return 2
    write_theme(Path(argv[0]), Path(argv[1]), Path(argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

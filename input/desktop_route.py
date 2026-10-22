"""The experimental Hyprland session's route file.

The session writes $XDG_RUNTIME_DIR/frametop-hyprland.route and removes it on
the way out. Readers use that file only. A dead pid, a second Hyprland
signature, or Plasma's ft-screens means there is no experimental desktop to
steer.
"""
import os
import shlex
import sys
import time
from pathlib import Path

ROUTE_NAME = "frametop-hyprland.route"
_PLASMA_AT = 0.0
_PLASMA = False


def route_path():
    override = os.environ.get("FT_HYPR_ROUTE")
    if override:
        return override
    runtime = os.environ.get("XDG_RUNTIME_DIR", "")
    if not runtime:
        return ""
    return os.path.join(runtime, ROUTE_NAME)


def _abs_path(value):
    if not value or "\n" in value or "\x00" in value or not value.startswith("/"):
        return None
    return value


def load(path=None):
    """Parse a route file. Invalid contents are no route."""
    path = route_path() if path is None else path
    if not path:
        return None
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return None
    fields = {}
    for line in text.splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        fields[key.strip()] = value.strip()
    pid = fields.get("pid", "")
    control = fields.get("control", "")
    runtime = _abs_path(fields.get("runtime", ""))
    wayland = _abs_path(fields.get("wayland", ""))
    config_home = _abs_path(fields.get("config_home", ""))
    if not pid.isdigit() or not control or not control.replace("-", "").replace("_", "").isalnum():
        return None
    if not runtime or not wayland or not config_home or not os.path.isdir(runtime):
        return None
    return {
        "pid": int(pid),
        "control": control,
        "runtime": runtime,
        "wayland": wayland,
        "config_home": config_home,
    }


def pid_alive(pid):
    try:
        os.kill(int(pid), 0)
    except OSError:
        return False
    return True


def signature(runtime):
    """The one Hyprland instance directory under this runtime. Never a glob."""
    hypr = os.path.join(runtime, "hypr")
    if not os.path.isdir(hypr):
        return None, "experimental session has no Hyprland instance yet"
    names = sorted(
        name for name in os.listdir(hypr)
        if os.path.isdir(os.path.join(hypr, name)) and not name.startswith(".")
    )
    if len(names) != 1:
        if len(names) > 1:
            return None, "experimental session has more than one Hyprland instance"
        return None, "experimental session has no Hyprland instance yet"
    return names[0], None


def plasma_running():
    """True when Plasma's compositor holds the regular desktop socket."""
    global _PLASMA_AT, _PLASMA
    now = time.monotonic()
    if now - _PLASMA_AT < 0.5:
        return _PLASMA
    found = False
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        try:
            raw = open(f"/proc/{name}/cmdline", "rb").read()
        except OSError:
            continue
        cmd = raw.replace(b"\0", b" ").decode("utf-8", "replace")
        if "ft-screens" in cmd and "--socket ft-screens-0" in cmd:
            found = True
            break
    _PLASMA_AT = now
    _PLASMA = found
    return found


def live_route(path=None):
    """The experimental session, whether or not Plasma's compositor is also up."""
    info = load(path)
    if info is None or not pid_alive(info["pid"]):
        return None
    return info


def desktop_target(path=None, plasma=None):
    """Where experimental desktop input goes, or None to leave @ft_screens alone."""
    info = load(path)
    if info is None or not pid_alive(info["pid"]):
        return None
    if plasma is None:
        plasma = plasma_running()
    if plasma:
        return None
    return info


def mtime(path=None):
    path = route_path() if path is None else path
    try:
        return os.stat(path).st_mtime_ns
    except OSError:
        return None


def chords_should_bind(*, route_ok, desktop_focused, paused, game, capturing, controller_in_games):
    """Face buttons are taken only while this session is the desktop being typed on.

    controller_in_games prefixes the helper's whole bind list, which would also
    take these buttons during gameplay. They stay out of that list.
    """
    if capturing or not route_ok or not desktop_focused or paused or game or controller_in_games:
        return False
    return True


def _fail(message):
    print(message, file=sys.stderr)
    raise SystemExit(2)


def export_lines(path):
    info = load(path)
    if info is None:
        _fail("frametop: experimental Hyprland route is missing or invalid")
    if not pid_alive(info["pid"]):
        _fail("frametop: experimental Hyprland route session is not running")
    sig, err = signature(info["runtime"])
    if err:
        _fail(f"frametop: {err}")
    pairs = {
        "FT_ROUTE_RUNTIME": info["runtime"],
        "FT_ROUTE_SIGNATURE": sig,
        "FT_ROUTE_CONFIG_HOME": info["config_home"],
        "FT_ROUTE_CONTROL": info["control"],
        "FT_ROUTE_WAYLAND": info["wayland"],
    }
    return "\n".join(f"{key}={shlex.quote(value)}" for key, value in pairs.items())


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "--export":
        raise SystemExit("usage: desktop_route.py --export ROUTE")
    print(export_lines(sys.argv[2]))

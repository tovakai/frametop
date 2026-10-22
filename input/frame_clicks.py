"""Right-controller clicks from vrserver's input stream.

The pointer helper reads the same buttons through SteamVR action sets, and
those sets stay inactive until SteamVR delivers overlay-global input. This
stream reports the clicks either way. The chord machine ignores a repeated
press, so both sources can feed it.
"""

import os
import threading
import time


def clicks(text, sides):
    """`(button, 1|0)` for click components in one websocket message.

    `sides` maps a controller's root path to "left" or "right". Other
    components (touch, position) are ignored.
    """
    if not text or "/click" not in text:
        return []
    import json
    try:
        msg = json.loads(text)
    except ValueError:
        return []
    side = sides.get(msg.get("device"))
    if side not in ("left", "right"):
        return []
    found = []
    for component, value in (msg.get("components") or {}).items():
        parts = str(component).split("/")
        if len(parts) != 4 or parts[1] != "input" or parts[3] != "click":
            continue
        found.append((f"{side}/{parts[2]}", 1 if value else 0))
    return found


class ClickWatch(threading.Thread):
    """Follow controller clicks while `enabled()` is true and pass them to `on_click`."""

    def __init__(self, on_click, enabled, log):
        super().__init__(name="frame-clicks", daemon=True)
        self.on_click = on_click
        self.enabled = enabled
        self.log = log

    def run(self):
        import vrws
        while True:
            if not self.enabled():
                time.sleep(0.25)
                continue
            try:
                self._session(vrws)
            except (OSError, ValueError) as exc:
                self.log(f"controller clicks: SteamVR's web socket went away ({exc}); retrying")
                time.sleep(2)

    def _session(self, vrws):
        ws = vrws.VrSocket()
        try:
            ws.open(f"frametop_chords_{os.getpid()}")
            sides = {}
            while self.enabled():
                found = vrws.controllers()
                if found != sides:
                    for path in sides.keys() - found.keys():
                        ws.subscribe(path, on=False)
                    for path in found.keys() - sides.keys():
                        ws.subscribe(path)
                    sides = found
                    self.log(f"controller clicks: following {' and '.join(sorted(sides.values())) or 'no'} "
                             f"controller{'s' if len(sides) != 1 else ''}")
                for text in ws.messages(timeout=0.5):
                    for button, value in clicks(text, sides):
                        self.on_click(button, value)
        finally:
            ws.close()

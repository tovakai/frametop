#!/usr/bin/env python3
"""Offline checks for the right-controller trigger chords.

Nothing here talks to SteamVR, the input relay, or the headset.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import controller_chords

SPEC = {
    "modifier": "right/trigger",
    "swallow_click": "right/bumper",
    "normal": {
        "right/x": "workspace-prev",
        "right/b": "workspace-next",
        "right/a": "window-next",
        "right/y": "window-prev",
    },
    "modified": {
        "right/x": "terminal",
        "right/b": "browser",
        "right/a": "files",
        "right/y": "launcher",
        "right/bumper": "close",
    },
}


def fresh():
    return controller_chords.ControllerChords(SPEC)


def check(name, cond):
    if not cond:
        raise SystemExit(f"FAIL {name}")
    print(f"ok {name}")


def main():
    idle = controller_chords.ControllerChords(None)
    check("absent spec owns nothing", not idle.owns("right/a") and idle.bind_names() == [])
    check("absent spec ignores events", idle.event("right/trigger", 1) == [])

    c = fresh()
    check("trigger press is not an action", c.event("right/trigger", 1) == [] and c.armed)
    check("trigger release is not an action", c.event("right/trigger", 0) == [] and not c.armed)

    c = fresh()
    check("X alone is previous workspace", c.event("right/x", 1) == ["workspace-prev"])
    check("holding X does not repeat", c.event("right/x", 1) == [])
    check("repeat code is ignored", c.event("right/x", 2) == [])
    check("X release is silent", c.event("right/x", 0) == [])
    check("B alone is next workspace", c.event("right/b", 1) == ["workspace-next"])
    c.event("right/b", 0)
    check("A alone sends the window forward", c.event("right/a", 1) == ["window-next"])
    c.event("right/a", 0)
    check("Y alone sends the window back", c.event("right/y", 1) == ["window-prev"])

    c = fresh()
    c.event("right/trigger", 1)
    check("trigger then X opens a terminal", c.event("right/x", 1) == ["terminal"])
    check("X release after a chord is silent", c.event("right/x", 0) == [])
    check("trigger release after the chord is silent", c.event("right/trigger", 0) == [])

    c = fresh()
    c.event("right/trigger", 1)
    c.event("right/a", 1)
    check("releasing the trigger first does not fire the normal action",
          c.event("right/trigger", 0) == [])
    check("releasing A afterwards stays silent", c.event("right/a", 0) == [])

    c = fresh()
    check("A before the trigger is the normal action", c.event("right/a", 1) == ["window-next"])
    check("trigger afterwards adds nothing", c.event("right/trigger", 1) == [])
    check("releasing A while the trigger is held adds nothing", c.event("right/a", 0) == [])

    c = fresh()
    c.event("right/trigger", 1)
    check("trigger then B opens the browser", c.event("right/b", 1) == ["browser"])
    c = fresh()
    c.event("right/trigger", 1)
    check("trigger then Y opens the launcher", c.event("right/y", 1) == ["launcher"])
    c = fresh()
    c.event("right/trigger", 1)
    check("trigger then A opens files", c.event("right/a", 1) == ["files"])

    c = fresh()
    check("R1 is not taken from SteamVR", "right/bumper" not in c.bind_names())
    check("trigger and the face buttons are bound",
          c.bind_names() == ["right/trigger", "right/x", "right/b", "right/a", "right/y"])
    c.event("right/trigger", 1)
    check("a bumper event does not itself close", c.event("right/bumper", 1) == [])
    check("swallowed click closes once", c.click_down() == ["close"])
    check("a repeated click report does not close again", c.click_down() == [])
    c.click_up()
    check("another R1 while the trigger stays down closes once more", c.click_down() == ["close"])
    c.click_up()
    c.event("right/trigger", 0)
    check("R1 without the trigger is not a close", c.click_down() == [])

    c = fresh()
    c.event("right/trigger", 1)
    c.click_down()
    c.clear()
    check("clear drops the modifier and the latch", not c.armed and c.click_down() == [])
    check("a later X is the normal workspace action", c.event("right/x", 1) == ["workspace-prev"])

    print("controller chords: ok")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Offline checks for controller clicks read from vrserver's stream."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import frame_clicks

SIDES = {"/user/hand/right": "right", "/user/hand/left": "left"}


def check(label, got, want):
    if got != want:
        raise SystemExit(f"FAIL {label}: got {got!r}, want {want!r}")
    print(f"ok    {label}")


def main():
    text = ('{"type":"update_component_states","device":"/user/hand/right",'
            '"components":{"/input/a/click":true,"/input/trigger/value":0.4}}')
    check("a click is a button press, an analog value is not",
          frame_clicks.clicks(text, SIDES), [("right/a", 1)])
    text = ('{"device":"/user/hand/right","components":{"/input/trigger/click":false,'
            '"/input/b/click":true}}')
    check("release and a second click",
          frame_clicks.clicks(text, SIDES), [("right/trigger", 0), ("right/b", 1)])
    check("unknown device", frame_clicks.clicks(text, {}), [])
    check("not json", frame_clicks.clicks("nope /click", SIDES), [])
    check("no click", frame_clicks.clicks('{"device":"/user/hand/right"}', SIDES), [])
    print("frame clicks: ok")


if __name__ == "__main__":
    main()

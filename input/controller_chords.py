"""Right-controller chords for the experimental Hyprland desktop.

The trigger is a modifier and never an action by itself. A button press
invokes one action: the modified action when the trigger is already held,
otherwise the normal action. Releases do not invoke anything, whichever
button comes up first. A repeat while the same button stays down is ignored.

R3 (right/thumbstick) stays SteamVR's right click, so it is not requested
from the helper. A thumbstick press while the trigger is already down closes
once. ft-screens also swallows that right click and may report it with
chord-fired; the latch makes the button event and the click one close.
R3 without the trigger is only the right click.
"""


class ControllerChords:
    def __init__(self, spec):
        spec = spec if isinstance(spec, dict) else {}
        self.enabled = bool(spec)
        self.modifier = spec.get("modifier") or ("right/trigger" if spec else "")
        self.swallow = spec.get("swallow_click") or ""
        normal = spec.get("normal") if isinstance(spec.get("normal"), dict) else {}
        modified = spec.get("modified") if isinstance(spec.get("modified"), dict) else {}
        self.normal = dict(normal)
        self.modified = dict(modified)
        self.clear()

    def clear(self):
        """Drop held modifier state. Used for pause, a VR game, and focus loss."""
        self.modifier_down = False
        self.down = set()
        self.click_latched = False

    def busy(self):
        """A modifier, face button, or swallowed click is still down."""
        return self.modifier_down or bool(self.down) or self.click_latched

    @property
    def armed(self):
        """The next controller left-click should be swallowed."""
        return bool(self.enabled and self.modifier_down and self.swallow in self.modified)

    def owns(self, button):
        if not self.enabled:
            return False
        return button == self.modifier or button in self.normal or button in self.modified

    def bind_names(self):
        """Buttons the helper should take. The swallowed click stays with SteamVR."""
        if not self.enabled:
            return []
        names = [self.modifier]
        for mapping in (self.normal, self.modified):
            for button in mapping:
                if button != self.swallow and button not in names:
                    names.append(button)
        return names

    def event(self, button, value):
        """Press or release. Returns the actions to run now (at most one)."""
        if not self.owns(button) or value not in (0, 1):
            return []
        if button == self.swallow:
            # The overlay click can arrive as well. Whichever report is first
            # closes; the latch drops the second one.
            if value == 0:
                self.down.discard(button)
                return []
            if button in self.down or self.click_latched:
                return []
            self.down.add(button)
            if not self.modifier_down:
                return []
            self.click_latched = True
            action = self.modified.get(button)
            if not action or action in ("none", "key"):
                return []
            return [action]
        if button == self.modifier:
            self.modifier_down = value == 1
            if not self.modifier_down:
                self.click_latched = False
            return []
        if value == 0:
            self.down.discard(button)
            return []
        if button in self.down:
            return []
        self.down.add(button)
        action = self.modified.get(button) if self.modifier_down else self.normal.get(button)
        if not action or action in ("none", "key"):
            return []
        return [action]

    def click_down(self):
        """One swallowed left click. Empty when the trigger is up or it already fired."""
        if not self.armed or self.click_latched:
            return []
        self.click_latched = True
        action = self.modified.get(self.swallow)
        if not action or action in ("none", "key"):
            return []
        return [action]

    def click_up(self):
        self.click_latched = False

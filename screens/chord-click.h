#ifndef FT_CHORD_CLICK_H
#define FT_CHORD_CLICK_H
#include <stdbool.h>
// Trigger+R1 arrives as the controller's left click. Arming swallows that
// press. Disarming must not forget a press that is still down: releasing the
// trigger first, then R1, still drops the release so it cannot become a click.
struct ft_chord_guard {
    bool armed;
    bool held;
};
enum { FT_CHORD_DELIVER = 0, FT_CHORD_SWALLOW = 1 };
static inline void ft_chord_guard_set_armed(struct ft_chord_guard *guard, bool armed) {
    guard->armed = armed;
}
// R1 is SteamVR's overlay left click. That click is attributed either to the
// hand controller or to the pointer helper's virtual controller (ft_pointer).
// A mouse is neither, so an armed chord does not swallow it.
static inline bool ft_chord_is_controller_click(bool hand, bool virtual_pointer, bool left) {
    return left && (hand || virtual_pointer);
}
// *notify is set on the swallowed press edge and on its matching release.
static inline int ft_chord_guard_button(struct ft_chord_guard *guard, bool pressed, bool *notify) {
    *notify = false;
    if (pressed) {
        if (guard->held) return FT_CHORD_SWALLOW;
        if (!guard->armed) return FT_CHORD_DELIVER;
        guard->held = true;
        *notify = true;
        return FT_CHORD_SWALLOW;
    }
    if (!guard->held) return FT_CHORD_DELIVER;
    guard->held = false;
    *notify = true;
    return FT_CHORD_SWALLOW;
}
#endif

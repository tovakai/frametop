#undef NDEBUG
#include <assert.h>
#include "../chord-click.h"
int main(void) {
    struct ft_chord_guard guard = {0};
    bool notify = false;
    assert(ft_chord_guard_button(&guard, true, &notify) == FT_CHORD_DELIVER && !notify);
    assert(ft_chord_guard_button(&guard, false, &notify) == FT_CHORD_DELIVER && !notify);
    ft_chord_guard_set_armed(&guard, true);
    assert(ft_chord_guard_button(&guard, true, &notify) == FT_CHORD_SWALLOW && notify && guard.held);
    assert(ft_chord_guard_button(&guard, true, &notify) == FT_CHORD_SWALLOW && !notify);
    ft_chord_guard_set_armed(&guard, false);
    assert(guard.held);
    assert(ft_chord_guard_button(&guard, false, &notify) == FT_CHORD_SWALLOW && notify && !guard.held);
    assert(ft_chord_guard_button(&guard, false, &notify) == FT_CHORD_DELIVER && !notify);
    ft_chord_guard_set_armed(&guard, true);
    assert(ft_chord_guard_button(&guard, true, &notify) == FT_CHORD_SWALLOW && notify);
    assert(ft_chord_guard_button(&guard, false, &notify) == FT_CHORD_SWALLOW && notify && !guard.held);
    ft_chord_guard_set_armed(&guard, false);
    assert(ft_chord_guard_button(&guard, true, &notify) == FT_CHORD_DELIVER && !guard.held);
    return 0;
}

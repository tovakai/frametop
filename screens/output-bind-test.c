#include "output-bind.h"

#include <stdio.h>
#include <string.h>

static int fails;

static void expect(int cond, const char *what) {
    if (cond) return;
    fprintf(stderr, "fail: %s\n", what);
    ++fails;
}

int main(void) {
    char name[FT_OUTPUT_NAME_MAX];
    struct ft_output_table table;
    ft_output_table_init(&table);

    expect(ft_output_monitor_name("aquamarine - WAYLAND-1", name, sizeof name), "parse 1");
    expect(strcmp(name, "WAYLAND-1") == 0, "name 1");
    expect(ft_output_monitor_name("aquamarine - WAYLAND-12 extra", name, sizeof name), "parse 12");
    expect(strcmp(name, "WAYLAND-12") == 0, "name 12");
    expect(!ft_output_monitor_name("KDE Wayland Compositor DP-1", name, sizeof name), "kwin title");
    expect(!ft_output_monitor_name("aquamarine - HDMI-A-1", name, sizeof name), "other backend");
    expect(!ft_output_monitor_name(NULL, name, sizeof name), "null title");

    // Arrival order is not the slot. WAYLAND-2 is claimed onto screen 1
    // before WAYLAND-1 exists, then WAYLAND-1 takes screen 2.
    expect(ft_output_claim(&table, "WAYLAND-2", 1), "claim 2->1");
    expect(ft_output_claim(&table, "WAYLAND-1", 2), "claim 1->2");
    expect(ft_output_screen(&table, "WAYLAND-2") == 1, "screen of 2");
    expect(ft_output_screen(&table, "WAYLAND-1") == 2, "screen of 1");
    expect(strcmp(ft_output_monitor(&table, 1), "WAYLAND-2") == 0, "monitor on 1");

    // Recreate: the old name dies, the new name takes the same slot,
    // and the other slot is left alone.
    ft_output_release_monitor(&table, "WAYLAND-2");
    expect(ft_output_screen(&table, "WAYLAND-2") == 0, "released");
    expect(ft_output_screen(&table, "WAYLAND-1") == 2, "other slot stays");
    expect(ft_output_claim(&table, "WAYLAND-4", 1), "recreate onto slot 1");
    expect(ft_output_screen(&table, "WAYLAND-4") == 1, "new name, same slot");
    expect(ft_output_screen(&table, "WAYLAND-1") == 2, "slot 2 still WAYLAND-1");

    // A claim replaces a previous occupant of that slot.
    expect(ft_output_claim(&table, "WAYLAND-9", 2), "replace slot 2");
    expect(ft_output_screen(&table, "WAYLAND-1") == 0, "old occupant released");
    expect(ft_output_screen(&table, "WAYLAND-9") == 2, "new occupant");
    expect(!ft_output_claim(&table, "WAYLAND-9", 0), "slot 0 rejected");
    expect(!ft_output_claim(&table, "bad name", 3), "space rejected");

    // Three screens, claimed out of order, keep distinct slots.
    ft_output_table_init(&table);
    expect(ft_output_claim(&table, "WAYLAND-3", 3), "three c");
    expect(ft_output_claim(&table, "WAYLAND-1", 1), "three a");
    expect(ft_output_claim(&table, "WAYLAND-2", 2), "three b");
    expect(ft_output_screen(&table, "WAYLAND-1") == 1, "three slot 1");
    expect(ft_output_screen(&table, "WAYLAND-2") == 2, "three slot 2");
    expect(ft_output_screen(&table, "WAYLAND-3") == 3, "three slot 3");
    ft_output_release_screen(&table, 2);
    expect(ft_output_screen(&table, "WAYLAND-2") == 0, "drop middle");
    expect(ft_output_screen(&table, "WAYLAND-1") == 1 && ft_output_screen(&table, "WAYLAND-3") == 3,
           "ends stay");

    if (fails) {
        fprintf(stderr, "%d failure(s)\n", fails);
        return 1;
    }
    printf("output-bind: ok\n");
    return 0;
}

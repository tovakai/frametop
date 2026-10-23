#ifndef FT_OUTPUT_BIND_H
#define FT_OUTPUT_BIND_H
// Hyprland monitor name <-> Frametop screen slot.
// Aquamarine titles its Wayland toplevel "aquamarine - WAYLAND-N". N is a
// creation counter, so the slot comes from an explicit claim, not from N
// and not from which toplevel appeared first.
#include <stdbool.h>

#define FT_OUTPUT_NAME_MAX 64
#define FT_OUTPUT_BINDS 24

struct ft_output_bind {
    char monitor[FT_OUTPUT_NAME_MAX];
    int screen;  // 1-based Frametop slot
};

struct ft_output_table {
    struct ft_output_bind binds[FT_OUTPUT_BINDS];
    int n;
};

void ft_output_table_init(struct ft_output_table *table);

// "aquamarine - WAYLAND-12" (optional trailing text) -> "WAYLAND-12".
// KWin titles ("KDE Wayland Compositor ...") do not match.
bool ft_output_monitor_name(const char *title, char *out, int out_len);

// One monitor, one slot. A later claim for either replaces the old one.
// Returns false when the name or slot is unusable.
bool ft_output_claim(struct ft_output_table *table, const char *monitor, int screen);
void ft_output_release_monitor(struct ft_output_table *table, const char *monitor);
void ft_output_release_screen(struct ft_output_table *table, int screen);

// 0 when this monitor has no claim.
int ft_output_screen(const struct ft_output_table *table, const char *monitor);
const char *ft_output_monitor(const struct ft_output_table *table, int screen);

#endif

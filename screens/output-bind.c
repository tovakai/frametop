#include "output-bind.h"

#include <ctype.h>
#include <string.h>

void ft_output_table_init(struct ft_output_table *table) {
    if (!table) return;
    memset(table, 0, sizeof *table);
}

bool ft_output_monitor_name(const char *title, char *out, int out_len) {
    static const char prefix[] = "aquamarine - ";
    const size_t prefix_len = sizeof prefix - 1;
    const char *name, *end;
    int len;
    if (!title || !out || out_len < 2) return false;
    if (strncmp(title, prefix, prefix_len) != 0) return false;
    name = title + prefix_len;
    if (strncmp(name, "WAYLAND-", 8) != 0) return false;
    end = name + 8;
    if (!isdigit((unsigned char)*end)) return false;
    while (isdigit((unsigned char)*end)) ++end;
    if (*end != '\0' && *end != ' ') return false;
    len = (int)(end - name);
    if (len <= 0 || len >= out_len) return false;
    memcpy(out, name, (size_t)len);
    out[len] = '\0';
    return true;
}

static bool name_ok(const char *monitor) {
    size_t n;
    if (!monitor || !monitor[0]) return false;
    n = strlen(monitor);
    if (n >= FT_OUTPUT_NAME_MAX) return false;
    for (size_t i = 0; i < n; ++i)
        if (monitor[i] == ' ' || monitor[i] == '\n') return false;
    return true;
}

static void drop_at(struct ft_output_table *table, int index) {
    if (index < 0 || index >= table->n) return;
    memmove(&table->binds[index], &table->binds[index + 1],
            (size_t)(table->n - index - 1) * sizeof table->binds[0]);
    --table->n;
    memset(&table->binds[table->n], 0, sizeof table->binds[0]);
}

void ft_output_release_monitor(struct ft_output_table *table, const char *monitor) {
    if (!table || !monitor) return;
    for (int i = 0; i < table->n; ++i) {
        if (strcmp(table->binds[i].monitor, monitor) == 0) {
            drop_at(table, i);
            return;
        }
    }
}

void ft_output_release_screen(struct ft_output_table *table, int screen) {
    if (!table) return;
    for (int i = 0; i < table->n; ++i) {
        if (table->binds[i].screen == screen) {
            drop_at(table, i);
            return;
        }
    }
}

bool ft_output_claim(struct ft_output_table *table, const char *monitor, int screen) {
    if (!table || !name_ok(monitor) || screen < 1 || screen > FT_OUTPUT_BINDS) return false;
    ft_output_release_monitor(table, monitor);
    ft_output_release_screen(table, screen);
    if (table->n >= FT_OUTPUT_BINDS) return false;
    struct ft_output_bind *bind = &table->binds[table->n++];
    memset(bind, 0, sizeof *bind);
    memcpy(bind->monitor, monitor, strlen(monitor) + 1);
    bind->screen = screen;
    return true;
}

int ft_output_screen(const struct ft_output_table *table, const char *monitor) {
    if (!table || !monitor) return 0;
    for (int i = 0; i < table->n; ++i)
        if (strcmp(table->binds[i].monitor, monitor) == 0) return table->binds[i].screen;
    return 0;
}

const char *ft_output_monitor(const struct ft_output_table *table, int screen) {
    if (!table) return NULL;
    for (int i = 0; i < table->n; ++i)
        if (table->binds[i].screen == screen) return table->binds[i].monitor;
    return NULL;
}

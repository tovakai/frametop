-- Frametop native Hyprland 0.56.2 first-boot profile.
-- No Quickshell or host agents: prove rendering and input before porting end-4.
hl.monitor({ output = "", mode = "preferred", position = "auto", scale = 1 })

hl.config({
    general = { gaps_in = 0, gaps_out = 0, border_size = 1, layout = "dwindle" },
    decoration = {
        rounding = 0,
        shadow = { enabled = false },
        blur = { enabled = false },
    },
    animations = { enabled = false },
    misc = { force_default_wallpaper = 0, disable_hyprland_logo = true },
})

-- Additional outputs must use the Wayland backend, not a headless output.
hl.on("hyprland.start", function()
    local startup = os.getenv("FT_HYPRLAND_STARTUP")
    if startup and #startup > 0 then hl.exec_cmd(startup) end
end)

hl.bind("SUPER + Return", hl.dsp.exec_cmd("sh -c 'if command -v foot >/dev/null; then exec foot; elif command -v kitty >/dev/null; then exec kitty; fi'"))
hl.bind("SUPER + SHIFT + E", hl.dsp.exec_cmd("hyprctl dispatch exit"))

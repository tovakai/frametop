-- Frame startup. Replaces hyprland.execs from the laptop config via package.path
-- so that file stays untouched. No hypridle, brightness keys, geoclue agent,
-- or easyeffects. Quickshell is a separate process: if it exits, Hyprland stays.
hl.on("hyprland.start", function()
    local root = os.getenv("FT_FRAME_SESSION")
    if root and #root > 0 then
        hl.exec_cmd(root .. "/frame-quickshell.sh")
    end
end)

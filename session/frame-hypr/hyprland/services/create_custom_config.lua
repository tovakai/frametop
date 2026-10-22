-- Replaces the laptop service that creates ~/.config/hypr/custom on startup.
-- The experimental session reads the staged tree. It does not create files in
-- the Frame user's Hyprland config.
hl.on("hyprland.start", function() end)

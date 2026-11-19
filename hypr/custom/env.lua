-- Custom Environment Variables (Lua)
--
-- API: hl.env(name, value)
--
-- Examples:
-- hl.env("LIBVA_DRIVER_NAME", "nvidia")
-- hl.env("ELECTRON_OZONE_PLATFORM_HINT", "auto")

-- Hyprland starts from a tty1 autologin, so nothing sets this; without it Firefox/Zen
-- think the session is X11 and screen sharing comes out black (no PipeWire/portal).
hl.env("XDG_SESSION_TYPE", "wayland")

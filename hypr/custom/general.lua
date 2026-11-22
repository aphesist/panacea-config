-- Custom General Settings & Overrides (Lua)
--
-- API: hl.config({ section = { key = value } })
--
-- Examples:
-- hl.config({ general = { gaps_in = 6, gaps_out = 12 } })
-- hl.config({ decoration = { rounding = 12 } })

-- Window corners: a bit rounder than Panacea's 12 to match the panel's own
-- corners (logical px; x1.6 on the internal OLED). Same squircle curve.
hl.config({ decoration = { rounding = 16, rounding_power = 4.0 } })

-- Lock screen: render the desktop under the lock surface so the unlock can
-- fade into it (lock surfaces are opaque until the fade starts), and let a
-- relaunched lock take over if the lock client ever crashes.
hl.config({ misc = { session_lock_xray = true, allow_session_lock_restore = true } })

-- Touchpad: right-click by pressing the bottom-right corner (Panacea uses
-- clickfinger, where only a two-finger press right-clicks). A two-finger TAP
-- still right-clicks; a two-finger physical press becomes a left click.
hl.config({ input = { touchpad = { clickfinger_behavior = false } } })

-- Fullscreen on the internal OLED (2026-11-22): it used to re-sync and look worse.
-- - cm_auto_hdr: Hyprland switched the panel to HDR for "HDR" fullscreen apps/videos (a modeset,
--   and SDR content looks washed out in HDR mode on this panel).
-- - send_content_type: let the panel change picture profile by itself for video/game content.
-- - vrr: always-on VRR let the refresh follow a 24-30 fps video in fullscreen; this OLED flickers
--   and shifts brightness at low refresh. Fixed 120 Hz instead.
hl.config({ render = { cm_auto_hdr = 0, send_content_type = false } })
hl.config({ misc = { vrr = 0 } })

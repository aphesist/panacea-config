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

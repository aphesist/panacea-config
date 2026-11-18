-- Custom Window Rules & Layer Rules (Lua)
--
-- API: hl.window_rule({ name = ..., match = { ... }, <rule> = ... })
--
-- Examples:
-- hl.window_rule({ name = "mpv-float", match = { class = "^(mpv)$" }, float = true })
-- hl.window_rule({ name = "discord-ws3", match = { class = "^(discord)$" }, workspace = "3" })

-- Spotify: open as a normal window. Panacea's rule of the same name sends it
-- silently to the hidden scratchpad (special:magic), so launching it looked
-- like nothing happened. Same name = this definition replaces Panacea's.
hl.window_rule({
    name  = "spotify",
    match = { class = "^(Spotify|spotify)$" },
    float = false,
    workspace = "unset",
})

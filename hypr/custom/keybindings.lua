-- Custom Keybindings & Shortcuts (Lua)
--
-- API: hl.bind(combo, dispatcher [, options])
-- Dispatchers live in hl.dsp — hl.dsp.exec_cmd, hl.dsp.killactive, ...
--
-- Examples:
-- hl.bind("SUPER + C", hl.dsp.exec_cmd("code"))
-- hl.bind("SUPER + B", hl.dsp.exec_cmd("brave"))
-- hl.bind("SUPER + SHIFT + Q", hl.dsp.killactive())

-- Island chat (Claude) on Super+C: Panacea has no shortcut for it
hl.bind("SUPER + C", hl.dsp.exec_cmd("qs -p ~/.config/panacea ipc call pill chat"))

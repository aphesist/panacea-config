-- Custom Keybindings & Shortcuts (Lua)
--
-- API: hl.bind(combo, dispatcher [, options])
-- Dispatchers live in hl.dsp — hl.dsp.exec_cmd, hl.dsp.killactive, ...
--
-- Examples:
-- hl.bind("SUPER + C", hl.dsp.exec_cmd("code"))
-- hl.bind("SUPER + B", hl.dsp.exec_cmd("brave"))
-- hl.bind("SUPER + SHIFT + Q", hl.dsp.killactive())

-- Claude in the island. Both shortcuts are set in the island's Shortcuts page
-- (Super+/, "Claude" rows, added by bin/claude-tools-patch.py); they reach us
-- through Panacea's generated lua/binds_data.lua. "" there = turned off.
local okB, binds = pcall(require, "lua.binds_data")
if not okB or type(binds) ~= "table" then binds = {} end
local function claudeBind(id, default, cmd)
    local combo = binds[id]
    if combo == nil then combo = default end
    if combo ~= "" then hl.bind(combo, hl.dsp.exec_cmd(cmd)) end
end
local HOME = os.getenv("HOME")
-- open the chat (Panacea has no shortcut for it)
claudeBind("claudeChat", "SUPER + C", "qs -p " .. HOME .. "/.config/panacea ipc call pill chat")
-- "Ask Claude about this": the selected text or a screen area, into the chat
claudeBind("askClaude", "SUPER + SHIFT + C", HOME .. "/.config/panacea/scripts/custom/ask_claude.sh")

-- task manager in the island (like Ctrl+Shift+Esc on Windows)
hl.bind("SUPER + SHIFT + Escape", hl.dsp.exec_cmd("qs -p " .. os.getenv("HOME") .. "/.config/panacea ipc call pill tasks"))

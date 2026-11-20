-- Custom Autostart Programs & Daemons (Lua)
--
-- API: hl.exec_cmd(command) inside the "hyprland.start" event

local HOME = os.getenv("HOME")
local BIN  = HOME .. "/.config/hypr/custom/bin/"
local RUN  = os.getenv("XDG_RUNTIME_DIR") or "/tmp"

-- ------------------------------------------------- lock-first startup gate
-- Panacea's lua/autostart.lua starts hyprpaper, the pill and the theme
-- restore on "hyprland.start". For the first seconds of a new Hyprland
-- instance those three commands go through custom/bin/after-lock, which
-- holds them until the lock screen confirms the session is locked.
-- `hyprctl reload` re-runs this file but not "hyprland.start"; the
-- per-instance marker below keeps the gate from re-arming then.
local sig = os.getenv("HYPRLAND_INSTANCE_SIGNATURE") or "nosig"
local started = RUN .. "/panacea-started-" .. sig

local function exists(p)
    local f = io.open(p, "r")
    if f then f:close() return true end
    return false
end

if not exists(started) then
    local mark = io.open(started, "w")
    if mark then mark:close() end
    os.remove(RUN .. "/panacea-locked")   -- stale marker from an older session

    local real_exec = hl.exec_cmd
    local gated = { "^hyprpaper", "panacea/scripts/start%.sh", "switch_theme%.sh" }
    local gate_on = true
    hl.exec_cmd = function(cmd, ...)
        if gate_on and type(cmd) == "string" then
            for _, pat in ipairs(gated) do
                if cmd:find(pat) then
                    return real_exec(BIN .. "after-lock " .. cmd, ...)
                end
            end
        end
        return real_exec(cmd, ...)
    end
    local function gate_off()
        gate_on = false
        hl.exec_cmd = real_exec
    end
    pcall(hl.timer, gate_off, { timeout = 8000, type = "oneshot" })

    hl.on("hyprland.start", function()
        real_exec(BIN .. "panacea-lock")
        real_exec("hypridle -c " .. HOME .. "/.config/hypr/custom/hypridle.conf")
        -- the island's Startup screen: apps switched on in hypr/custom/startup-apps.json
        real_exec(HOME .. "/.config/panacea/scripts/custom/startup-apps.py")
    end)
end

-- Lid close also locks when logind won't suspend (e.g. Panacea's
-- "Keep awake" inhibits the lid switch). Panacea's own lid binds are
-- disabled via settings.json (bind_lidOn/bind_lidOff = "") so the lock
-- isn't started twice; panacea-lock's flock dedupes vs hypridle.
hl.bind("switch:on:Lid Switch", hl.dsp.exec_cmd(BIN .. "panacea-lock"), { locked = true })

-- panacea-island: the island drives this player.
-- * Each mpv gets its own JSON IPC socket, $XDG_RUNTIME_DIR/panacea-mpv/<pid>.sock; the island
--   finds the focused mpv window's pid (hyprctl) and talks to that socket.
-- * In a window, uosc's on-screen controls are hidden: the island is the control bar. Its menus
--   still work (the island opens long lists like chapters or the playlist with uosc). In
--   fullscreen the island is hidden, so uosc's controls come back.
local utils = require 'mp.utils'

local dir = (os.getenv('XDG_RUNTIME_DIR') or '/tmp') .. '/panacea-mpv'
local pid = utils.getpid()
local sock = dir .. '/' .. pid .. '.sock'
os.execute('mkdir -p "' .. dir .. '"')
mp.set_property('input-ipc-server', sock)

local HIDE = 'timeline,controls,volume,top_bar,window_border,pause_indicator'
local function apply()
    local fs = mp.get_property_bool('fullscreen', false)
    mp.commandv('script-message-to', 'uosc', 'disable-elements', 'panacea-island', fs and '' or HIDE)
end
mp.observe_property('fullscreen', 'bool', apply)
mp.register_event('file-loaded', apply)    -- uosc may load after this script

mp.register_event('shutdown', function() os.remove(sock) end)

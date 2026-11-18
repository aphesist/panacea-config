-- Internal OLED panel (Galaxy Book3 Ultra). Lives in custom/ so Panacea
-- updates never touch it; loaded after lua.monitors, so it wins.
-- 2880/1.6 = 1800, 1800/1.6 = 1125 -> clean logical size 1800x1125.
hl.monitor({
    output    = "eDP-1",
    mode      = "2880x1800@120",
    position  = "0x0",
    scale     = 1.6,
})

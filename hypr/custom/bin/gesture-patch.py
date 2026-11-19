#!/usr/bin/env python3
"""Three-finger swipe up/down changes the volume (like Windows), instead of
closing the window (down) and toggling fullscreen (up).

Hyprland can't remove a gesture defined elsewhere, so this patches Panacea's
~/.config/hypr/lua/input.lua. Each swipe is one press of the volume keys
(smart_volume.sh: 5%, speeding up on quick repeats, with Panacea's popup).
Hyprland's own gestures fire once per swipe for custom actions, hence a step
per swipe rather than a slider. Idempotent; keeps input.lua.pristine;
re-run by panacea-gesture-patch.path after Panacea updates.
"""
import os, sys

P = os.path.expanduser("~/.config/hypr/lua/input.lua")
VERSION = "v1"
TAG = "-- panacea-local gesture patch "
VOL = 'os.getenv("HOME") .. "/.local/bin/smart_volume.sh '
REPL = [
    ('hl.gesture({ fingers = 3, direction = "down", action = "close" })\n',
     'hl.gesture({ fingers = 3, direction = "down", action = function() hl.exec_cmd(' + VOL + 'down") end })   ' + TAG + VERSION + ': volume down\n'),
    ('hl.gesture({ fingers = 3, direction = "up", action = "fullscreen" })\n',
     'hl.gesture({ fingers = 3, direction = "up", action = function() hl.exec_cmd(' + VOL + 'up") end })   ' + TAG + VERSION + ': volume up\n'),
]


def main():
    cur = open(P, encoding="utf-8").read()
    if TAG + VERSION in cur:
        return 0
    src = open(P + ".pristine", encoding="utf-8").read() if TAG in cur and os.path.exists(P + ".pristine") else cur
    if TAG in src:
        print("gesture-patch: older patch, no pristine copy", file=sys.stderr); return 2
    out = src
    for old, new in REPL:
        if out.count(old) != 1:
            print("gesture-patch: anchor moved, untouched: " + old.strip(), file=sys.stderr); return 2
        out = out.replace(old, new)
    if not os.path.exists(P + ".pristine") or TAG not in cur:
        open(P + ".pristine", "w", encoding="utf-8").write(src)
    with open(P, "r+", encoding="utf-8") as f:
        f.seek(0); f.write(out); f.truncate()
    print("gesture-patch: applied " + VERSION)
    return 0


if __name__ == "__main__":
    sys.exit(main())

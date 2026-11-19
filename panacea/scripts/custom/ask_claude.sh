#!/bin/bash
# "Ask Claude about this" (Super+Shift+C by default; Settings > Claude).
#
# Sends the text you selected, or a part of the screen you draw a box around,
# to the island chat (IPC askAbout, added by portal-patch.py v13), then either
# waits for your question or asks Claude to explain it right away.
#
#   askSource: auto      selected text if it changed since the last ask, else a screen area
#              region    always a screen area
#              selection always the selected text (does nothing without one)
#   askThen:   wait | explain
#
# The screen area works like Panacea's own screenshot (scripts/shot.sh): a still
# frame is shown while you select, then cut from that frame. Nothing is captured
# until you press the key, and the crop stays in ~/.cache/panacea-claude/attachments.
set -u
CFG="$HOME/.config/panacea"
SETTINGS="$CFG/settings.json"
ATT="$HOME/.cache/panacea-claude/attachments"
LAST="$HOME/.cache/panacea-claude/ask-last-selection"
mkdir -p "$ATT"

setting() { jq -r --arg k "$1" --arg d "$2" '.[$k] // $d' "$SETTINGS" 2>/dev/null || echo "$2"; }
ipc() { qs -p "$CFG" ipc call pill "$@" >/dev/null 2>&1; }
ask() {   # ask <draft> <file or "">
    local files='[]'
    [ -n "$2" ] && files=$(jq -nc --arg f "$2" '[$f]')
    ipc askAbout "$(jq -nc --arg d "$1" --argjson f "$files" --argjson s "$SEND" '{draft: $d, files: $f, send: $s}')"
}

SOURCE=$(setting askSource auto)
THEN=$(setting askThen wait)
SEND=false; [ "$THEN" = explain ] && SEND=true
STAMP=$(date +%Y%m%d-%H%M%S)

# ------------------------------------------------------------------ selected text
if [ "$SOURCE" != region ]; then
    SEL=$(timeout 2 wl-paste --primary --no-newline --type text 2>/dev/null | head -c 20000)
    HASH=$(printf '%s' "$SEL" | sha256sum | cut -c1-16)
    # "auto": only a selection made since the last ask counts, so an old one
    # doesn't come back every time
    [ "$SOURCE" = auto ] && [ "$(cat "$LAST" 2>/dev/null)" = "$HASH" ] && SEL=""
    if [ -n "${SEL//[[:space:]]/}" ]; then
        printf '%s' "$HASH" > "$LAST"
        if [ "${#SEL}" -le 400 ]; then
            DRAFT=$(printf '"%s"\n\n' "$SEL")
            $SEND && DRAFT="${DRAFT}Explain this."
            ask "$DRAFT" ""
        else   # long text goes as a file, so the message box stays usable
            F="$ATT/selection-$STAMP.txt"
            printf '%s\n' "$SEL" > "$F"
            DRAFT=""; $SEND && DRAFT="Explain the attached text."
            ask "$DRAFT" "$F"
        fi
        exit 0
    fi
    if [ "$SOURCE" = selection ]; then
        notify-send --app-name "Panacea Claude" "Nothing selected" "Select some text first, then press the shortcut."
        exit 0
    fi
fi

# ------------------------------------------------------------------ a screen area
SHOT=""; FROZEN=0
cleanup() {   # never leave the still frame on screen
    [ "$FROZEN" = 1 ] && ipc unfreeze
    [ -n "$SHOT" ] && rm -f -- "$SHOT"
}
trap cleanup EXIT INT TERM HUP

SHOT=$(mktemp -p "${XDG_RUNTIME_DIR:-/tmp}" panacea-ask.XXXXXXXX.ppm) || exit 1
SNAP=0
grim -t ppm "$SHOT" 2>/dev/null && SNAP=1
if [ "$SNAP" = 1 ] && ipc freeze "$SHOT"; then FROZEN=1; sleep 0.08; fi

GEOM=$(slurp -b 00000060 -c d71921ff -w 2) || exit 0     # Esc / right click = cancel
[ -n "$GEOM" ] || exit 0
if [ "$FROZEN" = 1 ]; then ipc unfreeze; FROZEN=0; fi

OUT="$ATT/screen-$STAMP.png"
if [ "$SNAP" = 1 ]; then
    python3 "$CFG/scripts/shotcrop.py" "$SHOT" "$GEOM" "$OUT" || exit 1
else
    grim -g "$GEOM" "$OUT" || exit 1
fi

DRAFT=""; $SEND && DRAFT="What is this? Explain it."
ask "$DRAFT" "$OUT"

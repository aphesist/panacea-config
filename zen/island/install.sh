#!/bin/bash
# "Panacea for Zen": the add-on + native host the island uses to search and open
# tabs, history and bookmarks in Zen. Plain code, no AI.
#   - host + panacea-zen command -> ~/.local/lib/panacea-zen, ~/.local/bin/panacea-zen
#   - native-messaging file -> /usr/lib/mozilla/native-messaging-hosts (Zen only reads
#     the system-wide folder; pkexec)
#   - the add-on, signed (private, unlisted) with the addons.mozilla.org key in
#     ~/.config/claude-zen-sandbox/amo.env, then Zen asks you to add it
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
LIB="$HOME/.local/lib/panacea-zen"
OWN="$HOME/.local/share/panacea-zen"
AMO_ENV="$HOME/.config/claude-zen-sandbox/amo.env"
WEBEXT="$HOME/.local/share/claude-zen-sandbox/web-ext/node_modules/.bin/web-ext"
SYS="/usr/lib/mozilla/native-messaging-hosts/panacea_zen.json"

install -D -m 755 "$HERE/host/panacea-zen-host.py" "$LIB/panacea-zen-host.py"
install -D -m 755 "$HERE/host/panacea-zen" "$HOME/.local/bin/panacea-zen"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
sed "s|@HOST@|$LIB/panacea-zen-host.py|" "$HERE/host/panacea_zen.json.in" > "$TMP/panacea_zen.json"
cmp -s "$TMP/panacea_zen.json" "$SYS" 2>/dev/null || pkexec install -D -m 644 "$TMP/panacea_zen.json" "$SYS"

VER=$(jq -r .version "$HERE/addon/manifest.json")
SIGNED=$(ls "$OWN"/signed/*-"$VER".xpi 2>/dev/null | head -1 || true)
if [ -z "$SIGNED" ]; then
    [ -f "$AMO_ENV" ] && [ -x "$WEBEXT" ] || { echo "need $AMO_ENV and web-ext (claude-zen-sandbox) to sign"; exit 1; }
    ( set -a; . "$AMO_ENV"; set +a
      cd "$TMP" && "$WEBEXT" sign --source-dir "$HERE/addon" --artifacts-dir "$OWN/signed" \
          --channel unlisted --no-input --api-key "$AMO_JWT_ISSUER" --api-secret "$AMO_JWT_SECRET" 2>&1 | grep -v -i secret )
    SIGNED=$(ls "$OWN"/signed/*-"$VER".xpi 2>/dev/null | head -1 || true)
fi
[ -n "$SIGNED" ] || { echo "signing failed"; exit 1; }
echo "signed: $SIGNED"
HAVE=$(jq -r '[.addons[] | select(.id == "panacea-zen@aphesist" and .active) | .version][0] // empty' \
       "$HOME"/.config/zen/*/extensions.json 2>/dev/null | head -1 || true)
if [ "$HAVE" != "$VER" ]; then
    echo "Zen asks you to add it: click Add."
    zen-browser "$SIGNED" >/dev/null 2>&1 &
fi
echo "done. test: panacea-zen ping"

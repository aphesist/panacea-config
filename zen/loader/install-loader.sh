#!/bin/sh
# Install the userChrome.js loader (fx-autoconfig, MrOtherGuy) for Zen, as root:
# pkexec sh install-loader.sh. Undo: remove the four files listed below.
set -e
D=$(dirname "$(readlink -f "$0")")
install -D -m 644 "$D/config.js"        /usr/local/share/zen-userchromejs/config.js
install -D -m 644 "$D/config-prefs.js"  /usr/local/share/zen-userchromejs/config-prefs.js
install -D -m 644 "$D/zen-userchromejs.hook" /etc/pacman.d/hooks/zen-userchromejs.hook
install -m 644 "$D/config.js"       /opt/zen-browser-bin/config.js
install -m 644 "$D/config-prefs.js" /opt/zen-browser-bin/defaults/pref/config-prefs.js
echo "loader installed"

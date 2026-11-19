#!/usr/bin/env bash
# Install these Panacea customisations into ~/.config. Run as YOUR USER:
#     bash install.sh
# Everything lands in the folders Panacea keeps across updates
# (hypr/custom, fish/custom, foot/custom.ini, panacea/scripts/custom);
# the two Panacea files that get patched (lock.qml, scripts/vault.sh) are
# re-patched automatically after every Panacea update.
# Files that already exist are backed up to ~/.local/state/panacea-config/backup-<time>/.
set -euo pipefail
[ "$(id -u)" -ne 0 ] || { echo "run as your user, not root"; exit 1; }
HERE="$(cd "$(dirname "$0")" && pwd)"
CFG="${XDG_CONFIG_HOME:-$HOME/.config}"
BK="$HOME/.local/state/panacea-config/backup-$(date +%Y%m%d-%H%M%S)"
say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
[ -d "$CFG/panacea" ] || { echo "Panacea not found in $CFG/panacea - install Panacea first"; exit 1; }

put() {   # put <repo path> <destination>
    local src="$HERE/$1" dst="$2"
    if [ -e "$dst" ] && ! cmp -s "$src" "$dst"; then
        mkdir -p "$BK/$(dirname "${dst#$HOME/}")"; cp -a "$dst" "$BK/${dst#$HOME/}"
    fi
    install -Dm"$( [ -x "$src" ] && echo 755 || echo 644 )" "$src" "$dst"
}

say "Hyprland (hypr/custom)"
for f in "$HERE"/hypr/custom/*.lua "$HERE"/hypr/custom/*.conf "$HERE"/hypr/custom/bin/*; do
    put "${f#$HERE/}" "$CFG/${f#$HERE/}"
done

say "Panacea vault <-> Proton Pass bridge, fish, foot"
put panacea/scripts/custom/vault-proton.py "$CFG/panacea/scripts/custom/vault-proton.py"
put panacea/scripts/custom/mullvad_control.py "$CFG/panacea/scripts/custom/mullvad_control.py"
put fish/custom/proton-pass.fish "$CFG/fish/custom/proton-pass.fish"
put foot/custom.ini "$CFG/foot/custom.ini"
mkdir -p "$CFG/environment.d"
printf 'PROTON_PASS_LINUX_KEYRING=dbus\nPROTON_PASS_DISABLE_TELEMETRY=1\n' > "$CFG/environment.d/60-proton-pass.conf"

say "Spotify theme (Spicetify)"
put spotify/spotify-flags.conf "$CFG/spotify-flags.conf"   # native Wayland: scales with the display
put electron/vesktop-flags.conf "$CFG/vesktop-flags.conf"  # Discord (Vesktop), same reason
put electron/claude-desktop-flags.conf "$CFG/claude-desktop-flags.conf"  # Claude desktop: use GNOME Keyring on Hyprland
# Vesktop on a tiling WM: no minimum window size (fits a half tile), no window buttons
mkdir -p "$CFG/vesktop/settings"
V="$CFG/vesktop/settings.json"; [ -s "$V" ] || echo '{}' > "$V"
jq '.disableMinSize=true' "$V" > "$V.new" && cat "$V.new" > "$V" && rm "$V.new"
Q="$CFG/vesktop/settings/quickCss.css"
grep -qs "hide Discord's own window buttons" "$Q" || cat "$HERE/electron/vesktop-quickCss.css" >> "$Q"
for f in "$HERE"/spicetify/Themes/Panacea/*; do put "${f#$HERE/}" "$CFG/${f#$HERE/}"; done
if command -v spicetify >/dev/null && [ -w /opt/spotify ]; then
    spicetify config current_theme Panacea color_scheme Nothing inject_css 1 replace_colors 1 >/dev/null
    spicetify backup apply >/dev/null 2>&1 || spicetify apply >/dev/null 2>&1 || echo "  note: run 'spicetify backup apply' once Spotify has been opened"
else
    echo "  skipped: needs spicetify-cli and a writable /opt/spotify (see README)"
fi

say "Zen Browser: rounder web-content corners (userChrome.css)"
ZEN="$CFG/zen"; ZP=""
if [ -f "$ZEN/installs.ini" ]; then ZP="$(sed -n 's/^Default=//p' "$ZEN/installs.ini" | head -1)"; fi
if [ -n "$ZP" ] && [ -d "$ZEN/$ZP" ]; then
    mkdir -p "$ZEN/$ZP/chrome"
    grep -qs "zen-webview-border-radius" "$ZEN/$ZP/chrome/userChrome.css" || cat "$HERE/zen/userChrome.css" >> "$ZEN/$ZP/chrome/userChrome.css"
    while IFS= read -r line; do   # add each pref that's missing
        key="$(printf '%s' "$line" | sed -n 's/^user_pref("\([^"]*\)".*/\1/p')"
        [ -n "$key" ] && ! grep -qsF "\"$key\"" "$ZEN/$ZP/user.js" && printf '%s\n' "$line" >> "$ZEN/$ZP/user.js"
    done < "$HERE/zen/user.js"
    echo "  done - restart Zen to see it"
else
    echo "  skipped: open Zen once to create its profile, then re-run"
fi

say "Claude desktop: Panacea theme"
if pacman -Q claude-desktop-extra >/dev/null 2>&1; then
    # claude-desktop-extra themes the whole app (Chat, Code, Cowork); applied live
    put claude-desktop/claude-desktop-extra.jsonc "$CFG/Claude/claude-desktop-extra.jsonc"
    echo "  installed - Ctrl+Shift+T in the app lists it as 'panacea'"
elif command -v claude >/dev/null; then
    # official app: themes reach only local Code sessions, via a Claude Code mod
    claude plugin marketplace add "$HERE/claude-desktop" >/dev/null 2>&1 || true
    claude plugin install panacea-look@panacea --scope user >/dev/null 2>&1 && echo "  installed (Code tab only) - open a new local Code session" || echo "  could not install (claude plugin install panacea-look@panacea)"
else
    echo "  skipped: neither claude-desktop-extra nor Claude Code is installed"
fi

say "settings.json overrides (PrtSc screenshot, dictation on Right Ctrl, lid binds, softer motion)"
S="$CFG/panacea/settings.json"
mkdir -p "$BK"; cp -a "$S" "$BK/settings.json"
jq -s '.[0] * .[1]' "$S" "$HERE/settings.overrides.json" > "$S.new" && cat "$S.new" > "$S" && rm "$S.new"

say "systemd user units (splash fix, re-patching after Panacea updates)"
for f in "$HERE"/systemd/user/*; do put "${f#$HERE/}" "$CFG/systemd/user/$(basename "$f")"; done
systemctl --user daemon-reload
systemctl --user enable --now hyprpaper-nosplash.path panacea-vault-patch.path
systemctl --user start panacea-wallpaper.service 2>/dev/null || true   # also started at login by bin/after-lock
systemctl --user start hyprpaper-nosplash.service panacea-vault-patch.service || true

python3 -I "$CFG/hypr/custom/bin/vault-patch.py" || true

say "Island file picker for every app (file-chooser portal backend)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
put portal/panacea.portal "$DATA/xdg-desktop-portal/portals/panacea.portal"
put portal/org.freedesktop.impl.portal.desktop.panacea.service "$DATA/dbus-1/services/org.freedesktop.impl.portal.desktop.panacea.service"
put portal/hyprland-portals.conf "$CFG/xdg-desktop-portal/hyprland-portals.conf"
systemctl --user enable --now panacea-portal-patch.path
python3 -I "$CFG/hypr/custom/bin/portal-patch.py" || echo "  island picker patch skipped - apps keep the GTK dialog"
busctl --user call org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus ReloadConfig >/dev/null 2>&1 || true
systemctl --user try-restart xdg-desktop-portal || true

say "Mullvad in the island (VPN page and country button control the mullvad CLI)"
systemctl --user enable --now panacea-vpn-patch.path
python3 -I "$CFG/hypr/custom/bin/vpn-patch.py" || echo "  VPN patch skipped - Mullvad keeps opening its app"

say "Patching lock.qml now (also re-done before every lock)"
python3 -I "$CFG/hypr/custom/bin/lock-patch.py" || echo "  lock patch skipped (see message above)"

hyprctl reload >/dev/null 2>&1 || true
echo
[ -d "$BK" ] && echo "Backups of replaced files: $BK"
cat <<'EOF'
Done. Still to do once (see README):
  - fingerprint unlock: the PAM file from galaxy-book3-ultra-linux/fingerprint/2-lock-screen-pam.sh
  - Proton Pass: install proton-pass-cli-bin, then  pass-cli login
  - island chat -> Claude: the panacea-claude-bridge repo
EOF

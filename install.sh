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
put fish/custom/proton-pass.fish "$CFG/fish/custom/proton-pass.fish"
put foot/custom.ini "$CFG/foot/custom.ini"
mkdir -p "$CFG/environment.d"
printf 'PROTON_PASS_LINUX_KEYRING=dbus\nPROTON_PASS_DISABLE_TELEMETRY=1\n' > "$CFG/environment.d/60-proton-pass.conf"

say "Spotify theme (Spicetify)"
put spotify/spotify-flags.conf "$CFG/spotify-flags.conf"   # native Wayland: scales with the display
put electron/vesktop-flags.conf "$CFG/vesktop-flags.conf"  # Discord (Vesktop), same reason
# Vesktop on a tiling WM: no minimum window size (fits a half tile), close button only
mkdir -p "$CFG/vesktop/settings"
V="$CFG/vesktop/settings.json"; [ -s "$V" ] || echo '{}' > "$V"
jq '.disableMinSize=true' "$V" > "$V.new" && cat "$V.new" > "$V" && rm "$V.new"
Q="$CFG/vesktop/settings/quickCss.css"
grep -qs "keep only Discord's close button" "$Q" || cat "$HERE/electron/vesktop-quickCss.css" >> "$Q"
for f in "$HERE"/spicetify/Themes/Panacea/*; do put "${f#$HERE/}" "$CFG/${f#$HERE/}"; done
if command -v spicetify >/dev/null && [ -w /opt/spotify ]; then
    spicetify config current_theme Panacea color_scheme Nothing inject_css 1 replace_colors 1 >/dev/null
    spicetify backup apply >/dev/null 2>&1 || spicetify apply >/dev/null 2>&1 || echo "  note: run 'spicetify backup apply' once Spotify has been opened"
else
    echo "  skipped: needs spicetify-cli and a writable /opt/spotify (see README)"
fi

say "settings.json overrides (PrtSc screenshot, dictation on Right Ctrl, lid binds, softer motion)"
S="$CFG/panacea/settings.json"
mkdir -p "$BK"; cp -a "$S" "$BK/settings.json"
jq -s '.[0] * .[1]' "$S" "$HERE/settings.overrides.json" > "$S.new" && cat "$S.new" > "$S" && rm "$S.new"

say "systemd user units (splash fix, vault re-patch on Panacea updates)"
for f in "$HERE"/systemd/user/*; do put "${f#$HERE/}" "$CFG/systemd/user/$(basename "$f")"; done
systemctl --user daemon-reload
systemctl --user enable --now hyprpaper-nosplash.path panacea-vault-patch.path
systemctl --user start hyprpaper-nosplash.service panacea-vault-patch.service || true

python3 -I "$CFG/hypr/custom/bin/vault-patch.py" || true

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

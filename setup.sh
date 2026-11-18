#!/usr/bin/env bash
# One script from a fresh Arch install to this whole setup, always on the
# latest versions: Panacea from upstream, then my four repos on top.
#
#   git clone https://github.com/aphesist/panacea-config ~/src/panacea-config
#   bash ~/src/panacea-config/setup.sh
#
# Run as YOUR USER on a fresh Arch install (after archinstall, with network).
# It is resumable: re-run it after the reboot it asks for and it carries on.
# Every step asks first (y = run, n = skip, q = quit) unless --yes is given;
# root steps are separate scripts it runs with sudo, each verifying itself.
#
#   --yes            don't ask, run every step that applies
#   --no-hardware    skip the Galaxy Book3 Ultra fixes even on that laptop
#   --from <step>    restart from a step (see `--list`)
#   --list           show the steps and which are done
set -euo pipefail
[ "$(id -u)" -ne 0 ] || { echo "Run as your user, not root (it uses sudo where needed)."; exit 1; }
[ -f /etc/arch-release ] || { echo "This is for Arch Linux."; exit 1; }

SRC="$HOME/src"
STATE="$HOME/.local/state/panacea-setup"
mkdir -p "$SRC" "$STATE"
# Run from a private copy: the "repos" step pulls this very repo, and bash
# reads scripts as it goes, so updating the file mid-run would garble it.
if [ -z "${PANACEA_SETUP_COPY:-}" ]; then
    cp "$0" "$STATE/setup.running.sh"
    PANACEA_SETUP_COPY="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")" exec bash "$STATE/setup.running.sh" "$@"
fi
SELF="$PANACEA_SETUP_COPY"   # the real path, for the "re-run" hints
GH=https://github.com
PANACEA_URL=$GH/EnsixD/Panacea
MY_REPOS=(panacea-config panacea-claude-bridge galaxy-book3-ultra-linux arch-setup)
# webcam driver (third-party, runs as root): pinned to the reviewed commit
CAM_URL=$GH/Andycodeman/samsung-galaxy-book-linux-fixes
CAM_COMMIT=d3b1801

YES=0; HW=auto; FROM=""; LIST=0
while [ $# -gt 0 ]; do
    case "$1" in
        --yes|-y) YES=1 ;;
        --no-hardware) HW=0 ;;
        --from) FROM="${2:?--from needs a step name}"; shift ;;
        --list) LIST=1 ;;
        -h|--help) sed -n "2,18p" "$SELF"; exit 0 ;;
        *) echo "unknown option: $1"; exit 1 ;;
    esac
    shift
done

if [ "$HW" = auto ]; then
    grep -q "960XFH" /sys/class/dmi/id/product_name 2>/dev/null && HW=1 || HW=0
fi

c() { printf '\033[%sm%s\033[0m' "$1" "$2"; }
say()  { printf '\n%s %s\n' "$(c '1;36' '==>')" "$*"; }
note() { printf '    %s\n' "$*"; }
die()  { printf '\n%s %s\n' "$(c '1;31' 'xx')" "$*"; exit 1; }
done_mark() { touch "$STATE/$1.done"; }
is_done()   { [ -e "$STATE/$1.done" ]; }

# ask <step> <description>  -> 0 run, 1 skip; q quits
ask() {
    [ "$YES" = 1 ] && return 0
    local a
    while true; do
        printf '\n%s %s\n    %s ' "$(c '1;33' "[$1]")" "$2" "Run it? [y/n/q]"
        read -r a </dev/tty
        case "$a" in y|Y|yes) return 0 ;; n|N|no) return 1 ;; q|Q) echo "Stopped. Re-run to continue."; exit 0 ;; esac
    done
}

clone_or_pull() {   # clone_or_pull <url> <dir>
    if [ -d "$2/.git" ]; then
        git -C "$2" pull --ff-only -q || die "$2 has local changes - commit or stash them, then re-run"
    else
        git clone -q "$1" "$2"
    fi
}

# ------------------------------------------------------------------ steps
step_repos() {
    sudo pacman -S --needed --noconfirm git base-devel jq curl
    clone_or_pull "$PANACEA_URL" "$HOME/Panacea"
    for r in "${MY_REPOS[@]}"; do clone_or_pull "$GH/aphesist/$r" "$SRC/$r"; done
    note "Panacea $(cat "$HOME/Panacea/VERSION" 2>/dev/null || git -C "$HOME/Panacea" log -1 --format=%h)  ·  repos in $SRC"
}

step_panacea() {
    # Panacea's own installer: packages, yay, configs, SDDM + GRUB themes.
    (cd "$HOME/Panacea" && ./install.sh $( [ "$YES" = 1 ] && echo --yes ))
}

step_apps() {
    bash "$SRC/arch-setup/apps/install-apps.sh"
    bash "$SRC/arch-setup/apps/user-setup.sh"
}

step_nvidia() {
    sudo bash "$SRC/galaxy-book3-ultra-linux/nvidia/1-runtime-pm.sh"
    sudo bash "$SRC/galaxy-book3-ultra-linux/nvidia/2-initramfs-udev-rule.sh"
    sudo bash "$SRC/galaxy-book3-ultra-linux/nvidia/3-kernel-7.3-rtd3-patch.sh"
}

step_camera() {
    local d="$SRC/samsung-galaxy-book-linux-fixes"
    [ -d "$d/.git" ] || git clone -q --filter=blob:none "$CAM_URL" "$d"
    git -C "$d" fetch -q origin
    git -C "$d" -c advice.detachedHead=false checkout -q "$CAM_COMMIT"
    note "OV02C10 26 MHz driver @ $CAM_COMMIT (Andycodeman, reviewed)"
    sudo bash "$d/ov02c10-26mhz-fix/install.sh"
    sudo bash "$SRC/galaxy-book3-ultra-linux/camera/install.sh"
    install -Dm644 "$SRC/galaxy-book3-ultra-linux/camera/50-hide-ipu6-raw-v4l2.conf" \
        "$HOME/.config/wireplumber/wireplumber.conf.d/50-hide-ipu6-raw-v4l2.conf"
    install -Dm644 "$SRC/galaxy-book3-ultra-linux/camera/50-egl-mesa.conf" \
        "$HOME/.config/environment.d/50-egl-mesa.conf"
}

step_fingerprint() {
    bash "$SRC/galaxy-book3-ultra-linux/fingerprint/1-install.sh"
    sudo bash "$SRC/galaxy-book3-ultra-linux/fingerprint/2-lock-screen-pam.sh"
    sudo bash "$SRC/galaxy-book3-ultra-linux/fingerprint/3-sudo-fingerprint.sh"
    note "Enroll a finger now (or later):  fprintd-enroll"
    if [ "$YES" = 0 ] && [ -t 0 ]; then
        printf '    Enroll now? [y/N] '; read -r a </dev/tty
        [ "$a" = y ] && fprintd-enroll || true
    fi
}

step_config() {
    bash "$SRC/panacea-config/install.sh"
}

step_proton() {
    command -v pass-cli >/dev/null || yay -S --needed proton-pass-cli-bin
    if PROTON_PASS_LINUX_KEYRING=dbus pass-cli info >/dev/null 2>&1; then
        note "already logged in"
    else
        note "Log in to Proton in the browser window it opens:"
        PROTON_PASS_LINUX_KEYRING=dbus PROTON_PASS_DISABLE_TELEMETRY=1 pass-cli login
    fi
}

step_claude() {
    if [ ! -x "$HOME/.local/bin/claude" ]; then
        note "Installing Claude Code (official installer from claude.ai)"
        curl -fsSL https://claude.ai/install.sh | bash
    fi
    if ! "$HOME/.local/bin/claude" -p --output-format json "Reply: ok" >/dev/null 2>&1; then
        note "Claude Code isn't logged in yet: run  claude  ->  /login  (your subscription), then re-run:"
        note "  bash $SELF --from claude"
        exit 0
    fi
    bash "$SRC/panacea-claude-bridge/install.sh"
}

step_boot() {
    sudo bash "$SRC/arch-setup/boot/1-silent-boot.sh"
    sudo bash "$SRC/arch-setup/boot/2-fix-sddm-qt6.sh"
    sudo bash "$SRC/arch-setup/boot/3-autologin-setup.sh"
    bash "$SRC/arch-setup/boot/5-user-hook.sh"
    done_mark boot
    cat <<EOF

$(c '1;33' 'Reboot now.') In the GRUB menu (it shows once), pick
    "Arch Linux (autologin test)"
It should go straight from the splash to Panacea's lock screen.
If it does, log in and run   bash $SELF   again to make it the default.
If it doesn't, reboot normally: SDDM is still the default (see arch-setup/RECOVERY.md).
EOF
    sudo grub-editenv - set menu_once=1 2>/dev/null || true
    exit 0
}

step_autologin() {
    grep -q "autologin test" /boot/grub/grub.cfg 2>/dev/null || { note "test entry not present - already finalised?"; return 0; }
    if [ "$YES" = 0 ]; then
        printf '    Did the "autologin test" boot reach the lock screen? [y/N] '; read -r a </dev/tty
        [ "$a" = y ] || { note "Not finalising; SDDM stays the default. Re-run when the test boot works."; exit 0; }
    fi
    sudo bash "$SRC/arch-setup/boot/4-autologin-finalize.sh"
}

# name | needs hardware | description
STEPS=(
  "repos|0|Fetch the latest Panacea + my repos into ~/Panacea and $SRC"
  "panacea|0|Install Panacea (upstream installer: packages, yay, configs, SDDM/GRUB themes)"
  "apps|0|Apps + full dev toolchain (Zen, Spotify+Spicetify, Zed, Claude desktop, Figma, Rust/Python/Node/Go/Java/Zig, Docker, mise)"
  "nvidia|1|RTX runtime power management + kernel 7.3 RTD3 patch"
  "camera|1|Webcam driver (26 MHz fork, pinned) + rotation, gain, one camera in browsers"
  "fingerprint|1|SDCP libfprint (Egis reader), lock-screen + sudo fingerprint"
  "config|0|panacea-config: lock screen, idle, vault bridge, motion, PrtSc, Spotify theme"
  "proton|0|Proton Pass CLI + login (Panacea's vault syncs with it)"
  "claude|0|Claude Code + the island chat bridge (your subscription)"
  "boot|0|Silent boot + autologin test entry (then reboot)"
  "autologin|0|Make autologin the default (after the test boot worked)"
)

if [ "$LIST" = 1 ]; then
    for s in "${STEPS[@]}"; do IFS='|' read -r n h d <<<"$s"
        m=" "; is_done "$n" && m="✓"; [ "$h" = 1 ] && [ "$HW" = 0 ] && m="-"
        printf ' %s %-12s %s\n' "$m" "$n" "$d"; done
    exit 0
fi
if [ -n "$FROM" ]; then
    hit=0; for s in "${STEPS[@]}"; do n="${s%%|*}"; [ "$n" = "$FROM" ] && hit=1; [ "$hit" = 1 ] && rm -f "$STATE/$n.done"; done
    [ "$hit" = 1 ] || die "no step named '$FROM' (see --list)"
fi

echo
c '1;37' "Panacea / Arch setup"; echo
note "Laptop: $(cat /sys/class/dmi/id/product_name 2>/dev/null)   ·   hardware fixes: $([ "$HW" = 1 ] && echo yes || echo 'no (not a Galaxy Book3 Ultra)')"
note "Progress is kept in $STATE  (bash $SELF --list)"
sudo -v || die "sudo is needed"

for s in "${STEPS[@]}"; do
    IFS='|' read -r name hw desc <<<"$s"
    is_done "$name" && continue
    [ "$hw" = 1 ] && [ "$HW" = 0 ] && continue
    if ask "$name" "$desc"; then
        say "$name"
        "step_$name"
        done_mark "$name"
    else
        note "skipped (run later with: bash $SELF --from $name)"
        done_mark "$name"
    fi
done

say "All done."
cat <<'EOF'
    - Open Spotify once and log in, then:  spicetify backup apply
    - Log out and back in for the docker group
    - Wallpapers: Super+Shift+T · lock: Super+L · launcher: Super+A
EOF

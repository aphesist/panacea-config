#!/usr/bin/env bash
# Is the internet fine, with the VPN on or off? Run after a suspend/resume or a reboot.
# Appends to mullvad-check.log next to this script (no IPs or account details).
LOG="$(dirname "$0")/mullvad-check.log"
r() { "$@" >/dev/null 2>&1 && echo ok || echo FAIL; }
line=$(printf "%s  %-10s daemon=%-8s status=%-13s lockdown=%-3s ping=%-4s dns=%-4s via-mullvad=%s" \
    "$(date '+%F %T')" "${1:-check}" "$(systemctl is-active mullvad-daemon)" \
    "$(mullvad status 2>/dev/null | head -1)" \
    "$(mullvad lockdown-mode get 2>/dev/null | grep -q ': on' && echo on || echo off)" \
    "$(r ping -c1 -W3 1.1.1.1)" "$(r getent hosts archlinux.org)" \
    "$(curl -s -m 10 https://am.i.mullvad.net/json | jq -r .mullvad_exit_ip 2>/dev/null)")
echo "$line" | tee -a "$LOG"

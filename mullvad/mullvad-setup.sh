#!/usr/bin/env bash
# Mullvad, part 1: a setup where the internet keeps working whenever the VPN is off.
# Each step checks connectivity; if DNS breaks, the DNS change is rolled back.
set -uo pipefail

ok()   { printf '  \e[32mok\e[0m  %s\n' "$*"; }
bad()  { printf '  \e[31m!!\e[0m  %s\n' "$*"; }
net()  { ping -c1 -W3 1.1.1.1 >/dev/null 2>&1; }
dns()  { getent ahosts archlinux.org >/dev/null 2>&1; }
check(){ net && ok "internet (ping 1.1.1.1)" || bad "no internet"; dns && ok "DNS (archlinux.org)" || bad "no DNS"; }

echo "== before"; check

echo "== 1. remove the debug-symbols package installed by mistake"
pacman -Q mullvad-vpn-bin-debug >/dev/null 2>&1 && sudo pacman -R --noconfirm mullvad-vpn-bin-debug && ok removed || ok "not installed"

echo "== 2. early-boot blocker off (it blocks all traffic until the daemon starts;"
echo "      started late during the install, it left a block-everything rule behind)"
sudo systemctl disable mullvad-early-boot-blocking.service && ok disabled

echo "== 3. DNS through systemd-resolved, with NetworkManager feeding it (Mullvad's recommended setup)"
sudo cp -a /etc/resolv.conf /etc/resolv.conf.pre-resolved 2>/dev/null
sudo install -Dm644 /dev/stdin /etc/NetworkManager/conf.d/dns.conf <<'EOF'
# NetworkManager hands its DNS servers (your router's when the VPN is off) to
# systemd-resolved; Mullvad sets its own on the tunnel when connected.
[main]
dns=systemd-resolved
EOF
sudo systemctl enable --now systemd-resolved.service
sudo ln -sf /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf
sudo systemctl reload NetworkManager
sleep 3
if dns; then
    ok "DNS works through systemd-resolved"
else
    bad "DNS broke - rolling back step 3"
    sudo rm -f /etc/NetworkManager/conf.d/dns.conf
    sudo cp -a /etc/resolv.conf.pre-resolved /etc/resolv.conf
    sudo systemctl disable --now systemd-resolved.service
    sudo systemctl reload NetworkManager
fi

echo "== 4. start the Mullvad daemon (disconnected, lockdown off) and check nothing is blocked"
sudo systemctl start mullvad-daemon.service
sleep 4
mullvad lockdown-mode get
mullvad status
echo "  Mullvad firewall table (should hold no blocking rules while disconnected):"
sudo nft list table inet mullvad 2>/dev/null | grep -cE "drop|reject" | xargs -I{} echo "    drop/reject rules: {}"

echo "== ufw: left as is (enabled; default deny incoming, allow outgoing)"
sudo ufw status verbose | sed -n 1,4p

echo "== after"; check

#!/usr/bin/env bash
# If Mullvad ever cuts the internet while it shouldn't: stop it and remove its firewall table.
sudo systemctl stop mullvad-daemon.service mullvad-early-boot-blocking.service
sudo nft delete table inet mullvad 2>/dev/null
ping -c1 -W3 1.1.1.1 >/dev/null && echo "internet back" || echo "still no internet - check 'sudo nft list ruleset'"

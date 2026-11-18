# Proton Pass CLI: keep the session key in GNOME Keyring (Secret Service) so it
# survives reboots (the default kernel keyring is wiped at every boot), and no telemetry.
set -gx PROTON_PASS_LINUX_KEYRING dbus
set -gx PROTON_PASS_DISABLE_TELEMETRY 1

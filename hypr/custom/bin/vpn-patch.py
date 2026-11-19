#!/usr/bin/env python3
"""Mullvad in Panacea's VPN control: the island's country button and the VPN
page's power button connect/disconnect Mullvad directly, and the island shows
its real state.

Panacea's vpn.py has direct control for one client (Happ); every other app
only gets launched. This routes Mullvad to an adapter that drives its CLI,
~/.config/panacea/scripts/custom/mullvad_control.py (a folder Panacea keeps
across updates), and tells the VPN page that Mullvad is directly controllable.

Patches scripts/vpn.py and VpnView.qml. All-or-nothing and idempotent; keeps
*.pristine copies; if an anchor moved, nothing changes (Mullvad then just
opens its app, as before). Re-run by panacea-vpn-patch.path after updates.
"""
import os, sys

D = os.path.expanduser("~/.config/panacea")
VERSION = "v2"
PY_PREFIX = "# panacea-local vpn patch "
QML_PREFIX = "// panacea-local vpn patch "

VPN_PY = [
    ("        if client.stem.casefold() != 'happ':\n",
     "        if 'mullvad' in client.stem.casefold():   " + PY_PREFIX + VERSION + "\n"
     "            sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / 'custom'))\n"
     "            import mullvad_control\n"
     "            return mullvad_control.status() if op == 'client-status' else mullvad_control.toggle()\n"
     "        if client.stem.casefold() != 'happ':\n"),
]

VPN_VIEW = [
    ('    readonly property bool directControl: !selectedClient || selectedClient.toLowerCase().endsWith("/happ.desktop")\n',
     '    readonly property bool directControl: !selectedClient || selectedClient.toLowerCase().endsWith("/happ.desktop")\n'
     '                                          || /\\/mullvad[^\\/]*\\.desktop$/.test(selectedClient.toLowerCase())   ' + QML_PREFIX + VERSION + '\n'),
    ('subtitle: modelData.desktop.toLowerCase().endsWith("/happ.desktop") ? view.sys.tr("Управление подключением через Happ") : view.sys.tr("Управление в приложении клиента")',
     'subtitle: /\\/mullvad[^\\/]*\\.desktop$/.test(modelData.desktop.toLowerCase()) ? "Connect and disconnect from the island"\n'
     '                              : modelData.desktop.toLowerCase().endsWith("/happ.desktop") ? view.sys.tr("Управление подключением через Happ") : view.sys.tr("Управление в приложении клиента")'),
    ('    function chooseClient(path) { sys.cfg.vpnPreferredClient = path; sys.cfg.vpnPreferred = ""; sys.saveCfg(); sys.refreshVpnStatus(); }\n',
     '    function chooseClient(path) { sys.cfg.vpnPreferredClient = path; sys.cfg.vpnPreferred = ""; sys.saveCfg(); sys.refreshVpnStatus(); sys.vpnClassic = false; }\n'),
]

# the island's Mullvad page (shown instead of this one when Mullvad is the client;
# shell.qml's side of it lives in portal-patch.py, which owns shell.qml)
PAGE_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "MullvadView.qml")


def plan(path, repl, prefix):
    tag = prefix + VERSION
    cur = open(path, encoding="utf-8").read()
    if tag in cur:
        return cur, None
    if prefix in cur:
        if not os.path.exists(path + ".pristine"):
            print(f"vpn-patch: {os.path.basename(path)} has an older patch but no pristine copy", file=sys.stderr)
            return None
        src = open(path + ".pristine", encoding="utf-8").read()
    else:
        src = cur
    out = src
    for old, new in repl:
        if out.count(old) != 1:
            print(f"vpn-patch: anchor not found in {os.path.basename(path)}: {old.strip()[:60]!r}", file=sys.stderr)
            return None
        out = out.replace(old, new, 1)
    return out, (src if prefix not in src else None)


def write(path, text):
    # in place: Quickshell's file watcher loses a file that is swapped for a new one
    with open(path, "r+" if os.path.exists(path) else "w", encoding="utf-8") as f:
        f.seek(0)
        f.write(text)
        f.truncate()


def main():
    targets = [(os.path.join(D, "scripts/vpn.py"), VPN_PY, PY_PREFIX),
               (os.path.join(D, "VpnView.qml"), VPN_VIEW, QML_PREFIX)]
    plans = []
    for path, repl, prefix in targets:
        p = plan(path, repl, prefix)
        if p is None:
            print("vpn-patch: untouched - Mullvad keeps opening its app", file=sys.stderr)
            return 2
        plans.append((path, p))
    changed = False
    if os.path.exists(PAGE_SRC):
        page = open(PAGE_SRC, encoding="utf-8").read()
        dst = os.path.join(D, "MullvadView.qml")
        if not os.path.exists(dst) or open(dst, encoding="utf-8").read() != page:
            write(dst, page)
            changed = True
    for path, (out, pristine) in plans:
        if pristine is not None:
            write(path + ".pristine", pristine)
        if out != open(path, encoding="utf-8").read():
            write(path, out)
            changed = True
    if changed:
        print(f"vpn-patch: applied {VERSION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

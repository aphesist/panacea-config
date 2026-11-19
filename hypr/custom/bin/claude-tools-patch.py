#!/usr/bin/env python3
"""Settings for the island chat's Claude tools: a "Claude" page in Panacea's
settings (SetClaude.qml: the browser via Claudezilla, "Ask Claude about this")
and two rows in the Shortcuts page (open the chat, ask about this).

The settings themselves (cfg.claudeBrowser, askSource, bind_askClaude...) and the
askAbout IPC call are added to shell.qml by portal-patch.py (v13+); the chat side
by chat-patch.py (v31+). The shortcuts are bound by hypr/custom/keybindings.lua,
which reads them from ~/.config/hypr/lua/binds_data.lua (Panacea's genbinds.sh).

Patches SettingsView.qml and SetKeys.qml. All-or-nothing and idempotent; keeps
*.pristine copies so a newer version upgrades cleanly. If Panacea moved an anchor,
nothing changes. Re-run by panacea-claude-tools-patch.path after Panacea updates.
"""
import os, sys

D = os.path.expanduser("~/.config/panacea")
HERE = os.path.dirname(os.path.abspath(__file__))
VERSION = "v1"
TAG_PREFIX = "// panacea-local claude tools patch "
TAG = TAG_PREFIX + VERSION

SETTINGS_VIEW = [
    ('        { id: "vpn", title: "VPN", g: 0xF0582, page: "SetVpn.qml",\n',
     '        { id: "claude", title: "Claude", g: 0xF0674, page: "SetClaude.qml",   ' + TAG + '\n'
     '          sub: "The island chat\'s tools: your browser, and asking about anything on screen.",\n'
     '          keys: "claude ai chat browser zen firefox claudezilla ask selection screenshot region explain shortcut" },\n'
     '        { id: "vpn", title: "VPN", g: 0xF0582, page: "SetVpn.qml",\n'),
    ('        { id: "vpn", title: "VPN", g: 0xF0582, pages: ["vpn"] },\n',
     '        { id: "claude", title: "Claude", g: 0xF0674, pages: ["claude"] },   ' + TAG + '\n'
     '        { id: "vpn", title: "VPN", g: 0xF0582, pages: ["vpn"] },\n'),
]

SET_KEYS = [
    ('            BindRow { bindId: "pillVault";     label: page.sys.tr("Менеджер паролей") }\n',
     '            BindRow { bindId: "pillVault";     label: page.sys.tr("Менеджер паролей") }\n'
     '\n'
     '            Head { text: "Claude" }   ' + TAG + '\n'
     '            BindRow { bindId: "claudeChat"; label: "Open the chat" }\n'
     '            BindRow { bindId: "askClaude";  label: "Ask Claude about this" }\n'),
]


def plan(path, repl):
    """-> (new text, pristine text to save or None), or None if an anchor is missing."""
    cur = open(path, encoding="utf-8").read()
    if TAG in cur:
        return cur, None
    if TAG_PREFIX in cur:
        if not os.path.exists(path + ".pristine"):
            print(f"claude-tools-patch: {os.path.basename(path)} has an older patch but no pristine copy", file=sys.stderr)
            return None
        src = open(path + ".pristine", encoding="utf-8").read()
    else:
        src = cur
    out = src
    for old, new in repl:
        if out.count(old) != 1:
            print(f"claude-tools-patch: anchor not found in {os.path.basename(path)}: {old.strip()[:50]!r}", file=sys.stderr)
            return None
        out = out.replace(old, new, 1)
    return out, (src if TAG_PREFIX not in src else None)


def write(path, text):
    # In place, not tmp + rename: Quickshell's file watcher loses a file that is
    # swapped for a new one, and then never reloads the shell.
    with open(path, "r+" if os.path.exists(path) else "w", encoding="utf-8") as f:
        f.seek(0)
        f.write(text)
        f.truncate()


def main():
    targets = [(os.path.join(D, "SettingsView.qml"), SETTINGS_VIEW), (os.path.join(D, "SetKeys.qml"), SET_KEYS)]
    plans = []
    for path, repl in targets:
        p = plan(path, repl)
        if p is None:
            print("claude-tools-patch: untouched", file=sys.stderr)
            return 2
        plans.append((path, p))
    changed = False
    src = os.path.join(HERE, "SetClaude.qml")       # written first: SettingsView points at it
    body = open(src, encoding="utf-8").read()
    dst = os.path.join(D, "SetClaude.qml")
    if not os.path.exists(dst) or open(dst, encoding="utf-8").read() != body:
        write(dst, body)
        changed = True
    for path, (out, pristine) in plans:
        if pristine is not None:
            write(path + ".pristine", pristine)
        if out != open(path, encoding="utf-8").read():
            write(path, out)
            changed = True
    if changed:
        print(f"claude-tools-patch: applied {VERSION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

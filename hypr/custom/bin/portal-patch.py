#!/usr/bin/env python3
"""One file picker for Panacea, inside the island: the chat's paperclip and
other apps' Open/Save dialogs (via panacea-portal.py) morph the island into
its file manager in picker mode, instead of a window Hyprland tiles behind it.

Patches shell.qml (picker state, an IPC entry point, the files page) and
FilesView.qml (a "cancelled" signal). All-or-nothing and idempotent; keeps
*.pristine copies so a newer patch version upgrades cleanly. If Panacea moved
any anchor, nothing is changed and apps keep the GTK dialog (the backend falls
back on its own). Re-run by panacea-portal-patch.path after Panacea updates.
"""
import os, sys

D = os.path.expanduser("~/.config/panacea")
VERSION = "v6"
TAG_PREFIX = "// panacea-local portal patch "
TAG = TAG_PREFIX + VERSION

SHELL = [
    ("    signal chatFilesPicked(var paths)\n",
     "    signal chatFilesPicked(var paths)\n"
     "    " + TAG + r""": one file picker, inside the island.
    // The chat's paperclip and other apps' Open/Save dialogs (panacea-portal.py)
    // morph the island into its file manager instead of opening a window that
    // Hyprland would tile behind the island.
    property var islandPick: null          // {kind: "chat"|"portal", multiple, directory, save, name, folder, accept, id}
    property var pendingChatAttach: []     // ChatView's attachments while the picker is up
    property string chatDraft: ""          // ...and its unsent text
    readonly property string portalScript: Quickshell.env("HOME") + "/.config/hypr/custom/bin/panacea-portal.py"
    Process { id: portalReplyProc }
    function startIslandPick(spec) {
        if (root.islandPick) root.endIslandPick(false, [], true);
        pageResetTimer.stop();
        root.islandPick = spec;
        root.page = "files"; root.expanded = true; root.holdOpen = true;
    }
    // quiet: the island was dismissed, so don't reopen the chat
    function endIslandPick(ok, paths, quiet) {
        var p = root.islandPick; if (!p) return;
        root.islandPick = null;
        if (p.kind === "chat") {
            if (ok) root.pendingChatAttach = (root.pendingChatAttach || []).concat(paths || []);
            if (!quiet) { root.page = "chat"; root.expanded = true; root.holdOpen = true; }
        } else {
            portalReplyProc.command = ["python3", "-I", root.portalScript, "--reply", String(p.id),
                                       JSON.stringify({ ok: ok, paths: paths || [] })];
            portalReplyProc.running = true;
            if (!quiet) root.collapse();
        }
    }
    Connections {
        target: root
        function onChatFilePickerOpenChanged() {
            if (!root.chatFilePickerOpen) return;
            root.chatFilePickerOpen = false;
            root.startIslandPick({ kind: "chat", multiple: true, accept: "Attach" });
        }
        function onPageChanged() { if (root.islandPick && root.page !== "files") root.endIslandPick(false, [], true); }
        function onExpandedChanged() { if (!root.expanded && root.islandPick) root.endIslandPick(false, [], true); }
    }
"""),
    ('        function chat(): void { root.page = "chat"; root.expanded = true; root.holdOpen = true; }\n',
     '        function chat(): void { root.page = "chat"; root.expanded = true; root.holdOpen = true; }\n'
     "        function pickFile(spec: string): void {   " + TAG + "\n"
     "            var s; try { s = JSON.parse(spec); } catch (e) { return; }\n"
     "            s.kind = \"portal\";\n"
     "            root.startIslandPick(s);\n"
     "        }\n"),
    # the approval toast's green check / red cross circles -> flat Deny / Allow pills
    ("""                        width: 30; height: 30; radius: 15
                        color: modelData.action === "panacea-allow" ? "#305f46" : "#643f45"
                        Text { anchors.centerIn: parent; text: modelData.label; color: modelData.action === "panacea-allow" ? "#9be0b1" : "#f0b3b6"; font { pixelSize: 17; bold: true } }
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.replyAgentApproval(modelData.action) }
""", """                        // """ + TAG + """: flat pills in Panacea's palette (white = primary), like the chat's approval card
                        width: 76; height: 28; radius: 14
                        readonly property bool primary: modelData.action === "panacea-allow"
                        color: primary ? (apMa.containsMouse ? Qt.rgba(1, 1, 1, 0.85) : root.colFg)
                                       : (apMa.containsMouse ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(1, 1, 1, 0.09))
                        Behavior on color { ColorAnimation { duration: 120 } }
                        Text { anchors.centerIn: parent; text: parent.primary ? "Allow" : "Deny"
                               color: parent.primary ? root.colBg : root.colFg
                               font { family: root.fontFam; pixelSize: root.fontSize - 3; bold: parent.primary } }
                        MouseArea { id: apMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.replyAgentApproval(modelData.action) }
"""),
    # The toast's icon. Claude's approval cards get the pixel Claude from the
    # chat instead: no tile behind it, bigger, and animated (it waves for your
    # attention). Taller approval cards also centre the icon vertically.
    ("""                Layout.preferredWidth: 34
                Layout.preferredHeight: 34
                Layout.alignment: Qt.AlignTop
                radius: 10
                color: root.notifUrgent ? Qt.rgba(1, 0.27, 0.27, 0.18)
                                        : Qt.rgba(1, 1, 1, 0.08)
""", """                // """ + TAG + """
                readonly property bool claude: root.notifApp === "Panacea Claude"
                Layout.preferredWidth: claude ? 44 : 34
                Layout.preferredHeight: claude ? 40 : 34
                Layout.alignment: root.approvalToast ? Qt.AlignVCenter : Qt.AlignTop
                radius: 10
                color: claude ? "transparent"
                     : root.notifUrgent ? Qt.rgba(1, 0.27, 0.27, 0.18)
                                        : Qt.rgba(1, 1, 1, 0.08)
"""),
    ("""                    visible: source != "" && status === Image.Ready
""", """                    visible: source != "" && status === Image.Ready && !parent.claude
"""),
    ("""                    visible: !toastIcon.visible
""", """                    visible: !toastIcon.visible && !parent.claude
"""),
    ("""                    font { family: root.fontFam; pixelSize: root.iconSize - 1 }
                }
            }
""", """                    font { family: root.fontFam; pixelSize: root.iconSize - 1 }
                }
                // the pixel Claude, asking for you: arms wave in turn, feet tap, it blinks
                Item {
                    id: toastCritter
                    visible: parent.claude
                    anchors.centerIn: parent
                    readonly property int px: 4
                    property int frame: 0          // 0 left arm up, 1 rest, 2 right arm up, 3 rest
                    property bool blink: false
                    readonly property var frames: [
                        ["..XXXXXXX..", "XXXXXXXXX..", "XXXEXXXEX..", "..XXXXXXXXX", "..XXXXXXXXX", "..XXXXXXX..", "..X.X.X.X.."],   // left arm up
                        ["..XXXXXXX..", "..XXXXXXX..", "..XEXXXEX..", "XXXXXXXXXXX", "XXXXXXXXXXX", "..XXXXXXX..", ".X.X.X.X..."],   // rest
                        ["..XXXXXXX..", "..XXXXXXXXX", "..XEXXXEXXX", "XXXXXXXXX..", "XXXXXXXXX..", "..XXXXXXX..", "..X.X.X.X.."],   // right arm up
                        ["..XXXXXXX..", "..XXXXXXX..", "..XEXXXEX..", "XXXXXXXXXXX", "XXXXXXXXXXX", "..XXXXXXX..", ".X.X.X.X..."]]   // rest
                    readonly property var rows: frames[frame]
                    width: 11 * px; height: 7 * px
                    Timer { interval: 260; repeat: true; running: toastCritter.visible
                            onTriggered: toastCritter.frame = (toastCritter.frame + 1) % 4 }
                    Timer { interval: 2600; repeat: true; running: toastCritter.visible
                            onTriggered: { toastCritter.blink = true; critterUnblink.restart(); } }
                    Timer { id: critterUnblink; interval: 150; onTriggered: toastCritter.blink = false }
                    Grid {
                        columns: 11
                        y: toastCritter.frame % 2 === 0 ? -2 : 0     // a little hop on each wave
                        Behavior on y { NumberAnimation { duration: 120; easing.type: Easing.OutQuad } }
                        Repeater {
                            model: 77
                            Rectangle {
                                required property int index
                                readonly property string ch: toastCritter.rows[Math.floor(index / 11)].charAt(index % 11)
                                width: toastCritter.px; height: toastCritter.px
                                color: ch === "." ? "transparent"
                                     : ch === "E" && !toastCritter.blink ? "#141414" : "#d97757"
                            }
                        }
                    }
                }
            }
"""),
    # the island's chat tab is Claude's: "Claude" and its logo
    ('{page:"chat", title:root.tr("Чат"), icon:0xF0181}', '{page:"chat", title:"Claude", icon:0xF0181}'),
    ("""IslandTabIcon { anchors.verticalCenter: parent.verticalCenter; width: 19; height: 19; kind: modelData.page === "main" ? "home" : "chat"; tint: root.page === modelData.page ? root.colFg : root.colMuted }""", """IslandTabIcon { anchors.verticalCenter: parent.verticalCenter; width: 19; height: 19; kind: modelData.page === "main" ? "home" : "chat"; tint: root.page === modelData.page ? root.colFg : root.colMuted
                                        visible: modelData.page !== "chat" || tabClaudeLogo.status !== Image.Ready }
                        // """ + TAG + """: the chat tab is Claude's (panacea-claude-bridge): its logo, white like the rest
                        Image { id: tabClaudeLogo; visible: modelData.page === "chat" && status === Image.Ready
                                anchors.verticalCenter: parent.verticalCenter; width: 17; height: 17
                                sourceSize: Qt.size(68, 68); fillMode: Image.PreserveAspectFit; smooth: true; mipmap: true
                                source: "file://" + Quickshell.env("HOME") + "/.config/panacea-claude/claude-logo.svg"
                                opacity: root.page === modelData.page ? 1 : 0.55 }"""),
    # the old windowed chat picker is never opened any more
    ("    active: root.chatFilePickerOpen\n    FloatingWindow {\n    id: chatPickerWindow\n",
     "    active: false   " + TAG + ": replaced by the island picker\n    FloatingWindow {\n    id: chatPickerWindow\n"),
    ("        Component { id: filesComp;    FilesView { sys: root } }\n",
     "        Component { id: filesComp;    Item {   " + TAG + r"""
            id: filesWrap
            readonly property var pick: root.islandPick
            readonly property bool saving: !!(pick && pick.save)
            readonly property bool folders: !!(pick && pick.directory)
            implicitHeight: filesInner.implicitHeight + (pick ? pickBar.height + 12 : 0)
            function accept() {
                if (filesWrap.saving) {
                    var n = nameField.text.trim(); if (!n) return;
                    root.endIslandPick(true, [(filesInner.dir === "/" ? "" : filesInner.dir) + "/" + n]);
                } else if (filesWrap.folders) {
                    root.endIslandPick(true, filesInner.selectedCount > 0 ? filesInner.selectedPaths : [filesInner.dir]);
                } else if (filesInner.selectedCount > 0) {
                    root.endIslandPick(true, filesInner.selectedPaths);
                }
            }
            readonly property bool canAccept: filesWrap.saving ? nameField.text.trim().length > 0
                                             : (filesWrap.folders || filesInner.selectedCount > 0)
            FilesView {
                id: filesInner
                anchors { left: parent.left; right: parent.right; top: parent.top }
                sys: root
                pickerMode: filesWrap.pick !== null
                dir: filesWrap.pick ? String(filesWrap.pick.folder || "") : ""
                onFilePicked: path => {
                    if (filesWrap.saving) nameField.text = path.split("/").pop();
                    else if (!filesWrap.folders) root.endIslandPick(true, [path]);
                }
                onPickCancelled: root.endIslandPick(false, [])
            }
            RowLayout {
                id: pickBar
                visible: filesWrap.pick !== null
                anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                height: 34; spacing: 10
                Rectangle {
                    visible: filesWrap.saving
                    Layout.fillWidth: true; Layout.preferredHeight: 34
                    radius: 17; color: Qt.rgba(1, 1, 1, 0.06); border.color: root.colLine; border.width: 1
                    TextInput {
                        id: nameField
                        anchors { fill: parent; leftMargin: 16; rightMargin: 16 }
                        verticalAlignment: TextInput.AlignVCenter
                        text: filesWrap.pick ? String(filesWrap.pick.name || "") : ""
                        color: root.colFg; selectionColor: Qt.rgba(1, 1, 1, 0.25); clip: true
                        font { family: root.fontFam; pixelSize: 13 }
                        Keys.onReturnPressed: filesWrap.accept()
                        Keys.onEscapePressed: root.endIslandPick(false, [])
                    }
                }
                Item { visible: !filesWrap.saving; Layout.fillWidth: true }
                Repeater {
                    model: [{ text: root.tr("Отмена"), accept: false },
                            { text: String((filesWrap.pick && filesWrap.pick.accept) || "") ||
                                    (filesWrap.saving ? "Save" : filesWrap.folders ? "Use this folder" : "Open"), accept: true }]
                    delegate: Rectangle {
                        required property var modelData
                        Layout.preferredWidth: Math.max(112, label.implicitWidth + 36); Layout.preferredHeight: 34
                        radius: 17
                        color: modelData.accept ? root.colFg : Qt.rgba(1, 1, 1, 0.09)
                        opacity: modelData.accept && !filesWrap.canAccept ? 0.4 : 1
                        Text { id: label; anchors.centerIn: parent; text: modelData.text
                               color: modelData.accept ? root.colBg : root.colFg; font.family: root.fontFam }
                        MouseArea {
                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            enabled: !modelData.accept || filesWrap.canAccept
                            onClicked: modelData.accept ? filesWrap.accept() : root.endIslandPick(false, [])
                        }
                    }
                }
            }
        } }
"""),
]

FILES = [
    ("    signal filePicked(string path)\n",
     "    signal filePicked(string path)\n"
     "    signal pickCancelled()   " + TAG + "\n"),
    ("        if (view.pickerMode) view.sys.chatFilePickerOpen = false;\n",
     "        if (view.pickerMode) { view.sys.chatFilePickerOpen = false; view.pickCancelled(); }   " + TAG + "\n"),
]


def plan(path, repl):
    """-> (new text, pristine text to save or None), or None if an anchor is missing."""
    cur = open(path, encoding="utf-8").read()
    if TAG in cur:
        return cur, None
    if TAG_PREFIX in cur:
        if not os.path.exists(path + ".pristine"):
            print(f"portal-patch: {os.path.basename(path)} has an older patch but no pristine copy", file=sys.stderr)
            return None
        src = open(path + ".pristine", encoding="utf-8").read()
    else:
        src = cur
    out = src
    for old, new in repl:
        if out.count(old) != 1:
            print(f"portal-patch: anchor not found in {os.path.basename(path)}: {old.strip()[:50]!r}", file=sys.stderr)
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
    targets = [(os.path.join(D, "FilesView.qml"), FILES), (os.path.join(D, "shell.qml"), SHELL)]
    plans = []
    for path, repl in targets:
        p = plan(path, repl)
        if p is None:
            print("portal-patch: untouched - apps keep the GTK dialog", file=sys.stderr)
            return 2
        plans.append((path, p))
    changed = False
    for path, (out, pristine) in plans:   # FilesView first: shell.qml uses its new signal
        if pristine is not None:
            write(path + ".pristine", pristine)
        if out != open(path, encoding="utf-8").read():
            write(path, out)
            changed = True
    if changed:
        print(f"portal-patch: applied {VERSION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

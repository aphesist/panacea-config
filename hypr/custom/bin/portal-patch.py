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
VERSION = "v28"
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
    ('{page:"chat", title:root.tr("Чат"), icon:0xF0181}', '{page:"chat", title:"Claude", icon:0xF0181}, {page:"zentab", title:"Zen", icon:0xF059F}'),
    ("""IslandTabIcon { anchors.verticalCenter: parent.verticalCenter; width: 19; height: 19; kind: modelData.page === "main" ? "home" : "chat"; tint: root.page === modelData.page ? root.colFg : root.colMuted }""", """IslandTabIcon { anchors.verticalCenter: parent.verticalCenter; width: 19; height: 19; kind: modelData.page === "main" ? "home" : "chat"; tint: root.page === modelData.page ? root.colFg : root.colMuted
                                        visible: modelData.page === "chat" && tabClaudeLogo.status !== Image.Ready }
                        // """ + TAG + """: Home is the filled house, like the Zen-only bar's strip
                        Text { visible: modelData.page === "main"; anchors.verticalCenter: parent.verticalCenter
                               width: 19; horizontalAlignment: Text.AlignHCenter
                               text: String.fromCodePoint(0xF02DC); color: root.page === modelData.page ? root.colFg : root.colMuted
                               font { family: root.fontFam; pixelSize: 18 } }
                        // """ + TAG + """: the chat tab is Claude's (panacea-claude-bridge): its logo, white like the rest
                        Image { id: tabClaudeLogo; visible: modelData.page === "chat" && status === Image.Ready
                                anchors.verticalCenter: parent.verticalCenter; width: 17; height: 17
                                sourceSize: Qt.size(68, 68); fillMode: Image.PreserveAspectFit; smooth: true; mipmap: true
                                source: "file://" + Quickshell.env("HOME") + "/.config/panacea-claude/claude-logo.svg"
                                opacity: root.page === modelData.page ? 1 : 0.55 }
                        // """ + TAG + """: the Zen tab: Zen's circles, white
                        Image { visible: modelData.page === "zentab" && status === Image.Ready
                                anchors.verticalCenter: parent.verticalCenter; width: 17; height: 17
                                sourceSize: Qt.size(68, 68); fillMode: Image.PreserveAspectFit; smooth: true; mipmap: true
                                source: Qt.resolvedUrl("zen-logo.svg")
                                opacity: root.page === modelData.page ? 1 : 0.55 }"""),
    # tab switches ease instead of jumping: the active tab widens while its fill fades in,
    # the old one narrows and fades, the label fades (content stays put: the icon keeps
    # the same inset either way, so nothing slides under it)
    ("""                    width: root.page === modelData.page ? tabText.implicitWidth + 48 : 40
                    height: 34; radius: 17
                    color: root.page === modelData.page ? Qt.rgba(1,1,1,0.12) : "transparent"
                    Row {
                        anchors.centerIn: parent; spacing: 8""", """                    width: root.page === modelData.page ? tabText.implicitWidth + 48 : 40
                    height: 34; radius: 17; clip: true   // """ + TAG + """: animated tabs
                    color: root.page === modelData.page ? Qt.rgba(1,1,1,0.12) : Qt.rgba(1,1,1,0)
                    Behavior on width { enabled: !root.noMotion; NumberAnimation { duration: 280; easing.type: Easing.OutCubic } }
                    Behavior on color { ColorAnimation { duration: 240; easing.type: Easing.OutCubic } }
                    Row {
                        anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                        anchors.leftMargin: (40 - (children.length ? children[0].width : 19)) / 2 + (modelData.page === "main" ? 0 : 1)
                        spacing: 8"""),
    ("visible: root.page === modelData.page; text: modelData.title;",
     "opacity: root.page === modelData.page ? 1 : 0; Behavior on opacity { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }\n                               text: modelData.title;"),
    # the page itself slides in from the side of the tab you picked, fading in
    ("            onLoaded: if (item) item.forceActiveFocus()\n",
     """            onLoaded: { if (item) item.forceActiveFocus(); pageEnter(); }   """ + TAG + """: page slide
            readonly property var tabRank: ({ main: 0, chat: 1, zentab: 2, vpn: 3 })
            property string lastTabPage: ""
            onActiveChanged: if (!active) lastTabPage = ""
            transform: Translate { id: pageSlide }
            NumberAnimation { id: pageSlideAnim; target: pageSlide; property: "x"; to: 0; duration: 300; easing.type: Easing.OutCubic }
            NumberAnimation { id: pageFadeAnim; property: "opacity"; from: 0; to: 1; duration: 240; easing.type: Easing.OutCubic }
            function pageEnter() {
                var r = tabRank[root.page], q = tabRank[lastTabPage];
                if (item && r !== undefined && q !== undefined && r !== q && !root.noMotion) {
                    pageSlide.x = (r > q ? 1 : -1) * 24; pageSlideAnim.restart();
                    item.opacity = 0; pageFadeAnim.target = item; pageFadeAnim.restart();
                }
                lastTabPage = r !== undefined ? root.page : "";
            }
"""),
    # Mullvad: its own page (MullvadView.qml, from vpn-patch.py), no notification after
    # every toggle (the island shows the state), the country button opens the page
    # (right-click toggles), and the button shows the Mullvad exit country
    ('    property string vpnCountryName: ""\n',
     '    property string vpnCountryName: ""\n'
     '    readonly property bool vpnIsMullvad: /mullvad/i.test(cfg.vpnPreferredClient || "")   ' + TAG + ': Mullvad page\n'
     '    property bool zenNewTab: false   // the Zen search page opens a new tab\n'
     '    property bool vpnClassic: false   // "Change VPN client" shows Panacea\'s own page\n'
     '    Connections { target: root; function onPageChanged() { if (root.page !== "vpn") root.vpnClassic = false; } }\n'),
    ('            if (d.clientState) { root.vpnClientState = d.clientState; root.vpnConnected = d.clientState === "connected"; }\n            else if (!root.cfg.vpnPreferredClient)',
     '            if (d.clientState) { root.vpnClientState = d.clientState; root.vpnConnected = d.clientState === "connected"; }\n'
     '            if (d.countryCode) { root.vpnCountry = d.countryCode; root.vpnCountryName = d.country || ""; }\n'
     '            else if (root.vpnIsMullvad && d.clientState === "disconnected" && root.vpnCountry !== "--" && !vpnGeo.running && !vpnGeoDelay.running) vpnGeoDelay.restart();\n'
     '            if (d.clientState) {}\n            else if (!root.cfg.vpnPreferredClient)'),
    ('                root.announceVpnChange(d.action || root.vpnQuickAction);\n',
     '                if (root.vpnIsMullvad) root.refreshVpnStatus(); else root.announceVpnChange(d.action || root.vpnQuickAction);\n'),
    ('if (mouse.button === Qt.RightButton || (!root.cfg.vpnPreferred && !root.cfg.vpnPreferredClient)) { root.page = "vpn"; root.holdOpen = true; }\n                    else root.togglePreferredVpn();',
     'if (root.vpnIsMullvad ? mouse.button !== Qt.RightButton : (mouse.button === Qt.RightButton || (!root.cfg.vpnPreferred && !root.cfg.vpnPreferredClient))) { root.page = "vpn"; root.holdOpen = true; }\n                    else root.togglePreferredVpn();'),
    ('        Component { id: vpnComp; VpnView { sys: root } }\n',
     '        Component { id: vpnComp; Loader {\n'
     '            function goBack() { return !!(item && typeof item.goBack === "function" && item.goBack()); }\n'
     '            onLoaded: item.forceActiveFocus()\n'
     '            sourceComponent: root.vpnIsMullvad && !root.vpnClassic && Qt.resolvedUrl("MullvadView.qml") ? mullvadPage : classicVpnPage } }\n'
     '        Component { id: mullvadPage; MullvadView { sys: root } }\n'
     '        Component { id: classicVpnPage; VpnView { sys: root } }\n'),
    # the task manager (TasksView.qml): a large centred page like the explorer, opened by
    # `qs ipc call pill tasks` (Super+Shift+Esc)
    ('                     || page === "files" || page === "media")',
     '                     || page === "files" || page === "media" || page === "tasks")   ' + TAG + ': task manager'),
    ('        var want = page === "files" ? Math.round((screen ? screen.width : 1920) * 0.78)\n',
     '        var want = page === "tasks" ? Math.round((screen ? screen.width : 1920) * 0.66)   ' + TAG + '\n'
     '                 : page === "files" ? Math.round((screen ? screen.width : 1920) * 0.78)\n'),
    ('                           : root.page === "files"    ? filesComp\n',
     '                           : root.page === "tasks"    ? tasksComp   ' + TAG + '\n'
     '                           : root.page === "zen"      ? zenComp   ' + TAG + ': Zen search\n'
     '                           : root.page === "zentab"   ? zenTabComp   ' + TAG + ': the Zen tab\n'
     '                           : root.page === "files"    ? filesComp\n'),
    ('        Component { id: chatComp; ChatView { sys: root } }\n',
     '        Component { id: chatComp; ChatView { sys: root } }\n'
     '        Component { id: tasksComp; TasksView { sys: root } }   ' + TAG + '\n'
     '        Component { id: zenComp; ZenSearchView { sys: root } }   ' + TAG + ': Zen search\n'
     '        Component { id: zenTabComp; ZenTabView { sys: root } }   ' + TAG + ': the Zen tab\n'),
    ('        function files(): void { root.togglePage("files"); }\n',
     '        function files(): void { root.togglePage("files"); }\n'
     '        function tasks(): void { root.togglePage("tasks"); }   ' + TAG + ': task manager\n'
     '        // ' + TAG + ': Zen\'s address bar in the island (Panacea for Zen add-on): current tab / new tab\n'
     '        function zen(): void { root.zenNewTab = false; root.togglePage("zen"); }\n'
     '        function zenNew(): void { root.zenNewTab = true; root.togglePage("zen"); }\n'),
    # ---- the activity glow (IslandGlow.qml): settings, sources, the layer, the IPC calls
    ('            property int    animBounce: 79     // перелёт осциллятора, %\n',
     '            property int    animBounce: 79     // перелёт осциллятора, %\n'
     '            // ' + TAG + ': activity glow along the island edge\n'
     '            property bool   glowEnabled: true\n'
     '            property bool   glowClaude: true\n'
     '            property bool   glowVpn: true\n'
     '            property bool   glowAgents: true\n'
     '            property string glowStyle: "standard"\n'
     '            property int    glowLap: 1800\n'
     '            property int    glowIntensity: 70\n'),
    ('reduceMotion: false, animMove: 230, animFade: 200, animHover: 150, animBounce: 0,',
     'reduceMotion: false, animMove: 230, animFade: 200, animHover: 150, animBounce: 0,\n'
     '        glowEnabled: true, glowClaude: true, glowVpn: true, glowAgents: true, glowStyle: "standard", glowLap: 1800, glowIntensity: 70,'),
    ('    property string vpnQuickAction: ""\n',
     '    property string vpnQuickAction: ""\n'
     '    // ' + TAG + ': who lights the island edge right now. Sources, strongest first:\n'
     '    // agents that asked (glow IPC / panacea-glow), Claude while it works, the VPN while it connects.\n'
     '    property var glowExternal: ({})      // id -> { colors: [...], at: ms, until: ms }\n'
     '    property bool claudeWorking: false\n'
     '    readonly property var claudeGlowColors: ["#f4b28f", "#d97757", "#a8492a"]\n'
     '    FileView { id: glowClaudeFile; path: Quickshell.env("HOME") + "/.cache/panacea-claude/live.json"; printErrors: false\n'
     '        onLoaded: { try { root.claudeWorking = !!JSON.parse(text()).busy; } catch (e) {} } }\n'
     '    Timer { interval: 900; repeat: true; triggeredOnStart: true; running: root.cfg.glowEnabled && root.cfg.glowClaude\n'
     '            onTriggered: glowClaudeFile.reload(); onRunningChanged: if (!running) root.claudeWorking = false }\n'
     '    Timer { interval: 5000; repeat: true; running: Object.keys(root.glowExternal).length > 0\n'
     '            onTriggered: { var now = Date.now(), e = {}, changed = false;\n'
     '                           for (var k in root.glowExternal) { if (root.glowExternal[k].until > now) e[k] = root.glowExternal[k]; else changed = true; }\n'
     '                           if (changed) root.glowExternal = e; } }\n'
     '    readonly property var glowNow: {\n'
     '        if (!cfg.glowEnabled) return null;\n'
     '        if (cfg.glowAgents) {\n'
     '            var best = null;\n'
     '            for (var k in glowExternal) if (!best || glowExternal[k].at > best.at) best = glowExternal[k];\n'
     '            if (best) return best.colors;\n'
     '        }\n'
     '        if (cfg.glowClaude && claudeWorking) return claudeGlowColors;\n'
     '        if (cfg.glowVpn && vpnBusy) return ["#ffffff", "#e8e8e8", "#bdbdbd"];\n'
     '        return null;\n'
     '    }\n'
     '    property var glowLast: ["#ffffff"]   // keeps its colour while it fades out\n'
     '    onGlowNowChanged: if (glowNow) glowLast = glowNow\n'
     '    function glowStart(id, colors, ttl) {\n'
     '        var list = String(colors || "").split(/[ ,]+/).filter(function (c) { return /^#?[0-9a-fA-F]{6}$/.test(c); })\n'
     '                       .map(function (c) { return c.charAt(0) === "#" ? c : "#" + c; }).slice(0, 3);\n'
     '        if (!list.length) list = ["#ffffff"];\n'
     '        var e = Object.assign({}, glowExternal);\n'
     '        e[String(id || "agent")] = { colors: list, at: Date.now(), until: Date.now() + Math.max(5, ttl || 900) * 1000 };\n'
     '        glowExternal = e;\n'
     '    }\n'
     '    function glowStop(id) { var e = Object.assign({}, glowExternal); delete e[String(id)]; glowExternal = e; }\n'),
    # the glow sits on the island's outline (not inside it): beside the flare corners, above the island
    ('        opacity: root.cornersOn ? 1 : 0\n        Behavior on opacity { NumberAnimation { duration: root.animFast } }\n    }\n}\n',
     '        opacity: root.cornersOn ? 1 : 0\n        Behavior on opacity { NumberAnimation { duration: root.animFast } }\n    }\n\n'
     '    // ' + TAG + ': the activity glow, on the island\'s exact outline (flares included)\n'
     '    IslandGlow {\n'
     '        z: 1000; enabled: false\n'
     '        active: root.glowNow !== null && !root.wallsOpen && capsule.visible\n'
     '        colors: root.glowNow || root.glowLast\n'
     '        style: ({ loop: "standard", sweep: "standard", bounce: "pingpong" })[root.cfg.glowStyle] || root.cfg.glowStyle\n'
     '        lap: root.cfg.glowLap; intensity: root.cfg.glowIntensity / 100\n'
     '        still: root.noMotion\n'
     '        cx: capsule.x + root.dragDX; cy: capsule.y + root.dragDY; cw: capsule.width; ch: capsule.height\n'
     '        rTL: capsule.topLeftRadius; rTR: capsule.topRightRadius\n'
     '        rBL: capsule.bottomLeftRadius; rBR: capsule.bottomRightRadius\n'
     '        attached: root.pillAtTop && !root.pillSide && root.cornersOn && !root.settingsMode\n'
     '        flare: root.cornerR\n'
     '    }\n}\n'),
    ('                anchors.fill: parent; anchors.margins: -3; visible: root.vpnBusy\n',
     '                anchors.fill: parent; anchors.margins: -3; visible: root.vpnBusy && !(root.cfg.glowEnabled && root.cfg.glowVpn)   ' + TAG + ': the glow shows it\n'),
    ('        function files(): void { root.togglePage("files"); }\n',
     '        function files(): void { root.togglePage("files"); }\n'
     '        // ' + TAG + ': light the island edge for an agent: glow <id> "<#hex,#hex,#hex>", glowStop <id>\n'
     '        function glow(id: string, colors: string): void { root.glowStart(id, colors, 900); }\n'
     '        function glowStop(id: string): void { root.glowStop(id); }\n'
     '        function vpn(): void { root.togglePage("vpn"); }   // the VPN / Mullvad page\n'),
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


# ---- Claude tools (v13, v14: auto-start, v16: where its window opens): settings for the browser (Claudezilla) and "Ask Claude about this",
# two configurable shortcuts, and the IPC call the hotkey uses (scripts/custom/ask_claude.sh).
# The Settings > Claude page and the Keys rows come from claude-tools-patch.py.
SHELL += [
    ('            property string bind_pillVault: "SUPER + SHIFT + P"\n',
     '            property string bind_pillVault: "SUPER + SHIFT + P"\n'
     '            // ' + TAG + ': Claude tools (read by bridge.py, ask_claude.sh, hypr/custom/keybindings.lua)\n'
     '            property string bind_claudeChat: "SUPER + C"\n'
     '            property string bind_askClaude: "SUPER + SHIFT + C"\n'
     '            property bool   claudeBrowser: true\n'
     '            property string claudeBrowserAsk: "actions"   // actions | all | none\n'
     '            property bool   claudeBrowserAutostart: true   // start Claude\'s Zen (claude-zen-sandbox) when needed\n'
     '            property string claudeBrowserPlace: "desktop"  // desktop (workspace 10) | hidden | current\n'
     '            property string claudeBrowserMode: "space"     // space (a Space in your own Zen) | profile (claude-zen-sandbox)\n'
     '            property string askSource: "auto"             // auto | region | selection\n'
     '            property string askThen: "wait"               // wait | explain\n'),
    ('        pillVault:      "SUPER + SHIFT + P",\n',
     '        pillVault:      "SUPER + SHIFT + P",\n'
     '        claudeChat:     "SUPER + C",            ' + TAG + '\n'
     '        askClaude:      "SUPER + SHIFT + C",\n'),
    ('        clock12: false, clockSeconds: false, clockWeekday: true,\n',
     '        claudeBrowser: true, claudeBrowserAsk: "actions", claudeBrowserAutostart: true, claudeBrowserPlace: "desktop", claudeBrowserMode: "space", askSource: "auto", askThen: "wait",   ' + TAG + '\n'
     '        clock12: false, clockSeconds: false, clockWeekday: true,\n'),
    ('    property string chatDraft: ""          // ...and its unsent text\n',
     '    property string chatDraft: ""          // ...and its unsent text\n'
     '    property bool chatAskSend: false       // "Ask Claude about this": send it right away\n'
     '    property int chatAskRev: 0             // bumped per request, so an open chat takes it too\n'),
    ('        function chat(): void { root.page = "chat"; root.expanded = true; root.holdOpen = true; }\n',
     '        function chat(): void { root.page = "chat"; root.expanded = true; root.holdOpen = true; }\n'
     '        // ' + TAG + ': "Ask Claude about this": {"files": [...], "draft": "...", "send": bool}\n'
     '        function askAbout(spec: string): void {\n'
     '            var s; try { s = JSON.parse(spec); } catch (e) { return; }\n'
     '            if (root.islandPick) root.endIslandPick(false, [], true);\n'
     '            root.pendingChatAttach = (root.pendingChatAttach || []).concat(s.files || []);\n'
     '            if (s.draft) root.chatDraft = String(s.draft);\n'
     '            root.chatAskSend = !!s.send;\n'
     '            root.chatAskRev++;\n'
     '            root.page = "chat"; root.expanded = true; root.holdOpen = true;\n'
     '        }\n'),
]


# ---- Zen-only mode (v19): Zen alone on the island's screen (floating windows aside) turns
# the collapsed island into Zen's address bar (ZenBar.qml), opening the search in place, and
# tells Zen to hide its dock ($XDG_RUNTIME_DIR/panacea-zen-solo, read by panacea-dock.uc.js,
# which also sends Zen's address-bar keys here: `ipc call pill zenBar` / `zenBarNew`).
SHELL += [
    ('(root.page === "main" || root.page === "chat" || root.page === "vpn")',
     '(root.page === "main" || root.page === "chat" || root.page === "zentab" || root.page === "vpn")', "all"),
    ('    property bool zenNewTab: false   // the Zen search page opens a new tab\n',
     '    property bool zenNewTab: false   // the Zen search page opens a new tab\n'
     '    // ' + TAG + r''': Zen-only mode
    property bool zenSolo: false
    readonly property int zenBarW: Math.round(Math.min((screen ? screen.width : 1920) * 0.4, 720) / 2) * 2
    readonly property bool zenBarShown: zenSolo && !expanded && !settingsMode && !pillSide && !pillHidden && !wallsOpen
        && !toastActive && !osdActive && !btToastActive && !wifiToastActive && !acToastActive
        && !recPickActive && !voxActive && !fileOverIsland
    property var zenTab: ({})              // Zen's active tab {url, title, host} (panacea-dock.uc.js)
    function zenOpenIsland(pg) { pageResetTimer.stop(); page = pg || "main"; expanded = true; holdOpen = pg === "chat"; }
    function zenOpenSearch(nt) { zenNewTab = !!nt; pageResetTimer.stop(); page = "zen"; expanded = true; holdOpen = true; }
    Process {
        id: zenSoloProc
        property bool again: false
        command: ["sh", "-c", "hyprctl -j clients; echo; echo @@; hyprctl -j monitors"]
        stdout: StdioCollector { onStreamFinished: root.zenSoloParse(text) }
        onExited: if (again) { again = false; running = true; }
    }
    function zenSoloCheck() { if (zenSoloProc.running) zenSoloProc.again = true; else zenSoloProc.running = true; }
    function zenSoloParse(text) {
        var parts = text.split("\n@@\n"), cl, mons;
        try { cl = JSON.parse(parts[0]); mons = JSON.parse(parts[1]); } catch (e) { return; }
        var name = root.screen ? root.screen.name : "", mon = null, i;
        for (i = 0; i < mons.length; i++) if (mons[i].name === name) mon = mons[i];
        for (i = 0; !mon && i < mons.length; i++) if (mons[i].focused) mon = mons[i];
        var solo = false, running = false;
        for (i = 0; i < cl.length; i++) if (cl[i]["class"] === "zen") running = true;
        root.zenRunning = running;
        if (root.zenMode === "island") {
            // island mode (Zen pref panacea.zen.urlbar = "island"): the bar shows whenever Zen
            // is the focused window on this screen, tiled or floating, alone or not
            for (i = 0; mon && i < cl.length; i++) {
                var f = cl[i];
                if (f["class"] === "zen" && f.focusHistoryID === 0 && f.mapped && !f.hidden && f.monitor === mon.id) solo = true;
            }
        } else if (mon && mon.activeWorkspace && !(mon.specialWorkspace && mon.specialWorkspace.id)) {
            var n = 0, zen = false;
            for (i = 0; i < cl.length; i++) {
                var c = cl[i];
                if (!c.mapped || c.hidden || c.floating || !c.workspace || c.workspace.id !== mon.activeWorkspace.id) continue;
                n++; zen = c["class"] === "zen";
            }
            solo = n === 1 && zen;
        }
        if (solo && !root.zenSolo) { zenTabFile.reload(); zenIconsFile.reload(); }
        root.zenSolo = solo;
    }
    Timer { id: zenSoloDebounce; interval: 40; onTriggered: root.zenSoloCheck() }
    Connections {
        target: Hyprland
        function onRawEvent(ev) {
            if (/^(openwindow|closewindow|movewindow|changefloatingmode|workspace|focusedmon|activespecial|moveworkspace|minimized)/.test(ev.name)
                || (root.zenMode === "island" && /^activewindow$/.test(ev.name)))
                zenSoloDebounce.restart();
        }
    }
    // Zen hides its dock while this says 1; the pid (this shell) lets it ignore a stale file
    Process {
        id: zenSoloWriter
        property bool again: false
        onExited: if (again) { again = false; root.zenSoloWrite(); }
    }
    function zenSoloWrite() {   // the command is set here: a binding would still hold the old value
        if (zenSoloWriter.running) { zenSoloWriter.again = true; return; }
        zenSoloWriter.command = ["sh", "-c", 'printf "%s %s\\n" "$1" "$PPID" > "$XDG_RUNTIME_DIR/panacea-zen-solo"', "_", root.zenSolo ? "1" : "0"];
        zenSoloWriter.running = true;
    }
    onZenSoloChanged: zenSoloWrite()
    // Zen's address-bar mode, from panacea-dock.uc.js: "dock" (the island is the bar only
    // while Zen is alone) or "island" (the island is the bar whenever Zen has focus)
    property string zenMode: "dock"
    onZenModeChanged: zenSoloCheck()
    FileView {
        id: zenModeFile
        path: Quickshell.env("XDG_RUNTIME_DIR") + "/panacea-zen-mode"
        watchChanges: true
        printErrors: false
        onFileChanged: reload()
        onLoaded: root.zenMode = String(text() || "").trim() === "island" ? "island" : "dock"
    }
    Timer { interval: 400; running: true; onTriggered: { root.zenSoloWrite(); root.zenSoloCheck(); } }
    FileView {
        id: zenTabFile
        path: Quickshell.env("XDG_RUNTIME_DIR") + "/panacea-zen-tab.json"
        watchChanges: true
        printErrors: false
        onFileChanged: reload()
        onLoaded: { try { root.zenTab = JSON.parse(text()) || ({}); } catch (e) {} }
    }
    // the Zen tab (ZenTabView.qml): pinned and recent tabs, and commands back to Zen
    property bool zenRunning: false
    property var zenTabs: ({})
    FileView {
        id: zenTabsFile
        path: Quickshell.env("XDG_RUNTIME_DIR") + "/panacea-zen-tabs.json"
        watchChanges: true
        printErrors: false
        onFileChanged: reload()
        onLoaded: { try { root.zenTabs = JSON.parse(text()) || ({}); } catch (e) {} }
    }
    Connections { target: root; function onPageChanged() { if (root.page === "zentab") zenTabsFile.reload(); } }
    readonly property string zenFocusCmd: "hyprctl dispatch 'hl.dsp.focus({ window = \"class:^(zen)$\" })' >/dev/null 2>&1"
    function zenCmd(cmd, arg) {   // panacea-dock.uc.js picks it up; a switch brings Zen forward
        Quickshell.execDetached(["sh", "-c", 'printf "%s\\n" "$1" > "$XDG_RUNTIME_DIR/panacea-zen-cmd"' + (cmd === "select" ? "; " + zenFocusCmd : ""),
                                 "_", arg ? cmd + " " + arg : cmd]);
        if (cmd === "select") collapse();
    }
    function zenLaunch(args) { Quickshell.execDetached(["zen-browser"].concat(args || [])); collapse(); }
    function zenOpenApp() {
        if (zenRunning) Quickshell.execDetached(["sh", "-c", zenFocusCmd]); else Quickshell.execDetached(["zen-browser"]);
        collapse();
    }
    property var zenIcons: ({})            // site icons {host: file} (panacea-dock.uc.js)
    FileView {
        id: zenIconsFile
        path: Quickshell.env("XDG_RUNTIME_DIR") + "/panacea-zen-icons/index.json"
        watchChanges: true
        printErrors: false
        onFileChanged: reload()
        onLoaded: { try { root.zenIcons = JSON.parse(text()) || ({}); } catch (e) {} }
    }
'''),
    # the bar replaces the clock row, the mascot and the hover-to-open
    ('                : root.pillSide  ? capsule.evenUp(Math.max(vertCapsule.implicitHeight + 30,\n',
     '                : root.zenBarShown ? capsule.evenUp(zenBarItem.implicitWidth)   ' + TAG + ': Zen-only mode\n'
     '                : root.pillSide  ? capsule.evenUp(Math.max(vertCapsule.implicitHeight + 30,\n'),
    ('                ? toastCapsule.implicitHeight + 24 : root.pillH\n',
     '                ? toastCapsule.implicitHeight + 24 : root.zenBarShown ? zenBarItem.implicitHeight : root.pillH   ' + TAG + '\n'),
    # the search opened from the bar keeps the bar's width
    ('             : (root.expanded && !root.cfg.pillKeepVisible) ? root.panelW\n',
     '             : (root.expanded && !root.cfg.pillKeepVisible) ? (root.zenSolo && root.page === "zen" ? root.zenBarW : root.panelW)   ' + TAG + '\n'),
    ('            width: (root.settingsMode ? root.settingsW : root.panelW) - 30\n',
     '            width: (root.settingsMode ? root.settingsW : root.zenSolo && root.page === "zen" ? root.zenBarW : root.panelW) - 30   ' + TAG + '\n'),
    ('                     && !root.osdActive && !root.toastActive\n            opacity: root.pillSide ? 0 : (visible ? 1 : 0)\n',
     '                     && !root.osdActive && !root.toastActive && !root.zenBarShown   ' + TAG + '\n            opacity: root.pillSide ? 0 : (visible ? 1 : 0)\n'),
    ('        Mascot { id: mascot; sys: root; anchors.centerIn: parent; z: 10; visible: active && !root.pillSide }\n',
     '        Mascot { id: mascot; sys: root; anchors.centerIn: parent; z: 10; visible: active && !root.pillSide && !root.zenBarShown }   ' + TAG + '\n'),
    ('if (root.toastActive || root.btToastActive || root.wifiToastActive || root.acToastActive || root.recPickActive || root.voxActive) return;',
     'if (root.toastActive || root.btToastActive || root.wifiToastActive || root.acToastActive || root.recPickActive || root.voxActive || root.zenBarShown) return;   ' + TAG),
    ('                     && !root.osdActive && !root.btToastActive && !root.wifiToastActive && !root.acToastActive && !root.recPickActive && !root.voxActive\n            cursorShape: Qt.PointingHandCursor\n            onClicked: capsule.openPanel()\n',
     '                     && !root.osdActive && !root.btToastActive && !root.wifiToastActive && !root.acToastActive && !root.recPickActive && !root.voxActive\n'
     '                     && !root.zenBarShown   ' + TAG + '\n'
     '            cursorShape: Qt.PointingHandCursor\n            onClicked: capsule.openPanel()\n'),
    ('        // ---- свёрнутое: голосовой ввод',
     '        // ' + TAG + ': Zen-only mode, the address bar\n'
     '        ZenBar {\n'
     '            id: zenBarItem\n'
     '            // pinned to the top at its own size: when the island opens or closes around it, it\n'
     '            // fades in place instead of riding the growing panel down\n'
     '            anchors.top: parent.top\n'
     '            anchors.horizontalCenter: parent.horizontalCenter\n'
     '            width: implicitWidth\n'
     '            height: implicitHeight\n'
     '            z: 120\n'
     '            sys: root\n'
     '            visible: opacity > 0.01\n'
     '            opacity: root.zenBarShown ? 1 : 0\n'
     '            // out at once (the page takes over), back only once the island has shrunk to it\n'
     '            Behavior on opacity { SequentialAnimation {\n'
     '                PauseAnimation { duration: root.zenBarShown ? Math.round(root.animMs * 0.55) : 0 }\n'
     '                NumberAnimation { duration: root.zenBarShown ? root.animFast : Math.min(90, root.animFast) }\n'
     '            } }\n'
     '        }\n\n'
     '        // ' + TAG + ': a sideways touchpad swipe on the open island changes tab (one per swipe;\n'
     '        // fingers left = the next tab, like a carousel following them). Only sideways scrolls\n'
     '        // are taken; everything else (clicks, vertical scrolling) passes through.\n'
     '        MouseArea {\n'
     '            id: tabSwipe\n'
     '            parent: (root.cfg.pillKeepVisible && root.expanded && !root.settingsMode) ? detachedPanel : capsule\n'
     '            anchors.fill: parent\n'
     '            z: 498\n'
     '            acceptedButtons: Qt.NoButton\n'
     '            readonly property var order: ["main", "chat", "zentab", "vpn"]\n'
     '            enabled: root.expanded && !root.settingsMode && order.indexOf(root.page) >= 0\n'
     '            property real acc: 0\n'
     '            property bool spent: false\n'
     '            Timer { id: swipeQuiet; interval: 260; onTriggered: { tabSwipe.acc = 0; tabSwipe.spent = false; } }\n'
     '            onWheel: wheel => {\n'
     '                var dx = wheel.pixelDelta.x !== 0 ? wheel.pixelDelta.x : wheel.angleDelta.x / 4;\n'
     '                var dy = wheel.pixelDelta.y !== 0 ? wheel.pixelDelta.y : wheel.angleDelta.y / 4;\n'
     '                if (Math.abs(dx) <= Math.abs(dy) && !spent && Math.abs(acc) < 4) { wheel.accepted = false; return; }\n'
     '                swipeQuiet.restart();\n'
     '                if (spent) return;\n'
     '                acc += dx;\n'
     '                if (Math.abs(acc) < 70) return;\n'
     '                var i = order.indexOf(root.page) + (acc < 0 ? 1 : -1);\n'
     '                spent = true;\n'
     '                if (i < 0 || i >= order.length || !root.pageEnabled(order[i])) return;\n'
     '                root.page = order[i];\n'
     '                root.holdOpen = order[i] === "chat" || order[i] === "vpn";\n'
     '            }\n'
     '        }\n\n'
     '        // ---- свёрнутое: голосовой ввод'),
    # Zen's address-bar keys (Ctrl+L, Ctrl+K, Ctrl+T...) while its dock is hidden
    ('        function zenNew(): void { root.zenNewTab = true; root.togglePage("zen"); }\n',
     '        function zenNew(): void { root.zenNewTab = true; root.togglePage("zen"); }\n'
     '        function zenBar(): void { root.zenOpenSearch(false); }      ' + TAG + ': Zen-only mode\n'
     '        function zenBarNew(): void { root.zenOpenSearch(true); }\n'),
]

FILES = [
    ("    signal filePicked(string path)\n",
     "    signal filePicked(string path)\n"
     "    signal pickCancelled()   " + TAG + "\n"),
    ("        if (view.pickerMode) view.sys.chatFilePickerOpen = false;\n",
     "        if (view.pickerMode) { view.sys.chatFilePickerOpen = false; view.pickCancelled(); }   " + TAG + "\n"),
]


MOTION = [
    ("""    SetCard {
        sys: page.sys

        SetToggle {
            sys: page.sys
            label: page.sys.tr("Уменьшить анимацию")""", """    // """ + TAG + """: the activity glow along the island's edge (IslandGlow.qml)
    SetCard {
        sys: page.sys

        SetToggle {
            sys: page.sys
            label: "Activity glow"
            sub: "A light runs along the island's edge while something works, even when the island is closed."
            on: page.sys.cfg.glowEnabled
            onToggled: value => { page.sys.cfg.glowEnabled = value; page.sys.saveCfg(); }
        }
        SetToggle {
            sys: page.sys
            visible: page.sys.cfg.glowEnabled
            label: "Claude"
            sub: "Orange while Claude works in the island."
            on: page.sys.cfg.glowClaude
            onToggled: value => { page.sys.cfg.glowClaude = value; page.sys.saveCfg(); }
        }
        SetToggle {
            sys: page.sys
            visible: page.sys.cfg.glowEnabled
            label: "VPN"
            sub: "White while the VPN connects or disconnects, instead of the spinner."
            on: page.sys.cfg.glowVpn
            onToggled: value => { page.sys.cfg.glowVpn = value; page.sys.saveCfg(); }
        }
        SetToggle {
            sys: page.sys
            visible: page.sys.cfg.glowEnabled
            label: "Apps and agents"
            sub: "In their own colours, for anything that asks (panacea-glow)."
            on: page.sys.cfg.glowAgents
            onToggled: value => { page.sys.cfg.glowAgents = value; page.sys.saveCfg(); }
        }
        SetPick {
            sys: page.sys
            visible: page.sys.cfg.glowEnabled
            label: "Animation"
            visibleRows: 6
            value: ({ loop: "standard", sweep: "standard", bounce: "pingpong" })[page.sys.cfg.glowStyle] || page.sys.cfg.glowStyle
            options: [
                { id: "standard",  text: "Standard: one stroke, end to end" },
                { id: "pingpong",  text: "Ping-pong: there and back" },
                { id: "symmetric", text: "Symmetric: from the bottom, up both sides" },
                { id: "converge",  text: "Converge: from both ends to the bottom" },
                { id: "breathing", text: "Breathing: the whole outline" },
                { id: "wave",      text: "Wave: a soft band flowing round" }
            ]
            onPicked: id => { page.sys.cfg.glowStyle = id; page.sys.saveCfg(); }
        }
        SetSlider {
            sys: page.sys
            visible: page.sys.cfg.glowEnabled
            label: "Speed (one lap)"
            from: 700; to: 4000; step: 100
            value: page.sys.cfg.glowLap
            suffix: "ms"
            onMoved: v => { page.sys.cfg.glowLap = v; page.sys.saveCfg(); }
        }
        SetSlider {
            sys: page.sys
            visible: page.sys.cfg.glowEnabled
            label: "Intensity"
            from: 20; to: 100; step: 5
            value: page.sys.cfg.glowIntensity
            suffix: "%"
            onMoved: v => { page.sys.cfg.glowIntensity = v; page.sys.saveCfg(); }
        }
    }

    SetCard {
        sys: page.sys

        SetToggle {
            sys: page.sys
            label: page.sys.tr("Уменьшить анимацию")"""),
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
    for old, new, *mode in repl:
        if mode == ["all"] and out.count(old) >= 1:
            out = out.replace(old, new)
            continue
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
    targets = [(os.path.join(D, "FilesView.qml"), FILES), (os.path.join(D, "SetMotion.qml"), MOTION), (os.path.join(D, "shell.qml"), SHELL)]
    plans = []
    for path, repl in targets:
        p = plan(path, repl)
        if p is None:
            print("portal-patch: untouched - apps keep the GTK dialog", file=sys.stderr)
            return 2
        plans.append((path, p))
    changed = False
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ("TasksView.qml", "TasksChart.qml", "IslandGlow.qml", "ZenSearchView.qml", "ZenBar.qml", "ZenTabView.qml", "zen-logo.svg"):   # written first: shell.qml uses them
        src = os.path.join(here, name)
        if os.path.exists(src):
            body = open(src, encoding="utf-8").read()
            dst = os.path.join(D, name)
            if not os.path.exists(dst) or open(dst, encoding="utf-8").read() != body:
                write(dst, body)
                changed = True
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

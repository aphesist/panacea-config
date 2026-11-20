pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import Quickshell
import Quickshell.Io

// written by portal-patch.py (panacea-config) - Zen's address bar, in the island.
// Talks to Zen through the "Panacea for Zen" add-on (panacea-zen CLI -> native host
// socket): your tabs, bookmarks, history and search suggestions as you type; Enter opens
// in the current tab, Alt/Ctrl+Enter (or middle click) in a new one, a tab row switches to
// that tab. Plain code, no AI. Opened by `qs ipc call pill zen` / `zenNew`.
FocusScope {
    id: view
    property var sys
    implicitHeight: col.implicitHeight
    focus: true

    readonly property real islandR: sys.cfg.islandRadius > 0 ? sys.cfg.islandRadius : 26
    readonly property real boxR: Math.max(14, islandR - 6)
    readonly property real rInner: Math.max(8, boxR - 6)
    readonly property string cli: Quickshell.env("HOME") + "/.local/bin/panacea-zen"
    readonly property string focusZen: "hyprctl dispatch 'hl.dsp.focus({ window = \"class:^(zen)$\" })' >/dev/null 2>&1"
    readonly property int maxRows: 8

    property bool newTab: !!sys.zenNewTab
    property string query: ""
    property string asked: ""          // the query the shown results belong to
    property var items: []
    property int index: 0
    property bool connected: true
    property string currentUrl: ""
    property bool edited: false        // the field still shows the current address, untouched
    property bool picked: false        // a row was chosen with the arrows or the mouse

    function goBack() { return false; }

    // ---------------------------------------------------------------- talking to Zen
    Process {
        id: pCurrent
        command: [view.cli, "current"]
        running: !view.newTab
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    var d = JSON.parse(text);
                    if (d.error) { view.connected = false; return; }
                    view.currentUrl = d.url || "";
                    if (!view.edited && view.currentUrl && !/^about:/.test(view.currentUrl)) {
                        input.text = view.currentUrl;
                        input.selectAll();
                        view.edited = false;
                    }
                } catch (e) {}
            }
        }
    }
    Process {
        id: pSuggest
        property string q: ""
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    var d = JSON.parse(text);
                    if (d.error) { view.connected = false; view.items = []; }
                    else { view.connected = true; view.items = d.items || []; view.asked = pSuggest.q; }
                } catch (e) {}
                if (pSuggest.q !== view.suggestText()) suggestTimer.restart();   // typed meanwhile
            }
        }
    }
    function suggestText() { return view.edited ? view.query.trim() : ""; }
    Timer {
        id: suggestTimer
        interval: 70
        onTriggered: {
            if (pSuggest.running) return;   // its finish handler re-asks
            pSuggest.q = view.suggestText();
            pSuggest.command = [view.cli, "suggest", pSuggest.q];
            pSuggest.running = true;
        }
    }
    Component.onCompleted: suggestTimer.start()

    onQueryChanged: { index = 0; picked = false; suggestTimer.restart(); }
    onItemsChanged: if (rows && index >= rows.length) index = Math.max(0, rows.length - 1)

    // what the list shows: the add-on's rows, or a single "open Zen" row when it isn't there
    readonly property var rows: {
        if (!connected) {
            var t = query.trim();
            return [{ type: "launch", title: t ? "Open in Zen: " + t : "Open Zen", text: t }];
        }
        return items;
    }

    // ---------------------------------------------------------------- actions
    function run(cmd) {
        Quickshell.execDetached(["sh", "-c", cmd + " >/dev/null 2>&1; " + view.focusZen]);
    }
    function launch(forceNew) {
        var it = rows[index];
        var nt = view.newTab || !!forceNew;
        var typed = query.trim();
        if (!it && !typed) return;
        if (!it || (!view.edited && !view.picked && typed)) it = { type: "url", url: typed };   // Enter on the untouched address: reload it
        var q = function (s) { return "'" + String(s).replace(/'/g, "'\\''") + "'"; };
        if (it.type === "launch") {
            Quickshell.execDetached(["sh", "-c", "zen-browser \"$@\" >/dev/null 2>&1 &", "_"].concat(it.text ? [it.text] : []));
        } else if (it.type === "tab") {
            run(view.cli + " switch " + Number(it.tabId));
        } else {
            var target = it.url || it.text || typed;
            run(view.cli + " open " + q(target) + (nt ? " --new" : ""));
        }
        sys.collapse();
    }
    function move(d) {
        if (!rows.length) return;
        view.picked = true;
        index = Math.max(0, Math.min(rows.length - 1, index + d));
        list.positionViewAtIndex(index, ListView.Contain);
    }

    function glyphFor(t) {
        switch (t) {
        case "tab":        return String.fromCodePoint(0xF04E9);   // md-tab
        case "bookmark":   return String.fromCodePoint(0xF04CE);   // md-star
        case "history":    return String.fromCodePoint(0xF02DA);   // md-history
        case "url":        return String.fromCodePoint(0xF059F);   // md-web
        case "launch":     return String.fromCodePoint(0xF059F);
        }
        return String.fromCodePoint(0xF0349);                      // md-magnify
    }
    function iconFor(it) {
        if (!it.url || !/^https?:/.test(it.url)) return "";
        var h = it.host || "";
        if (!h) { var m = String(it.url).match(/^https?:\/\/([^\/:?#]+)/); h = m ? m[1] : ""; }
        var f = (view.sys.zenIcons || {})[h];
        return f ? "file://" + f : "";
    }
    function titleFor(it) {
        if (it.type === "search") return it.text;
        if (it.type === "suggestion") return it.text;
        return it.title || it.url || "";
    }
    function subFor(it) {
        switch (it.type) {
        case "search":     return "Search" + (it.engine ? " with " + it.engine : "");
        case "suggestion": return it.engine ? it.engine + " suggestion" : "Suggestion";
        case "tab":        return "Switch to tab · " + (it.host || "");
        case "bookmark":   return "Bookmark · " + (it.host || it.url || "");
        case "history":    return it.host || it.url || "";
        case "url":        return "Go to " + (it.host || it.url || "");
        case "launch":     return "Zen isn't running";
        }
        return "";
    }

    FocusGrabber { target: input }

    ColumnLayout {
        id: col
        width: parent.width
        spacing: 8

        // ------------------------------------------------------------ the field
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 42
            radius: view.rInner + 4
            color: input.activeFocus ? Qt.rgba(1, 1, 1, 0.075) : Qt.rgba(1, 1, 1, 0.055)
            Behavior on color { ColorAnimation { duration: 150 } }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 14
                anchors.rightMargin: 12
                spacing: 10

                Text {
                    text: String.fromCodePoint(0xF059F)
                    color: view.sys.colMuted
                    font { family: view.sys.fontFam; pixelSize: 15 }
                }
                TextField {
                    id: input
                    focus: true
                    Layout.fillWidth: true
                    placeholderText: view.newTab ? "New tab: search or address" : "Search or address"
                    color: view.sys.colFg
                    placeholderTextColor: view.sys.colMuted
                    selectionColor: Qt.rgba(1, 1, 1, 0.25)
                    selectedTextColor: view.sys.colFg
                    font { family: view.sys.fontFam; pixelSize: 13 }
                    background: null
                    onTextEdited: { view.edited = true; view.query = text; }
                    onTextChanged: if (!view.edited) view.query = text

                    Keys.onDownPressed: view.move(1)
                    Keys.onUpPressed: view.move(-1)
                    Keys.onTabPressed: view.move(1)
                    Keys.onBacktabPressed: view.move(-1)
                    Keys.onEscapePressed: view.sys.collapse()
                    Keys.onPressed: event => {
                        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                            view.launch(event.modifiers & (Qt.AltModifier | Qt.ControlModifier));
                            event.accepted = true;
                        }
                    }
                }
                Rectangle {
                    // new-tab marker; click toggles
                    Layout.preferredHeight: 22
                    Layout.preferredWidth: ntText.implicitWidth + 16
                    radius: 11
                    color: view.newTab ? Qt.rgba(1, 1, 1, 0.14) : (ntMa.containsMouse ? Qt.rgba(1, 1, 1, 0.08) : "transparent")
                    Behavior on color { ColorAnimation { duration: 150 } }
                    Text {
                        id: ntText
                        anchors.centerIn: parent
                        text: "new tab"
                        color: view.newTab ? view.sys.colFg : view.sys.colMuted
                        font { family: view.sys.fontFam; pixelSize: 10 }
                    }
                    MouseArea {
                        id: ntMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: { view.newTab = !view.newTab; input.forceActiveFocus(); }
                    }
                }
            }
        }

        // ------------------------------------------------------------ results
        ListView {
            id: list
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(view.rows.length, view.maxRows) * 46
            visible: view.rows.length > 0
            clip: true
            model: view.rows
            currentIndex: view.index
            boundsBehavior: Flickable.StopAtBounds
            spacing: 2

            delegate: Rectangle {
                id: row
                required property var modelData
                required property int index
                width: list.width
                height: 44
                radius: view.rInner + 4
                color: index === view.index ? Qt.rgba(1, 1, 1, 0.10)
                     : (rowMa.containsMouse ? Qt.rgba(1, 1, 1, 0.05) : "transparent")
                Behavior on color { ColorAnimation { duration: 120 } }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 12
                    spacing: 12

                    Item {
                        Layout.preferredWidth: 18
                        Layout.preferredHeight: 18
                        // the site's icon (panacea-dock.uc.js caches them), else a glyph
                        Image {
                            id: fav
                            anchors.centerIn: parent
                            width: 16; height: 16
                            sourceSize: Qt.size(32, 32)
                            smooth: true
                            source: view.iconFor(row.modelData)
                            visible: status === Image.Ready
                        }
                        Text {
                            anchors.centerIn: parent
                            visible: !fav.visible
                            text: view.glyphFor(row.modelData.type)
                            color: row.modelData.type === "tab" ? view.sys.colFg : view.sys.colMuted
                            font { family: view.sys.fontFam; pixelSize: 15 }
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Text {
                            Layout.fillWidth: true
                            text: view.titleFor(row.modelData)
                            color: view.sys.colFg
                            elide: Text.ElideRight
                            textFormat: Text.PlainText
                            font { family: view.sys.fontFam; pixelSize: 13; bold: row.index === view.index }
                        }
                        Text {
                            Layout.fillWidth: true
                            visible: text.length > 0
                            text: view.subFor(row.modelData)
                            color: view.sys.colMuted
                            elide: Text.ElideRight
                            textFormat: Text.PlainText
                            font { family: view.sys.fontFam; pixelSize: 10 }
                        }
                    }
                    Text {
                        visible: row.index === view.index
                        text: "󰌑"
                        color: view.sys.colMuted
                        font { family: view.sys.fontFam; pixelSize: 12 }
                    }
                }

                MouseArea {
                    id: rowMa
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.LeftButton | Qt.MiddleButton
                    cursorShape: Qt.PointingHandCursor
                    onEntered: { view.index = row.index; view.picked = true; }
                    onClicked: mouse => view.launch(mouse.button === Qt.MiddleButton)
                }
            }
        }
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Shapes
import Quickshell.Io

// written by vpn-patch.py (panacea-config) - the island's Mullvad page.
// Status and one power button at the top, then Servers (search, recents, every
// country and city) or Settings (connection options and DNS blockers). Talks to the
// Mullvad daemon through scripts/custom/mullvad_control.py. Same radius system and
// palette as the Claude chat: surfaces boxR, controls rInner, no outlines.
FocusScope {
    id: view
    required property var sys
    implicitHeight: 560

    readonly property real islandR: sys.cfg.islandRadius > 0 ? sys.cfg.islandRadius : 26
    readonly property real boxR: Math.max(14, islandR - 6)
    readonly property real rInner: Math.max(8, boxR - 6)
    readonly property string ctl: sys.scriptDir + "/custom/mullvad_control.py"

    property var st: ({})
    property var countries: []
    property string tab: "servers"
    property string query: ""
    property string openCountry: ""
    property string pending: ""
    property string error: ""
    property real lastActEnd: 0
    property real pollStart: 0

    readonly property string vstate: st.clientState || "unknown"
    readonly property bool isOn: vstate === "connected"
    readonly property bool isBusy: vstate === "busy" || pending === "power"
    readonly property var sel: st.selected || ({})

    function goBack() {
        if (query) { query = ""; search.text = ""; return true; }
        if (tab !== "servers") { tab = "servers"; return true; }
        return false;
    }
    function run(tag, args) {
        if (act.running) return;
        view.pending = tag; view.error = "";
        act.command = ["python3", "-I", view.ctl].concat(args);
        act.running = true;
    }
    function poll() { if (!stateProc.running) stateProc.running = true; }
    // a switch flips at once; the next real state (taken after the change) confirms it
    function flip(key, isDns) {
        var cur = isDns ? !!(st.dns || {})[key] : !!st[key];
        var next = Object.assign({}, st);
        if (isDns) { next.dns = Object.assign({}, st.dns || {}); next.dns[key] = !cur; } else next[key] = !cur;
        view.st = next;
        run("set:" + key, ["set", key, cur ? "off" : "on"]);
    }
    function pick(cc, city) { run("loc:" + cc + "/" + city, city ? ["location", cc, city] : ["location", cc]); }
    function countryName(cc) {
        for (var i = 0; i < countries.length; i++) if (countries[i].code === cc) return countries[i].name;
        return String(cc || "").toUpperCase();
    }
    function cityName(cc, city) {
        for (var i = 0; i < countries.length; i++) if (countries[i].code === cc)
            for (var j = 0; j < countries[i].cities.length; j++) if (countries[i].cities[j].code === city) return countries[i].cities[j].name;
        return "";
    }
    readonly property string selectedLabel: sel.host ? sel.host
        : sel.cc ? ((sel.city && cityName(sel.cc, sel.city) ? cityName(sel.cc, sel.city) + ", " : "") + countryName(sel.cc)) : "Fastest server"
    readonly property var filtered: {
        var q = query.trim().toLowerCase(), out = [];
        if (!q) return countries;
        for (var i = 0; i < countries.length; i++) {
            var c = countries[i];
            var whole = c.name.toLowerCase().indexOf(q) >= 0 || c.code === q;
            var cities = c.cities.filter(function (x) { return x.name.toLowerCase().indexOf(q) >= 0; });
            if (whole || cities.length) out.push({ code: c.code, name: c.name, cities: whole ? c.cities : cities, byCity: !whole });
        }
        return out;
    }

    Process {
        id: stateProc
        command: ["python3", "-I", view.ctl, "state"]
        onStarted: view.pollStart = Date.now()
        stdout: StdioCollector { onStreamFinished: {
            if (act.running || view.pollStart < view.lastActEnd) return;   // older than a change you just made
            try { var d = JSON.parse(text); if (d.ok === false) view.error = d.error || ""; else view.st = d; } catch (e) {}
        } }
    }
    Timer { interval: view.isBusy ? 700 : 1800; running: true; repeat: true; triggeredOnStart: true; onTriggered: view.poll() }
    Process {
        id: relayProc
        command: ["python3", "-I", view.ctl, "relays"]
        stdout: StdioCollector { onStreamFinished: { try { view.countries = JSON.parse(text).countries || []; } catch (e) {} } }
    }
    Process {
        id: act
        stdout: StdioCollector { onStreamFinished: {
            try { var d = JSON.parse(text); if (d.ok === false) view.error = d.error || "Mullvad didn't accept that"; } catch (e) {}
            view.pending = ""; view.lastActEnd = Date.now();
            stateProc.running = false; view.poll(); view.sys.refreshVpnStatus();
        } }
    }
    Process { id: openApp; command: ["gtk-launch", "mullvad-vpn"] }
    Component.onCompleted: relayProc.running = true

    Column {
        anchors.fill: parent
        spacing: 12

        // ------------------------------------------------------------ status
        Rectangle {
            width: parent.width; height: 112; radius: view.boxR
            color: Qt.rgba(1, 1, 1, 0.06)
            Column {
                x: 18; anchors.verticalCenter: parent.verticalCenter
                width: parent.width - x - power.width - 34; spacing: 5
                Row {
                    spacing: 7
                    Rectangle {
                        width: 7; height: 7; radius: 3.5; anchors.verticalCenter: parent.verticalCenter
                        color: view.isOn ? view.sys.colFg : view.vstate === "blocked" ? view.sys.colCrit : Qt.rgba(1, 1, 1, 0.3)
                        SequentialAnimation on opacity { running: view.isBusy; loops: Animation.Infinite
                            NumberAnimation { to: 0.25; duration: 450 } NumberAnimation { to: 1; duration: 450 } }
                    }
                    Text {
                        text: view.pending === "power" || view.vstate === "busy" ? (view.isOn ? "Disconnecting…" : "Connecting…")
                            : ({ connected: "Connected", disconnected: "Disconnected", blocked: "Blocked · waiting for the network", unknown: "Mullvad" })[view.vstate] || "Mullvad"
                        color: view.vstate === "blocked" ? view.sys.colCrit : view.sys.colMuted
                        font { pixelSize: 12; family: view.sys.fontBody }
                    }
                }
                Text {
                    width: parent.width; elide: Text.ElideRight
                    text: view.isOn && view.st.city ? view.st.city + ", " + view.st.country : view.selectedLabel
                    color: view.sys.colFg; font { pixelSize: 20; bold: true; family: view.sys.fontBody }
                }
                Text {
                    width: parent.width; elide: Text.ElideRight
                    text: view.isOn ? (view.st.relay || "") + (view.st.ip ? "  ·  " + view.st.ip : "")
                        : view.error ? view.error
                        : view.st.here ? "Visible as " + view.st.here : ""
                    color: view.error && !view.isOn ? view.sys.colCrit : view.sys.colMuted
                    font { pixelSize: 11; family: view.sys.fontFam }
                }
            }
            // the one button that matters
            Rectangle {
                id: power
                anchors.right: parent.right; anchors.rightMargin: 18; anchors.verticalCenter: parent.verticalCenter
                width: 60; height: 60; radius: 30
                color: view.isOn ? view.sys.colFg : (powerMa.containsMouse ? Qt.rgba(1, 1, 1, 0.14) : Qt.rgba(1, 1, 1, 0.08))
                scale: powerMa.pressed ? 0.94 : 1
                Behavior on color { ColorAnimation { duration: 200 } }
                Behavior on scale { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
                Shape {
                    anchors.centerIn: parent; width: 24; height: 24
                    preferredRendererType: Shape.CurveRenderer
                    ShapePath {
                        scale: Qt.size(1.2, 1.2)
                        fillColor: "transparent"; strokeWidth: 2
                        strokeColor: view.isOn ? view.sys.colBg : view.sys.colFg
                        capStyle: ShapePath.RoundCap
                        PathSvg { path: "M 10 3 L 10 9.5 M 6 5.2 A 6.5 6.5 0 1 0 14 5.2" }
                    }
                }
                // spinning ring while it connects or disconnects
                Shape {
                    anchors.fill: parent; anchors.margins: -4
                    visible: view.isBusy
                    preferredRendererType: Shape.CurveRenderer
                    ShapePath {
                        fillColor: "transparent"; strokeWidth: 2; capStyle: ShapePath.RoundCap
                        strokeColor: view.sys.colFg
                        PathAngleArc { centerX: 34; centerY: 34; radiusX: 33; radiusY: 33; startAngle: 0; sweepAngle: 90 }
                    }
                    RotationAnimator on rotation { from: 0; to: 360; duration: 900; loops: Animation.Infinite; running: view.isBusy }
                }
                MouseArea {
                    id: powerMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: view.run("power", [view.vstate === "disconnected" ? "connect" : "disconnect"])
                }
            }
        }

        // ------------------------------------------------------------ servers | settings
        Rectangle {
            id: seg
            anchors.horizontalCenter: parent.horizontalCenter
            width: 220; height: 32; radius: 16
            color: Qt.rgba(1, 1, 1, 0.06)
            Rectangle {
                width: parent.width / 2 - 4; height: parent.height - 6; y: 3; radius: height / 2
                x: view.tab === "servers" ? 3 : parent.width / 2 + 1
                color: Qt.rgba(1, 1, 1, 0.12)
                Behavior on x { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
            }
            Repeater {
                model: [{ k: "servers", t: "Servers" }, { k: "settings", t: "Settings" }]
                delegate: Item {
                    required property var modelData
                    required property int index
                    x: index * seg.width / 2; width: seg.width / 2; height: seg.height
                    Text { anchors.centerIn: parent; text: parent.modelData.t
                           color: view.tab === parent.modelData.k ? view.sys.colFg : view.sys.colMuted
                           Behavior on color { ColorAnimation { duration: 180 } }
                           font { pixelSize: 12; bold: view.tab === parent.modelData.k; family: view.sys.fontBody } }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: view.tab = parent.modelData.k }
                }
            }
        }

        Item {
            width: parent.width
            height: parent.height - y

            // -------------------------------------------------------- servers
            Item {
                id: servers
                anchors.fill: parent
                opacity: view.tab === "servers" ? 1 : 0; visible: opacity > 0
                x: view.tab === "servers" ? 0 : -16
                Behavior on opacity { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }
                Behavior on x { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }

                Rectangle {
                    id: searchBox
                    width: parent.width; height: 38; radius: view.rInner
                    color: search.activeFocus ? Qt.rgba(1, 1, 1, 0.075) : Qt.rgba(1, 1, 1, 0.055)
                    Behavior on color { ColorAnimation { duration: 150 } }
                    TextInput {
                        id: search
                        anchors.fill: parent; anchors.leftMargin: 14; anchors.rightMargin: 14
                        verticalAlignment: TextInput.AlignVCenter; clip: true
                        color: view.sys.colFg; selectionColor: Qt.rgba(1, 1, 1, 0.25)
                        font { pixelSize: 13; family: view.sys.fontFam }
                        onTextChanged: view.query = text
                        Text { anchors.verticalCenter: parent.verticalCenter; visible: !search.text
                               text: "Search countries and cities"; color: view.sys.colMuted
                               font { pixelSize: 13; family: view.sys.fontFam } }
                    }
                }

                Flow {
                    id: recents
                    anchors.top: searchBox.bottom; anchors.topMargin: visible ? 10 : 0
                    width: parent.width; spacing: 6
                    visible: !view.query && (view.st.recents || []).length > 0
                    height: visible ? implicitHeight : 0
                    Repeater {
                        model: view.st.recents || []
                        delegate: Rectangle {
                            required property var modelData
                            width: chipText.implicitWidth + 24; height: 28; radius: 14
                            color: chipMa.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : Qt.rgba(1, 1, 1, 0.07)
                            Behavior on color { ColorAnimation { duration: 120 } }
                            Text { id: chipText; anchors.centerIn: parent; text: parent.modelData.label
                                   color: view.sys.colFg; font { pixelSize: 11; family: view.sys.fontBody } }
                            MouseArea { id: chipMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                        onClicked: view.pick(parent.modelData.cc, parent.modelData.city) }
                        }
                    }
                }

                ListView {
                    id: list
                    anchors.top: recents.bottom; anchors.topMargin: 10
                    anchors.bottom: parent.bottom
                    width: parent.width
                    clip: true; spacing: 2
                    boundsBehavior: Flickable.StopAtBounds
                    model: view.filtered
                    ScrollBar.vertical: ScrollBar {
                        id: nub; policy: ScrollBar.AsNeeded; width: hovered || pressed ? 6 : 3; padding: 0
                        x: list.width - width
                        Behavior on width { NumberAnimation { duration: 120 } }
                        background: Item {}
                        contentItem: Rectangle { implicitWidth: 3; radius: width / 2; color: Qt.rgba(1, 1, 1, nub.pressed ? 0.55 : 0.32)
                                                 opacity: nub.active || nub.hovered ? 1 : 0
                                                 Behavior on opacity { NumberAnimation { duration: 260 } } }
                    }
                    delegate: Column {
                        id: country
                        required property var modelData
                        readonly property bool open: view.openCountry === modelData.code || (view.query && modelData.byCity)
                        readonly property bool chosen: view.sel.cc === modelData.code
                        width: list.width - 8

                        Rectangle {
                            width: parent.width; height: 42; radius: view.rInner
                            color: rowMa.containsMouse ? Qt.rgba(1, 1, 1, 0.06) : "transparent"
                            Behavior on color { ColorAnimation { duration: 120 } }
                            Rectangle {
                                id: badge; x: 10; anchors.verticalCenter: parent.verticalCenter
                                width: 28; height: 20; radius: 6
                                color: country.chosen ? view.sys.colFg : Qt.rgba(1, 1, 1, 0.08)
                                Text { anchors.centerIn: parent; text: country.modelData.code.toUpperCase()
                                       color: country.chosen ? view.sys.colBg : view.sys.colMuted
                                       font { pixelSize: 10; bold: true; family: view.sys.fontFam } }
                            }
                            Text {
                                anchors.left: badge.right; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter
                                text: country.modelData.name; color: view.sys.colFg
                                font { pixelSize: 13; bold: country.chosen; family: view.sys.fontBody }
                            }
                            Text {
                                anchors.right: chev.left; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter
                                visible: view.pending === "loc:" + country.modelData.code + "/"
                                text: "···"; color: view.sys.colMuted; font.pixelSize: 12
                            }
                            Shape {
                                id: chev
                                anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
                                width: 12; height: 12
                                visible: country.modelData.cities.length > 1
                                rotation: country.open ? 90 : 0
                                Behavior on rotation { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                                preferredRendererType: Shape.CurveRenderer
                                ShapePath { fillColor: "transparent"; strokeColor: view.sys.colMuted; strokeWidth: 1.6
                                            capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin
                                            PathSvg { path: "M 4.5 2.5 L 8 6 L 4.5 9.5" } }
                            }
                            MouseArea {
                                id: rowMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    var c = country.modelData;
                                    if (c.cities.length <= 1) view.pick(c.code, c.cities.length ? c.cities[0].code : "");
                                    else view.openCountry = view.openCountry === c.code ? "" : c.code;
                                }
                            }
                        }

                        // cities, folded under their country
                        Item {
                            width: parent.width
                            height: country.open ? cities.implicitHeight : 0
                            clip: true
                            Behavior on height { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }
                            Column {
                                id: cities
                                width: parent.width
                                Repeater {
                                    model: country.modelData.cities.length > 1 ? [{ code: "", name: "Any city", count: 0 }].concat(country.modelData.cities) : []
                                    delegate: Rectangle {
                                        required property var modelData
                                        readonly property bool chosen: country.chosen && (view.sel.city || "") === modelData.code && !view.sel.host
                                        width: cities.width; height: 36; radius: view.rInner
                                        color: cityMa.containsMouse ? Qt.rgba(1, 1, 1, 0.06) : "transparent"
                                        Text {
                                            x: 50; anchors.verticalCenter: parent.verticalCenter
                                            text: parent.modelData.name
                                            color: parent.chosen ? view.sys.colFg : (parent.modelData.code ? view.sys.colFg : view.sys.colMuted)
                                            font { pixelSize: 12; bold: parent.chosen; family: view.sys.fontBody }
                                        }
                                        Text {
                                            anchors.right: parent.right; anchors.rightMargin: 14; anchors.verticalCenter: parent.verticalCenter
                                            text: view.pending === "loc:" + country.modelData.code + "/" + parent.modelData.code ? "···"
                                                : parent.chosen ? "Selected"
                                                : parent.modelData.count ? parent.modelData.count + (parent.modelData.count === 1 ? " server" : " servers") : ""
                                            color: view.sys.colMuted; font { pixelSize: 11; family: view.sys.fontBody }
                                        }
                                        MouseArea { id: cityMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                                    onClicked: view.pick(country.modelData.code, parent.modelData.code) }
                                    }
                                }
                            }
                        }
                    }
                    Text {
                        anchors.centerIn: parent; visible: list.count === 0
                        text: view.countries.length ? "No match" : "Loading servers…"
                        color: view.sys.colMuted; font { pixelSize: 12; family: view.sys.fontBody }
                    }
                }
            }

            // -------------------------------------------------------- settings
            Flickable {
                id: settings
                anchors.fill: parent
                opacity: view.tab === "settings" ? 1 : 0; visible: opacity > 0
                x: view.tab === "settings" ? 0 : 16
                Behavior on opacity { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }
                Behavior on x { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
                clip: true; contentHeight: setCol.implicitHeight + 6
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {
                    id: nub2; policy: ScrollBar.AsNeeded; width: hovered || pressed ? 6 : 3; padding: 0
                    x: settings.width - width
                    background: Item {}
                    contentItem: Rectangle { implicitWidth: 3; radius: width / 2; color: Qt.rgba(1, 1, 1, nub2.pressed ? 0.55 : 0.32)
                                             opacity: nub2.active || nub2.hovered ? 1 : 0
                                             Behavior on opacity { NumberAnimation { duration: 260 } } }
                }
                Column {
                    id: setCol
                    width: settings.width - 8; spacing: 8
                    Repeater {
                        model: [
                            { title: "Connection", rows: [
                                { k: "autoconnect", t: "Auto-connect", s: "Connect when you log in" },
                                { k: "lockdown", t: "Lockdown mode", s: "Block the internet whenever the VPN is off" },
                                { k: "lan", t: "Local network sharing", s: "Reach printers and other devices at home" },
                                { k: "quantum", t: "Quantum-resistant tunnel", s: "Post-quantum key exchange" },
                                { k: "daita", t: "DAITA", s: "Hides traffic patterns from analysis; slower" } ] },
                            { title: "DNS content blockers", rows: [
                                { k: "ads", t: "Ads", d: true }, { k: "trackers", t: "Trackers", d: true },
                                { k: "malware", t: "Malware", d: true }, { k: "adult", t: "Adult content", d: true },
                                { k: "gambling", t: "Gambling", d: true }, { k: "social", t: "Social media", d: true } ] }
                        ]
                        delegate: Column {
                            id: section
                            required property var modelData
                            width: setCol.width; spacing: 8
                            Text { leftPadding: 4; topPadding: 4; text: section.modelData.title; color: view.sys.colMuted
                                   font { pixelSize: 11; family: view.sys.fontBody; letterSpacing: 0.3 } }
                            Rectangle {
                                width: parent.width; height: rows.implicitHeight + 8; radius: view.boxR
                                color: Qt.rgba(1, 1, 1, 0.05)
                                Column {
                                    id: rows; y: 4; width: parent.width
                                    Repeater {
                                        model: section.modelData.rows
                                        delegate: Item {
                                            id: row
                                            required property var modelData
                                            readonly property bool value: row.modelData.d ? !!(view.st.dns || {})[row.modelData.k] : !!view.st[row.modelData.k]
                                            width: rows.width; height: row.modelData.s ? 54 : 42
                                            Column {
                                                x: 16; anchors.verticalCenter: parent.verticalCenter; spacing: 2
                                                width: parent.width - x - sw.width - 32
                                                Text { text: row.modelData.t; color: view.sys.colFg; font { pixelSize: 13; family: view.sys.fontBody } }
                                                Text { visible: !!row.modelData.s; width: parent.width; elide: Text.ElideRight
                                                       text: row.modelData.s || ""; color: view.sys.colMuted; font { pixelSize: 11; family: view.sys.fontBody } }
                                            }
                                            Rectangle {
                                                id: sw
                                                anchors.right: parent.right; anchors.rightMargin: 16; anchors.verticalCenter: parent.verticalCenter
                                                width: 38; height: 22; radius: 11
                                                color: row.value ? view.sys.colFg : Qt.rgba(1, 1, 1, 0.14)
                                                opacity: view.st.clientState === undefined || (row.modelData.d && view.st.customDns) ? 0.4 : 1
                                                Behavior on color { ColorAnimation { duration: 160 } }
                                                Rectangle {
                                                    width: 16; height: 16; radius: 8; y: 3
                                                    x: row.value ? parent.width - width - 3 : 3
                                                    color: row.value ? view.sys.colBg : Qt.rgba(1, 1, 1, 0.85)
                                                    Behavior on x { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
                                                }
                                            }
                                            MouseArea {
                                                anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                                enabled: view.st.clientState !== undefined && !(row.modelData.d && view.st.customDns)
                                                onClicked: view.flip(row.modelData.k, !!row.modelData.d)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    Row {
                        anchors.horizontalCenter: parent.horizontalCenter; spacing: 22; topPadding: 4
                        Repeater {
                            model: [{ t: "Change VPN client", a: "client" }, { t: "Open Mullvad app", a: "app" }]
                            delegate: Text {
                                required property var modelData
                                text: modelData.t; color: linkMa.containsMouse ? view.sys.colFg : view.sys.colMuted
                                font { pixelSize: 11; family: view.sys.fontBody; underline: linkMa.containsMouse }
                                MouseArea { id: linkMa; anchors.fill: parent; anchors.margins: -6; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                            onClicked: { if (parent.modelData.a === "client") view.sys.vpnClassic = true; else openApp.running = true; } }
                            }
                        }
                    }
                }
            }
        }
    }
}

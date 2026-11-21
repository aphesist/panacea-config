import QtQuick
import QtQuick.Effects
import QtCore

// panacea-island: the lock screen's face, drawn with the kit's look (ui/DESIGN.md): black, white
// and greys, one red, JetBrains Mono, Phosphor icons, a dot-matrix clock, no strokes.
// lock-patch.py copies this next to lock.qml and puts it in the lock surface in place of
// Panacea's own drawing. Presentation only: everything it shows comes from the lock's root
// (`lk`: password length, auth mode, PAM checking / error, fingerprint state); the password
// field, PAM and fingerprint sessions stay in lock.qml.
// Self-contained on purpose (only DotText, which ships with Panacea): the lock must load even
// if the island's kit files are missing. Tokens below mirror PkTheme.qml.
Item {
    id: face
    property var lk

    // ---- kit tokens (PkTheme.qml)
    readonly property color fg: "#ffffff"
    readonly property color soft: Qt.rgba(1, 1, 1, 0.7)
    readonly property color muted: Qt.rgba(1, 1, 1, 0.45)
    readonly property color faint: Qt.rgba(1, 1, 1, 0.28)
    readonly property color accent: "#d71921"
    readonly property color accentText: "#ff7a7f"
    readonly property string font: lk && lk.fontFam ? lk.fontFam : "JetBrainsMono Nerd Font"
    readonly property int tCaption: 11
    readonly property int tLabel: 12
    readonly property int tBody: 13
    readonly property int tEmph: 14
    readonly property int dFast: 120
    readonly property int dBase: 200
    readonly property int dSlow: 320

    // ---- Phosphor icons, loaded from the files (as PkTheme does); Nerd Font glyphs if missing
    readonly property string fontDir: StandardPaths.writableLocation(StandardPaths.GenericDataLocation) + "/fonts/phosphor/"
    FontLoader { id: phBold; source: face.fontDir + "Phosphor-Bold.ttf" }
    FontLoader { id: phFill; source: face.fontDir + "Phosphor-Fill.ttf" }
    readonly property bool phosphor: phBold.status === FontLoader.Ready && phFill.status === FontLoader.Ready
    readonly property var ph: ({ "lock": 58120, "unlock": 58122, "fingerprint": 57918, "spin": 60228 })
    readonly property var nerd: ({ "lock": 0xF033E, "unlock": 0xF0FC6, "fingerprint": 0xF0237, "spin": 0xF0772, "fpoff": 0xF0EB1 })
    function glyph(n) { return String.fromCodePoint(face.phosphor ? face.ph[n === "fpoff" ? "fingerprint" : n] : face.nerd[n]); }
    function iconFont(filled) { return face.phosphor ? (filled ? phFill.name : phBold.name) : face.font; }

    readonly property bool auth: !!lk && lk.authMode
    readonly property bool bad: !!lk && lk.errorText.length > 0
    readonly property string fp: lk && lk.fpState !== undefined ? lk.fpState : "idle"

    // ---------------------------------------------------------------- wallpaper, deep black
    Image {
        id: bg
        anchors.fill: parent
        source: face.lk && face.lk.wallpaper.length ? "file://" + face.lk.wallpaper : ""
        fillMode: Image.PreserveAspectCrop
        cache: true
        asynchronous: false
        // huge wallpapers: decode already scaled (Qt refuses images over 256 MB)
        sourceSize: Qt.size(face.width * 2, face.height * 2)
        layer.enabled: true
        layer.smooth: true
    }
    MultiEffect {
        anchors.fill: parent
        source: bg
        visible: bg.status === Image.Ready
        blurEnabled: true
        autoPaddingEnabled: false        // fill to the edges (padding left a dark frame)
        blurMax: face.lk && face.lk.cfg ? face.lk.cfg.lockBlur : 32
        blurMultiplier: 0.85
        blur: face.auth ? 1.0 : 0.35
        Behavior on blur { NumberAnimation { duration: 420; easing.type: Easing.OutCubic } }
    }
    // OLED: the wallpaper only glows through; typing takes it almost to black
    Rectangle {
        anchors.fill: parent
        color: "#000000"
        opacity: face.auth ? 0.82 : 0.62
        Behavior on opacity { NumberAnimation { duration: 420; easing.type: Easing.OutCubic } }
    }

    // ---------------------------------------------------------------- burn-in guard
    // The idle clock drifts a few pixels every minute, so nothing sits on the same pixels.
    property real driftX: 0
    property real driftY: 0
    Timer {
        interval: 60000; running: !face.auth; repeat: true
        onTriggered: { face.driftX = Math.round((Math.random() * 2 - 1) * 14); face.driftY = Math.round((Math.random() * 2 - 1) * 10); }
    }
    Behavior on driftX { NumberAnimation { duration: 2400; easing.type: Easing.InOutSine } }
    Behavior on driftY { NumberAnimation { duration: 2400; easing.type: Easing.InOutSine } }

    // ---------------------------------------------------------------- clock
    Column {
        id: clockCol
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.horizontalCenterOffset: face.auth ? 0 : face.driftX
        y: face.height / 2 - height / 2 - (face.auth ? 96 : 24) + (face.auth ? 0 : face.driftY)
        spacing: 0
        Behavior on y { NumberAnimation { duration: 420; easing.type: Easing.OutCubic } }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: face.glyph("lock")
            color: face.muted
            font { family: face.iconFont(false); pixelSize: 22 }
            opacity: face.auth ? 0 : 1
            visible: opacity > 0.01
            Behavior on opacity { NumberAnimation { duration: face.dSlow } }
        }
        Item { width: 1; height: face.auth ? 0 : 26; Behavior on height { NumberAnimation { duration: 420; easing.type: Easing.OutCubic } } }

        DotText {
            anchors.horizontalCenter: parent.horizontalCenter
            value: face.lk ? face.lk.timeText : ""
            size: 84
            gapRatio: 0.2
            color: face.fg
            // scale, not size: a new size rebuilds every dot
            scale: face.auth ? 0.7 : 1
            Behavior on scale { NumberAnimation { duration: 420; easing.type: Easing.OutCubic } }
        }
        Item { width: 1; height: 22 }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: face.lk ? face.lk.dateText : ""
            color: face.soft
            font { family: face.font; pixelSize: face.tEmph }
        }
        // the owner's line (whose machine, who to call); none when empty
        Item { width: 1; height: hint.visible ? 8 : 0 }
        Text {
            id: hint
            anchors.horizontalCenter: parent.horizontalCenter
            visible: text.length > 0
            text: face.lk && face.lk.cfg ? face.lk.cfg.lockHint : ""
            color: face.muted
            font { family: face.font; pixelSize: face.tLabel }
        }
    }

    // ---------------------------------------------------------------- password pill
    Item {
        id: field
        width: face.auth ? 360 : 200
        height: 52
        anchors.horizontalCenter: parent.horizontalCenter
        y: face.height / 2 + 64
        opacity: face.auth && face.fp !== "ok" ? 1 : 0     // a fingerprint unlock needs no box
        visible: opacity > 0.01
        Behavior on width { NumberAnimation { duration: 380; easing.type: Easing.OutCubic } }
        Behavior on opacity { NumberAnimation { duration: 260 } }

        transform: Translate { id: shakeT }
        SequentialAnimation {
            id: shake
            loops: 2
            NumberAnimation { target: shakeT; property: "x"; to: -9; duration: 55 }
            NumberAnimation { target: shakeT; property: "x"; to:  9; duration: 55 }
            NumberAnimation { target: shakeT; property: "x"; to:  0; duration: 55 }
        }
        Connections {
            target: face.lk
            function onErrorTextChanged() { if (face.lk.errorText.length) shake.restart(); }
        }

        Rectangle {
            anchors.fill: parent
            radius: height / 2
            color: Qt.rgba(1, 1, 1, 0.11)          // the kit's focused field veil

            Text {
                id: fieldIcon
                x: 20; anchors.verticalCenter: parent.verticalCenter
                width: 20; horizontalAlignment: Text.AlignHCenter
                text: face.glyph(face.lk && face.lk.checking ? "spin" : "lock")
                color: face.bad ? face.accent : face.muted
                font { family: face.iconFont(false); pixelSize: 18 }
                Behavior on color { ColorAnimation { duration: face.dBase } }
                RotationAnimator on rotation {
                    running: !!face.lk && face.lk.checking
                    loops: Animation.Infinite
                    from: 0; to: 360; duration: 900
                }
                onTextChanged: if (!(face.lk && face.lk.checking)) rotation = 0
            }

            // one dot per character, the kit's dot motif
            Row {
                x: fieldIcon.x + fieldIcon.width + 14
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                Repeater {
                    model: face.lk ? Math.min(face.lk.password.length, 18) : 0
                    Rectangle {
                        width: 8; height: 8; radius: 4
                        color: face.fg
                        opacity: face.lk && face.lk.checking ? 0.45 : 1
                        scale: 0
                        Component.onCompleted: scale = 1
                        Behavior on scale { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
                        Behavior on opacity { NumberAnimation { duration: face.dBase } }
                    }
                }
                Text {
                    visible: !face.lk || face.lk.password.length === 0
                    text: face.lk ? face.lk.tr("Пароль") : "Password"
                    color: face.faint
                    font { family: face.font; pixelSize: face.tBody }
                }
            }
        }
    }

    // under the pill: the error in red, else whose session this is
    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        y: field.y + field.height + 14
        text: face.bad ? face.lk.errorText : (face.lk ? face.lk.nick : "")
        color: face.bad ? face.accentText : face.muted
        opacity: face.auth && face.fp !== "ok" ? 1 : 0
        visible: opacity > 0.01
        font { family: face.font; pixelSize: face.tLabel }
        Behavior on opacity { NumberAnimation { duration: face.dSlow } }
        Behavior on color { ColorAnimation { duration: face.dBase } }
    }

    // idle: how to start typing
    Text {
        id: enterHint
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.horizontalCenterOffset: face.driftX
        y: clockCol.y + clockCol.height + 24          // follows the clock's drift
        text: face.lk ? face.lk.tr("Нажмите Enter") : "Press Enter"
        color: face.faint
        font { family: face.font; pixelSize: face.tLabel }
        opacity: face.auth ? 0 : pulse
        visible: opacity > 0.01
        property real pulse: 1
        SequentialAnimation on pulse {
            running: !face.auth
            loops: Animation.Infinite
            NumberAnimation { to: 0.45; duration: 1400; easing.type: Easing.InOutSine }
            NumberAnimation { to: 1.0; duration: 1400; easing.type: Easing.InOutSine }
        }
    }

    // ---------------------------------------------------------------- fingerprint
    // listening (soft pulse) / unavailable (faint) / password needed after a restart (faint) /
    // not recognized (red + shake) / recognized (fills white, then the fade)
    Column {
        id: fpCol
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 64
        spacing: 12
        opacity: face.fp === "idle" ? 0 : 1
        visible: opacity > 0.01
        Behavior on opacity { NumberAnimation { duration: 300 } }
        transform: Translate { id: fpShakeT }
        SequentialAnimation {
            id: fpShake
            loops: 2
            NumberAnimation { target: fpShakeT; property: "x"; to: -8; duration: 55 }
            NumberAnimation { target: fpShakeT; property: "x"; to:  8; duration: 55 }
            NumberAnimation { target: fpShakeT; property: "x"; to:  0; duration: 55 }
        }
        Connections {
            target: face.lk
            function onFpStateChanged() { if (face.lk.fpState === "fail") fpShake.restart(); }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: face.glyph(face.fp === "off" ? "fpoff" : "fingerprint")
            color: face.fp === "fail" ? face.accent
                 : (face.fp === "off" || face.fp === "pw") ? face.faint : face.fg
            opacity: face.fp === "ready" && face.lk ? face.lk.fpPulse : 1
            scale: face.fp === "ok" ? 1.12 : 1
            font { family: face.iconFont(face.fp === "ok"); pixelSize: 38 }
            Behavior on scale { NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }
            Behavior on color { ColorAnimation { duration: face.dBase } }
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: face.lk && face.lk.fpLabel !== undefined ? face.lk.fpLabel : ""
            color: face.fp === "fail" ? face.accentText : face.muted
            font { family: face.font; pixelSize: face.tLabel }
            Behavior on color { ColorAnimation { duration: face.dBase } }
        }
    }
}

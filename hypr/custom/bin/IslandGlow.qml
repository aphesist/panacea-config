import QtQuick
import QtQuick.Shapes
import QtQuick.Effects

// written by portal-patch.py (panacea-config) - the island's activity glow.
//
// A thin light that runs along the island's exact outline while something works:
// white for the system (VPN connecting), Claude's orange while it thinks, an
// agent's own colours for anything that asks (`panacea-glow`, or
// `qs ipc call pill glow <id> <colours>`). The line sits on the edge itself, half
// inside and half out, and follows every curve: the two flares where the island
// meets the screen edge, its sides and bottom corners. A detached island (big
// centred pages) gets a closed loop around all four corners instead.
//
//   loop    runs from one end to the other and starts again (laps a detached island)
//   bounce  runs to the far end and back
Item {
    id: glow
    property bool active: false
    property var colors: ["#ffffff"]          // head first; 1 to 3 of them
    property string style: "loop"
    property int lap: 1800                    // ms per run
    property real intensity: 0.7              // 0..1
    property bool still: false                // reduce motion: a steady lit edge
    // the island, in the parent's coordinates
    property real cx: 0
    property real cy: 0
    property real cw: 0
    property real ch: 0
    property real rTL: 0
    property real rTR: 0
    property real rBL: 0
    property real rBR: 0
    property bool attached: true              // grows from the top edge, with flares
    property real flare: 0

    readonly property real pad: 24
    x: cx - pad; y: cy - pad
    width: cw + 2 * pad; height: ch + 2 * pad

    readonly property color c0: colors.length ? colors[0] : "white"
    readonly property color c1: colors.length > 1 ? colors[1] : c0
    readonly property color c2: colors.length > 2 ? colors[2] : c1
    function a(c, alpha) { return Qt.rgba(c.r, c.g, c.b, alpha); }

    opacity: active ? 1 : 0
    visible: opacity > 0.01
    Behavior on opacity { NumberAnimation { duration: 450; easing.type: Easing.OutCubic } }

    // ---- the outline (item coordinates)
    readonly property real ex0: pad
    readonly property real ey0: pad
    readonly property real ex1: pad + cw
    readonly property real ey1: pad + ch
    function rr(r) { return Math.max(0, Math.min(r, ch / 2, cw / 2)); }
    readonly property real tl: rr(rTL)
    readonly property real tr: rr(rTR)
    readonly property real bl: rr(rBL)
    readonly property real br: rr(rBR)
    readonly property real f: attached ? Math.max(0, flare) : 0
    readonly property bool closed: !attached
    readonly property real q: Math.PI / 2
    readonly property real len: closed
        ? 2 * cw + 2 * ch - (2 - q) * (tl + tr + bl + br)
        : 2 * q * f + 2 * (ch - f) + cw - (2 - q) * (bl + br)
    readonly property string d: closed
        ? "M " + (ex0 + tl) + " " + ey0 + " L " + (ex1 - tr) + " " + ey0
          + " A " + tr + " " + tr + " 0 0 1 " + ex1 + " " + (ey0 + tr)
          + " L " + ex1 + " " + (ey1 - br) + " A " + br + " " + br + " 0 0 1 " + (ex1 - br) + " " + ey1
          + " L " + (ex0 + bl) + " " + ey1 + " A " + bl + " " + bl + " 0 0 1 " + ex0 + " " + (ey1 - bl)
          + " L " + ex0 + " " + (ey0 + tl) + " A " + tl + " " + tl + " 0 0 1 " + (ex0 + tl) + " " + ey0 + " Z"
        : "M " + (ex0 - f) + " " + ey0
          + " A " + f + " " + f + " 0 0 1 " + ex0 + " " + (ey0 + f)
          + " L " + ex0 + " " + (ey1 - bl) + " A " + bl + " " + bl + " 0 0 0 " + (ex0 + bl) + " " + ey1
          + " L " + (ex1 - br) + " " + ey1 + " A " + br + " " + br + " 0 0 0 " + ex1 + " " + (ey1 - br)
          + " L " + ex1 + " " + (ey0 + f) + " A " + f + " " + f + " 0 0 1 " + (ex1 + f) + " " + ey0

    // ---- the comet: a lit stretch [from, from + seg] travelling along the path
    readonly property real seg: Math.max(60, Math.min(360, len * 0.24))
    readonly property bool bounce: style === "bounce" && !closed
    property real t: 0
    property int dir: 1
    readonly property real from: still ? 0
        : closed ? t * len - seg
        : bounce ? (dir > 0 ? t * (len - seg) : (1 - t) * (len - seg))
        : t * (len + seg) - seg
    SequentialAnimation {
        running: glow.visible && !glow.still
        loops: Animation.Infinite
        ScriptAction { script: glow.dir = 1 }
        NumberAnimation { target: glow; property: "t"; from: 0; to: 1; duration: Math.max(400, glow.lap)
                          easing.type: glow.bounce ? Easing.InOutSine : Easing.Linear }
        ScriptAction { script: if (glow.bounce) glow.dir = -1 }
        NumberAnimation { target: glow; property: "t"; from: 0; to: 1; duration: glow.bounce ? Math.max(400, glow.lap) : 0
                          easing.type: Easing.InOutSine }
    }
    // the lit part of a stretch of length s whose leading end is the head: tail behind it
    function headFrom(s) { return bounce && dir < 0 ? from : from + seg - s; }
    function dash(s, w) { return still ? [1e6, 0.01] : [Math.max(0.01, s / w), Math.max(0.01, (closed ? len - s : len + seg + s) / w)]; }
    function off(s, w) { return still ? 0 : -headFrom(s) / w; }

    // soft halo around the head, centred on the edge
    Item {
        anchors.fill: parent
        layer.enabled: glow.visible
        layer.effect: MultiEffect { blurEnabled: true; blur: 0.55; blurMax: 14 }
        Shape {
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                fillColor: "transparent"; strokeWidth: 4; capStyle: ShapePath.RoundCap
                strokeColor: glow.a(glow.c1, 0.75 * glow.intensity)
                strokeStyle: ShapePath.DashLine
                dashPattern: glow.dash(glow.seg * 0.6, 4); dashOffset: glow.off(glow.seg * 0.6, 4)
                PathSvg { path: glow.d }
            }
        }
    }
    // the fine line: the whole edge barely lit, a tail in the last colour, a bright head
    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            fillColor: "transparent"; strokeWidth: 1
            strokeColor: glow.a(glow.c1, 0.14 * glow.intensity)
            PathSvg { path: glow.d }
        }
        ShapePath {
            fillColor: "transparent"; strokeWidth: 1.1; capStyle: ShapePath.RoundCap
            strokeColor: glow.a(glow.c2, 0.35 + 0.35 * glow.intensity)
            strokeStyle: ShapePath.DashLine
            dashPattern: glow.dash(glow.seg, 1.1); dashOffset: glow.off(glow.seg, 1.1)
            PathSvg { path: glow.d }
        }
        ShapePath {
            fillColor: "transparent"; strokeWidth: 1.2; capStyle: ShapePath.RoundCap
            strokeColor: glow.a(glow.c1, 0.55 + 0.4 * glow.intensity)
            strokeStyle: ShapePath.DashLine
            dashPattern: glow.dash(glow.seg * 0.55, 1.2); dashOffset: glow.off(glow.seg * 0.55, 1.2)
            PathSvg { path: glow.d }
        }
        ShapePath {
            fillColor: "transparent"; strokeWidth: 1.5; capStyle: ShapePath.RoundCap
            strokeColor: glow.a(Qt.lighter(glow.c0, 1.2), 1)
            strokeStyle: ShapePath.DashLine
            dashPattern: glow.dash(glow.seg * 0.2, 1.5); dashOffset: glow.off(glow.seg * 0.2, 1.5)
            PathSvg { path: glow.d }
        }
    }
}

#!/usr/bin/env python3
"""Patch Panacea's lock.qml in place (idempotent, all-or-nothing).

v2 adds, on top of Panacea's stock lock:
  1. a ready marker: $XDG_RUNTIME_DIR/panacea-locked appears once the
     compositor confirms the session is locked (startup gate waits on it);
  2. a ~350 ms fade into the running desktop on unlock
     (needs misc:session_lock_xray = true, set in custom/general.lua);
  3. fingerprint unlock: a second PAM session (/etc/pam.d/panacea-fprint,
     pam_fprintd only) runs the whole time the screen is locked, so touching
     the sensor unlocks; the password keeps working alongside it;
  4. a fingerprint indicator at the bottom of the lock screen:
     listening (soft pulse) / unavailable (crossed out) /
     not recognized (red + shake) / recognized (green, then fade).

Keeps an unpatched copy (lock.qml.pristine) so older patch versions can be
upgraded. Panacea updates overwrite lock.qml; this re-runs at every
automatic lock start (custom/bin/panacea-lock). If any anchor is missing
(upstream changed the file), nothing is written and the stock lock is used.
"""
import os
import sys

QML = os.path.expanduser("~/.config/panacea/lock.qml")
PRISTINE = QML + ".pristine"
VERSION = "v4"
TAG_PREFIX = "// panacea-local patch "
TAG = TAG_PREFIX + VERSION

RUN = 'Quickshell.env("XDG_RUNTIME_DIR")'

PATCHES = [
    # 1. ready marker + start listening for a finger once locked
    (
        "    WlSessionLock {\n        id: lock\n        locked: true\n",
        "    WlSessionLock {\n        id: lock\n        locked: true\n"
        "        " + TAG + ": ready marker for the startup gate, then fingerprint\n"
        "        onSecureChanged: if (secure) {\n"
        "            Quickshell.execDetached([\"touch\", " + RUN + " + \"/panacea-locked\"]);\n"
        "            root.startFprint();\n"
        "        }\n",
    ),
    # 2. password success -> fade
    (
        "                root.password = \"\";\n"
        "                lock.locked = false;\n"
        "                quitTimer.start();\n",
        "                root.password = \"\";\n"
        "                root.fadeOut();\n",
    ),
    # 3. fade + fingerprint machinery, next to quitTimer
    (
        "    Timer { id: quitTimer; interval: 220; onTriggered: Qt.quit() }\n",
        "    Timer { id: quitTimer; interval: 220; onTriggered: Qt.quit() }\n"
        "\n"
        "    " + TAG + ": fade into the desktop on unlock\n"
        "    property real fade: 1\n"
        "    property bool unlocking: false\n"
        "    NumberAnimation {\n"
        "        id: fadeAnim\n"
        "        target: root; property: \"fade\"; to: 0\n"
        "        duration: 350; easing.type: Easing.OutCubic\n"
        "        onFinished: { lock.locked = false; quitTimer.start(); }\n"
        "    }\n"
        "    function fadeOut() {\n"
        "        if (root.unlocking) return;\n"
        "        root.unlocking = true;\n"
        "        fprintRetry.stop();\n"
        "        if (fprintPam.active) fprintPam.abort();\n"
        "        Quickshell.execDetached([\"rm\", \"-f\", " + RUN + " + \"/panacea-locked\"]);\n"
        "        fadeAnim.start();\n"
        "    }\n"
        "\n"
        "    " + TAG + ": fingerprint unlock + indicator state\n"
        "    // fpState: idle (not started yet) | ready | fail | off | ok\n"
        "    property string fpState: \"idle\"\n"
        "    property string fpFailText: \"\"\n"
        "    property bool fpGotMsg: false\n"
        "    property real fpPulse: 1\n"
        "    SequentialAnimation on fpPulse {\n"
        "        running: root.fpState === \"ready\"\n"
        "        loops: Animation.Infinite\n"
        "        NumberAnimation { to: 0.45; duration: 1300; easing.type: Easing.InOutSine }\n"
        "        NumberAnimation { to: 1.0; duration: 1300; easing.type: Easing.InOutSine }\n"
        "    }\n"
        "    readonly property color fpColor:\n"
        "        fpState === \"ok\" ? \"#5bd68a\"\n"
        "        : fpState === \"fail\" ? root.colCrit\n"
        "        : fpState === \"off\" ? Qt.rgba(1, 1, 1, 0.35) : \"#ffffff\"\n"
        "    readonly property string fpLabel:\n"
        "        fpState === \"ok\" ? \"Unlocked\"\n"
        "        : fpState === \"fail\" ? (fpFailText.length ? fpFailText : \"Not recognized\")\n"
        "        : fpState === \"off\" ? \"Fingerprint unavailable\"\n"
        "        : \"Touch the sensor to unlock\"\n"
        "    PamContext {\n"
        "        id: fprintPam\n"
        "        config: \"panacea-fprint\"\n"
        "        user: root.user\n"
        "        onPamMessage: {\n"
        "            const m = fprintPam.message;\n"
        "            if (/timed out/i.test(m)) return;          // quiet restart, not a failure\n"
        "            root.fpGotMsg = true;\n"
        "            if (fprintPam.messageIsError || /failed|again|too fast|not centered/i.test(m)) {\n"
        "                root.fpFailText = /failed to match/i.test(m) ? \"Not recognized\" : m;\n"
        "                root.fpState = \"fail\";\n"
        "                fpFailClear.restart();\n"
        "            } else if (root.fpState !== \"fail\") {\n"
        "                root.fpState = \"ready\";\n"
        "            }\n"
        "        }\n"
        "        onCompleted: result => {\n"
        "            if (result === PamResult.Success) { root.fpState = \"ok\"; root.fadeOut(); }\n"
        "            else root.fprintEnded();\n"
        "        }\n"
        "        onError: root.fprintEnded()\n"
        "    }\n"
        "    // a retry prompt mid-scan: show it briefly, then back to listening\n"
        "    Timer { id: fpFailClear; interval: 1500\n"
        "        onTriggered: if (root.fpState === \"fail\" && fprintPam.active) root.fpState = \"ready\" }\n"
        "    Timer { id: fprintRetry; onTriggered: root.startFprint() }\n"
        "    function fprintEnded() {\n"
        "        if (root.unlocking) return;\n"
        "        if (root.fpState === \"fail\") fprintRetry.interval = 1500;   // let the red show\n"
        "        else if (!root.fpGotMsg) { root.fpState = \"off\"; fprintRetry.interval = 5000; } // no sensor/prints\n"
        "        else fprintRetry.interval = 200;                                // timed out: listen again\n"
        "        fprintRetry.restart();\n"
        "    }\n"
        "    function startFprint() {\n"
        "        if (!lock.secure || root.unlocking || fprintPam.active) return;\n"
        "        root.fpGotMsg = false;\n"
        "        if (root.fpState === \"fail\") root.fpState = \"ready\";\n"
        "        if (!fprintPam.start()) root.fprintEnded();\n"
        "    }\n"
    ),
    # 4. surface goes transparent and content fades
    (
        "            color: \"#000000\"\n\n            Item {\n                anchors.fill: parent\n",
        "            color: root.fade < 1 ? \"transparent\" : \"#000000\"\n\n"
        "            Item {\n                anchors.fill: parent\n"
        "                opacity: root.fade\n",
    ),
    # 5. fingerprint indicator, bottom centre of the lock surface
    (
        "                // фокус не должен теряться ни при каких обстоятельствах\n",
        "                " + TAG + ": fingerprint indicator\n"
        "                Column {\n"
        "                    anchors.horizontalCenter: parent.horizontalCenter\n"
        "                    anchors.bottom: parent.bottom\n"
        "                    anchors.bottomMargin: 72\n"
        "                    spacing: 12\n"
        "                    opacity: root.fpState === \"idle\" ? 0 : 1\n"
        "                    visible: opacity > 0.01\n"
        "                    Behavior on opacity { NumberAnimation { duration: 300 } }\n"
        "                    transform: Translate { id: fpShakeT }\n"
        "                    SequentialAnimation {\n"
        "                        id: fpShake\n"
        "                        loops: 2\n"
        "                        NumberAnimation { target: fpShakeT; property: \"x\"; to: -8; duration: 55 }\n"
        "                        NumberAnimation { target: fpShakeT; property: \"x\"; to:  8; duration: 55 }\n"
        "                        NumberAnimation { target: fpShakeT; property: \"x\"; to:  0; duration: 55 }\n"
        "                    }\n"
        "                    Connections {\n"
        "                        target: root\n"
        "                        function onFpStateChanged() { if (root.fpState === \"fail\") fpShake.restart(); }\n"
        "                    }\n"
        "\n"
        "                    Text {\n"
        "                        anchors.horizontalCenter: parent.horizontalCenter\n"
        "                        text: String.fromCodePoint(root.fpState === \"off\" ? 0xF0EB1 : 0xF0237)\n"
        "                        color: root.fpColor\n"
        "                        opacity: root.fpState === \"ready\" ? root.fpPulse : 1\n"
        "                        scale: root.fpState === \"ok\" ? 1.15 : 1\n"
        "                        font { family: root.fontFam; pixelSize: 44 }\n"
        "                        Behavior on scale { NumberAnimation { duration: 260; easing.type: Easing.OutBack } }\n"
        "                        Behavior on color { ColorAnimation { duration: 200 } }\n"
        "                    }\n"
        "                    Text {\n"
        "                        anchors.horizontalCenter: parent.horizontalCenter\n"
        "                        text: root.fpLabel\n"
        "                        color: root.fpState === \"fail\" ? root.colCrit : Qt.rgba(1, 1, 1, 0.55)\n"
        "                        font { family: root.fontFam; pixelSize: 13; letterSpacing: 1 }\n"
        "                        Behavior on color { ColorAnimation { duration: 200 } }\n"
        "                    }\n"
        "                }\n"
        "\n"
        "                // фокус не должен теряться ни при каких обстоятельствах\n",
    ),
]



def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def write_atomic(p, text):
    tmp = p + ".patch-tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, p)


def main() -> int:
    try:
        cur = read(QML)
    except OSError as e:
        print(f"lock-patch: cannot read {QML}: {e}", file=sys.stderr)
        return 1
    if TAG in cur:
        return 0  # already at this version

    if TAG_PREFIX in cur:
        # older patch version: start again from the pristine copy
        if not os.path.exists(PRISTINE):
            print("lock-patch: older patch present but no pristine copy - "
                  "leaving lock.qml as is", file=sys.stderr)
            return 2
        src = read(PRISTINE)
    else:
        src = cur  # stock Panacea file (fresh install or after an update)

    out = src
    for old, new in PATCHES:
        if out.count(old) != 1:
            print("lock-patch: anchor not found (Panacea changed lock.qml?) "
                  "- leaving it untouched", file=sys.stderr)
            return 2
        out = out.replace(old, new, 1)

    if TAG_PREFIX not in src:
        write_atomic(PRISTINE, src)
    write_atomic(QML, out)
    print(f"lock-patch: applied {VERSION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

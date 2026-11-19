import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io

// written by claude-tools-patch.py (panacea-config): Settings > Claude.
// The island chat's tools: Claude using your own Zen (Claudezilla), and
// "Ask Claude about this" (scripts/custom/ask_claude.sh). Everything here lives in
// settings.json; bridge.py and ask_claude.sh read it on every use, nothing restarts.
ColumnLayout {
    id: page

    property var sys
    property string zilla: "checking"      // on | off | missing | checking

    Layout.fillWidth: true
    spacing: 12

    // Claude's own Zen (claude-zen-sandbox): connected? And the guard: none of your own
    // Zen profiles may have the add-on (bridge.py turns the browser off if one does).
    Process {
        id: pZilla
        command: ["sh", "-c",
            "[ -f \"$HOME/.local/share/claudezilla/mcp/server.js\" ] && [ -d \"$HOME/.config/zen/claude\" ] || { echo missing; exit; }; " +
            "for e in \"$HOME\"/.config/zen/*/extensions.json; do case \"$e\" in */zen/claude/*) continue;; esac; " +
            "jq -e '.addons[] | select(.id == \"claudezilla@boot.industries\" and (.pendingUninstall | not))' \"$e\" >/dev/null 2>&1 && { echo leak; exit; }; done; " +
            "[ -S \"${XDG_RUNTIME_DIR:-/tmp}/claudezilla.sock\" ] && echo on || echo off"]
        stdout: StdioCollector { onStreamFinished: page.zilla = text.trim() || "off" }
    }
    Timer { interval: 3000; repeat: true; running: page.visible; triggeredOnStart: true; onTriggered: pZilla.running = true }
    Process { id: pRun; property var argv: []; command: argv }
    function run(argv) { pRun.argv = argv; pRun.running = true; }

    component Note: Text {
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: page.sys.colMuted
        font { family: page.sys.fontBody; pixelSize: page.sys.fontSize - 2 }
    }

    // ------------------------------------------------------------- browser
    SetCard {
        sys: page.sys

        SetToggle {
            sys: page.sys
            label: "Let Claude use the browser"
            sub: "In a Zen profile of its own (claude-zen-sandbox): your Zen, its tabs and logins stay out of reach."
            on: page.sys.cfg.claudeBrowser
            onToggled: value => { page.sys.cfg.claudeBrowser = value; page.sys.saveCfg(); }
        }
        SetSelect {
            sys: page.sys
            visible: page.sys.cfg.claudeBrowser
            label: "Ask before"
            value: page.sys.cfg.claudeBrowserAsk || "actions"
            options: [{ id: "actions", text: "Actions" }, { id: "all", text: "Everything" }, { id: "none", text: "Nothing" }]
            onPicked: id => { page.sys.cfg.claudeBrowserAsk = id; page.sys.saveCfg(); }
        }
        Note {
            visible: page.sys.cfg.claudeBrowser
            text: (page.sys.cfg.claudeBrowserAsk === "all")
                  ? "Every browser step shows an Allow/Deny card, even just reading a page."
                  : (page.sys.cfg.claudeBrowserAsk === "none")
                  ? "Claude clicks, types and opens pages without asking. Running JavaScript in pages stays off."
                  : "Reading pages and screenshots run freely; opening pages, clicks, typing and closing tabs show a card first."
        }
        SetSelect {
            sys: page.sys
            visible: page.sys.cfg.claudeBrowser
            label: "Opens on"
            value: page.sys.cfg.claudeBrowserPlace || "desktop"
            options: [{ id: "desktop", text: "Desktop 10" }, { id: "hidden", text: "Hidden" }, { id: "current", text: "Current" }]
            // hypr/custom/zen-claude.lua reads it on reload; settings.json is written a moment later
            onPicked: id => { page.sys.cfg.claudeBrowserPlace = id; page.sys.saveCfg();
                              page.run(["sh", "-c", "sleep 0.6; hyprctl reload >/dev/null"]); }
        }
        Note {
            visible: page.sys.cfg.claudeBrowser
            text: (page.sys.cfg.claudeBrowserPlace === "hidden") ? "Out of sight on a hidden workspace; Show brings it up."
                : (page.sys.cfg.claudeBrowserPlace === "current") ? "Opens wherever you are, like any window."
                : "Its own desktop (Super+0): go there to watch Claude work. It never pulls you away from what you're doing."
        }
        SetToggle {
            sys: page.sys
            visible: page.sys.cfg.claudeBrowser
            label: "Start it when needed"
            sub: "Claude's Zen opens by itself the first time Claude uses the browser."
            on: page.sys.cfg.claudeBrowserAutostart
            onToggled: value => { page.sys.cfg.claudeBrowserAutostart = value; page.sys.saveCfg(); }
        }
        RowLayout {
            visible: page.sys.cfg.claudeBrowser
            Layout.fillWidth: true
            spacing: 10
            Rectangle {
                Layout.preferredWidth: 8; Layout.preferredHeight: 8; radius: 4
                color: page.zilla === "on" ? page.sys.colFg : (page.zilla === "missing" || page.zilla === "leak") ? page.sys.colCrit : page.sys.colMuted
            }
            Text {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: page.zilla === "leak" ? page.sys.colFg : page.sys.colMuted
                font { family: page.sys.fontBody; pixelSize: page.sys.fontSize - 2 }
                text: page.zilla === "on" ? "Claude's Zen is running and connected"
                    : page.zilla === "leak" ? "Off for safety: your own Zen still has Claudezilla. Remove it there (about:addons)."
                    : page.zilla === "missing" ? "Not set up: run install.sh from claude-zen-sandbox"
                    : page.zilla === "checking" ? "Checking…"
                    : page.sys.cfg.claudeBrowserAutostart ? "Not running: it starts when Claude needs it" : "Not running"
            }
            SetButton {
                sys: page.sys
                visible: page.zilla === "off"
                text: "Start"
                onClicked: page.run(["systemctl", "--user", "start", "zen-claude.service"])
            }
            SetButton {
                sys: page.sys
                text: "Show"
                visible: page.zilla === "on" && page.sys.cfg.claudeBrowserPlace !== "current"
                onClicked: page.run(["hyprctl", "dispatch", page.sys.cfg.claudeBrowserPlace === "hidden"
                                     ? "hl.dsp.workspace.toggle_special(\"claude\")" : "hl.dsp.focus({ workspace = 10 })"])
            }
            SetButton {
                sys: page.sys
                visible: page.zilla === "on"
                text: "Quit"
                onClicked: page.run(["systemctl", "--user", "stop", "zen-claude.service"])
            }
        }
    }

    // ------------------------------------------------------------- ask about this
    SetCard {
        sys: page.sys

        Text {
            Layout.fillWidth: true
            text: "Ask Claude about this"
            color: page.sys.colFg
            font { family: page.sys.fontBody; pixelSize: page.sys.fontSize - 1; bold: true }
        }
        Note {
            text: "Press " + (page.sys.cfg.bind_askClaude || "the shortcut") + " anywhere: the chat opens with what you selected, or a part of the screen you draw a box around."
        }
        SetSelect {
            sys: page.sys
            label: "Sends"
            value: page.sys.cfg.askSource || "auto"
            options: [{ id: "auto", text: "Selection first" }, { id: "region", text: "Screen area" }, { id: "selection", text: "Selection" }]
            onPicked: id => { page.sys.cfg.askSource = id; page.sys.saveCfg(); }
        }
        Note {
            text: (page.sys.cfg.askSource === "region") ? "Always lets you draw a box around part of the screen."
                : (page.sys.cfg.askSource === "selection") ? "Always sends the text you last selected (nothing happens without one)."
                : "Text you selected since the last time goes first; otherwise you draw a box around part of the screen."
        }
        SetSelect {
            sys: page.sys
            label: "Then"
            value: page.sys.cfg.askThen || "wait"
            options: [{ id: "wait", text: "Wait for me" }, { id: "explain", text: "Explain it" }]
            onPicked: id => { page.sys.cfg.askThen = id; page.sys.saveCfg(); }
        }
        Note {
            text: (page.sys.cfg.askThen === "explain") ? "Sends it straight away, asking Claude to explain it."
                : "Puts it in the message box so you can type your question."
        }
    }

    // ------------------------------------------------------------- shortcuts
    SetCard {
        sys: page.sys

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text {
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                    text: "Open the chat: " + (page.sys.cfg.bind_claudeChat || "off")
                    color: page.sys.colFg
                    font { family: page.sys.fontBody; pixelSize: page.sys.fontSize - 1 }
                }
                Text {
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                    text: "Ask about this: " + (page.sys.cfg.bind_askClaude || "off")
                    color: page.sys.colFg
                    font { family: page.sys.fontBody; pixelSize: page.sys.fontSize - 1 }
                }
            }
            SetButton {
                sys: page.sys
                text: "Change"
                onClicked: page.run(["qs", "-p", Quickshell.env("HOME") + "/.config/panacea", "ipc", "call", "pill", "shortcuts"])
            }
        }
    }
}

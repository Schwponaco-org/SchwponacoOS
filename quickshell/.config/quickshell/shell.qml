// Super+Tab workspace overview, macOS Cmd+Tab style: a row of live previews of every workspace.
// Hold Super and tap Tab to step through workspaces (Shift+Tab steps back, both wrap around);
// releasing Super switches to the selected one. While open, h/l/arrows also move,
// Enter/o/space go, Esc/q close, and clicking a card goes there.
// Driven from Hyprland with: qs ipc call overview next|prev|release
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland

ShellRoot {
    id: root

    property bool open: false
    property int selected: 0
    property string activeName: ""
    // with the Lua config Quickshell reads every workspace id as -1, so sort and switch by name
    readonly property var workspaces: Hyprland.workspaces.values
        .filter(w => !w.name.startsWith("special:"))
        .sort((a, b) => parseInt(a.name) - parseInt(b.name))

    // first press opens with the neighbour already selected, like Cmd+Tab; later presses keep stepping
    function step(dir) {
        const n = workspaces.length
        if (!n) return
        if (!open) {
            Hyprland.refreshToplevels()  // fresh window positions for the previews
            selected = Math.max(0, workspaces.findIndex(w => w.name === activeName))
            open = true
        }
        selected = (selected + dir + n) % n
    }

    function go(ws) {
        if (!open) return  // the release can arrive twice: from this window and from Hyprland
        open = false
        Quickshell.execDetached(["hyprctl", "dispatch", `hl.dsp.focus({ workspace = ${ws.name} })`])
    }

    IpcHandler {
        target: "overview"
        function next(): void { root.step(1) }
        function prev(): void { root.step(-1) }
        // Super released, reported by Hyprland (hyprland.lua): switch to the selected workspace
        function release(): void { root.go(root.workspaces[root.selected]) }
    }

    // Quickshell can't see the focused workspace under the Lua config, so follow Hyprland's events
    // (seeded once from hyprctl) instead of asking on every open, which keeps opening instant
    Connections {
        target: Hyprland
        function onRawEvent(event) {
            if (event.name === "workspace") root.activeName = event.data
        }
    }
    Process {
        running: true
        command: ["hyprctl", "-j", "monitors"]
        stdout: StdioCollector {
            onStreamFinished: {
                const mons = JSON.parse(text)
                root.activeName = (mons.find(m => m.focused) || mons[0]).activeWorkspace.name
            }
        }
    }

    PanelWindow {
        id: win

        readonly property real gap: 32
        readonly property int count: Math.max(1, root.workspaces.length)
        readonly property real cardW: Math.min(width * 0.24, (width * 0.9 - (count - 1) * gap) / count)
        readonly property real cardH: cardW * height / width
        readonly property real scale: cardW / width

        visible: root.open
        anchors { top: true; bottom: true; left: true; right: true }
        exclusionMode: ExclusionMode.Ignore
        color: "#cc111111"  // blurred by the "overview" layer rule in hyprland.lua
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.namespace: "overview"
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive

        MouseArea {
            anchors.fill: parent
            onClicked: root.open = false
        }

        Item {
            id: keys
            anchors.fill: parent
            focus: true
            Keys.onPressed: event => {
                switch (event.key) {
                case Qt.Key_H: case Qt.Key_Left:
                    root.step(-1); break
                case Qt.Key_L: case Qt.Key_Right:
                    root.step(1); break
                case Qt.Key_Return: case Qt.Key_Enter: case Qt.Key_Space: case Qt.Key_O:
                    root.go(root.workspaces[root.selected]); break
                case Qt.Key_Escape: case Qt.Key_Q:
                    root.open = false; break
                default:
                    return
                }
                event.accepted = true
            }
            // letting go of Super commits the selection
            Keys.onReleased: event => {
                if (event.key === Qt.Key_Super_L || event.key === Qt.Key_Super_R || event.key === Qt.Key_Meta) {
                    root.go(root.workspaces[root.selected])
                    event.accepted = true
                }
            }
        }
        onVisibleChanged: if (visible) keys.forceActiveFocus()

        Row {
            anchors.centerIn: parent
            spacing: win.gap

            Repeater {
                model: root.workspaces

                Column {
                    id: card
                    required property var modelData
                    required property int index
                    readonly property bool isSelected: index === root.selected
                    spacing: 14

                    Rectangle {
                        width: win.cardW
                        height: win.cardH
                        color: "#191919"
                        clip: true

                        Repeater {
                            model: card.modelData.toplevels.values

                            ScreencopyView {
                                required property var modelData
                                readonly property var ipc: modelData.lastIpcObject
                                readonly property var origin: modelData.monitor ? [modelData.monitor.x, modelData.monitor.y] : [0, 0]
                                x: ipc.at ? (ipc.at[0] - origin[0]) * win.scale : 0
                                y: ipc.at ? (ipc.at[1] - origin[1]) * win.scale : 0
                                width: ipc.size ? ipc.size[0] * win.scale : 0
                                height: ipc.size ? ipc.size[1] * win.scale : 0
                                captureSource: root.open ? modelData.wayland : null
                                live: root.open
                            }
                        }

                        // frame drawn above the previews
                        Rectangle {
                            anchors.fill: parent
                            color: "transparent"
                            border.width: card.isSelected ? 2 : 1
                            border.color: card.isSelected ? "#BBBBBB" : "#2A2A2A"
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.go(card.modelData)
                        }
                    }

                    Text {
                        text: card.modelData.name
                        font.family: "Helvetica Neue"
                        font.bold: true
                        font.pixelSize: 20
                        color: card.isSelected ? "#FFFFFF" : "#666666"
                    }
                }
            }
        }
    }
}

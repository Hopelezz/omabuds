import QtQuick
import Quickshell.Io
import Quickshell.Services.Mpris
import Quickshell.Services.Pipewire
import qs.Commons
import qs.Ui
import "." as BudsCore

BarWidget {
  id: root
  moduleName: "io.github.hopelezz.omabuds"

  readonly property bool showBattery: setting("showBattery", true) === true
  readonly property string earBehavior: setting("earBehavior", "One out") || "One out"
  readonly property color foreground: bar ? bar.foreground : Color.foreground
  readonly property string fontFamily: bar ? bar.fontFamily : Style.font.family
  readonly property int lowestBattery: {
    var battery = BudsCore.BudsState.battery || {}
    var levels = []
    if (battery.left !== undefined && battery.left !== null) levels.push(battery.left)
    if (battery.right !== undefined && battery.right !== null) levels.push(battery.right)
    return levels.length ? Math.min.apply(null, levels) : -1
  }
  readonly property bool showsPercent: showBattery && lowestBattery >= 0 && !button.vertical
  readonly property bool isOutput: {
    var sink = Pipewire.defaultAudioSink
    var address = BudsCore.BudsState.address
    if (!sink || !address) return false
    return String(sink.name || "").indexOf(address.replace(/:/g, "_")) >= 0
  }

  property var pausedPlayer: null
  property bool inEar: true

  readonly property bool opened: panelLoader.item ? panelLoader.item.opened === true : false
  readonly property bool popoutSwitchClosing: panelLoader.item
    ? panelLoader.item.popoutSwitchClosing === true
    : false

  function injectPanel() {
    var target = panelLoader.item
    if (!target) return
    if ("bar" in target) target.bar = root.bar
    if ("settings" in target) target.settings = root.settings
    if ("anchorItem" in target) target.anchorItem = button
    if ("hostWidget" in target) target.hostWidget = root
  }

  function open() { if (panelLoader.item) panelLoader.item.open() }
  function close() { if (panelLoader.item) panelLoader.item.close() }
  function toggle() { if (panelLoader.item) panelLoader.item.toggle() }
  function closeForPopoutSwitch() { if (panelLoader.item) panelLoader.item.closeForPopoutSwitch() }

  function applyEarChange() {
    var ear = BudsCore.BudsState.ear
    if (!ear || earBehavior === "Never" || !isOutput) return
    var out = 0
    for (var i = 0; i < ear.length; i++)
      if (ear[i] === "idle") out += 1
    var wearing = earBehavior === "Both out" ? out < 2 : out < 1
    if (wearing === inEar) return
    inEar = wearing
    if (!inEar) {
      var players = Mpris.players ? Mpris.players.values : []
      pausedPlayer = players.find(function(player) {
        return player.isPlaying && player.canPause
      }) || null
      if (pausedPlayer) pausedPlayer.pause()
      return
    }
    if (pausedPlayer) {
      if (pausedPlayer.canPlay) pausedPlayer.play()
      pausedPlayer = null
    }
  }

  // Keep the root visible so the bar can measure the button. Hide by collapsing
  // the slot; `visible: false` on the widget makes ModuleSlot width stay 0.
  visible: true
  implicitWidth: BudsCore.BudsState.connected ? button.implicitWidth : 0
  implicitHeight: BudsCore.BudsState.connected ? button.implicitHeight : 0
  opacity: BudsCore.BudsState.connected ? 1 : 0

  onBarChanged: injectPanel()
  onSettingsChanged: injectPanel()

  Connections {
    target: BudsCore.BudsState
    function onEarChanged() { root.applyEarChange() }
    function onAddressChanged() { root.applyEarChange() }
  }

  Loader {
    id: panelLoader
    active: true
    source: Qt.resolvedUrl("Panel.qml")
    visible: false
    onLoaded: {
      root.injectPanel()
      Qt.callLater(root.injectPanel)
    }
  }

  IpcHandler {
    target: "io.github.hopelezz.omabuds"
    function open(): void { root.open() }
    function close(): void { root.close() }
    function show(): void { root.open() }
    function hide(): void { root.close() }
    function toggle(): void { root.toggle() }
  }

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    labelVisible: false
    hasVisualContent: true
    keepSpace: BudsCore.BudsState.connected
    fixedWidth: vertical ? -1 : barContent.implicitWidth + scaledHorizontalMargin * 2
    fixedHeight: vertical ? Style.bar.iconSlot : -1
    tooltipText: BudsCore.BudsState.deviceName || "Galaxy Buds"
    onPressed: function(buttonCode) {
      if (buttonCode === Qt.LeftButton) root.toggle()
    }

    Row {
      id: barContent
      anchors.centerIn: parent
      spacing: Style.space(5)

      BudsIcon {
        iconSize: Style.bar.iconFont
        color: root.bar ? root.bar.barForeground : Color.foreground
        anchors.verticalCenter: parent.verticalCenter
      }

      Text {
        visible: root.showsPercent
        text: root.lowestBattery + "%"
        color: root.bar ? root.bar.barForeground : Color.foreground
        font.family: root.fontFamily
        font.pixelSize: Style.bar.iconFont
        renderType: Text.NativeRendering
        anchors.verticalCenter: parent.verticalCenter
      }
    }
  }
}

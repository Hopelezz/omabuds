import QtQuick
import qs.Commons
import qs.Ui
import "." as BudsCore

Panel {
  id: root
  moduleName: "io.github.hopelezz.omabuds"
  ipcTarget: "io.github.hopelezz.omabuds"
  manageIpc: false

  property var anchorItem: null
  property var hostWidget: null
  readonly property var barIdentity: hostWidget || root
  readonly property color contentForeground: bar ? bar.foreground : Color.foreground
  readonly property color dimForeground: Qt.darker(contentForeground, 1.55)
  readonly property string contentFontFamily: bar ? bar.fontFamily : Style.font.family
  readonly property bool showBattery: setting("showBattery", true) === true
  readonly property string earBehavior: setting("earBehavior", "One out") || "One out"

  readonly property var modeOptions: {
    var options = [{ value: "off", label: "Off" }]
    if (BudsCore.BudsState.hasFeature("anc"))
      options.push({ value: "anc", label: "ANC" })
    if (BudsCore.BudsState.hasFeature("ambient"))
      options.push({ value: "ambient", label: "Ambient" })
    if (BudsCore.BudsState.hasFeature("adaptive"))
      options.push({ value: "adaptive", label: "Adaptive" })
    return options
  }
  readonly property var eqOptions: [
    { value: "bass", label: "Bass" },
    { value: "soft", label: "Soft" },
    { value: "dynamic", label: "Dynamic" },
    { value: "clear", label: "Clear" },
    { value: "treble", label: "Treble" }
  ]
  readonly property var ambientOptions: {
    var max = 2
    var options = []
    for (var i = 0; i <= max; i++)
      options.push({ value: i, label: String(i) })
    return options
  }

  function open() { root.controller.show() }
  function close() { root.controller.hide() }
  function toggle() { if (root.opened) root.close(); else root.open() }

  function switchPanel(direction) {
    if (root.bar && typeof root.bar.switchPanelFrom === "function")
      return root.bar.switchPanelFrom(root.barIdentity, direction)
    return false
  }

  function updateSetting(key, value) {
    var entry = { id: root.moduleName }
    for (var existing in root.settings)
      if (existing !== "id") entry[existing] = root.settings[existing]
    entry[key] = value
    root.settings = entry
    if (root.hostWidget && "settings" in root.hostWidget)
      root.hostWidget.settings = entry
    if (root.bar && root.bar.shell && typeof root.bar.shell.updateEntryInline === "function")
      root.bar.shell.updateEntryInline(root.moduleName, entry)
  }

  function batteryText(component) {
    var battery = BudsCore.BudsState.battery || {}
    var charging = BudsCore.BudsState.charging || {}
    var level = battery[component]
    if (level === undefined || level === null) return "—"
    return charging[component] ? level + "% 󱐋" : level + "%"
  }

  function setMode(value) {
    if (!BudsCore.BudsState.connected) return
    BudsCore.BudsState.mode = value
    BudsCore.BudsState.send("mode", value)
  }

  function setEq(value) {
    if (!BudsCore.BudsState.connected) return
    BudsCore.BudsState.eq = value
    BudsCore.BudsState.send("eq", value)
  }

  function setAmbient(value) {
    if (!BudsCore.BudsState.connected) return
    BudsCore.BudsState.send("ambient", value)
  }

  function setToggle(key, current) {
    if (!BudsCore.BudsState.connected || current !== true && current !== false) return
    BudsCore.BudsState.send(key, current === true ? "off" : "on")
  }

  component Chip: Button {
    required property var modelData
    bordered: true
    foreground: root.contentForeground
    fontFamily: root.contentFontFamily
    fontSize: Style.font.bodySmall
  }

  component SettingRow: Item {
    property string label: ""
    property bool checked: false
    signal toggled()

    width: parent ? parent.width : 0
    implicitHeight: Math.max(rowLabel.implicitHeight, rowSwitch.implicitHeight)
    opacity: enabled ? 1.0 : 0.4

    Text {
      id: rowLabel
      text: parent.label
      color: root.contentForeground
      font.family: root.contentFontFamily
      font.pixelSize: Style.font.bodySmall
      anchors.left: parent.left
      anchors.verticalCenter: parent.verticalCenter
    }

    ToggleSwitch {
      id: rowSwitch
      checked: parent.checked
      foreground: root.contentForeground
      anchors.right: parent.right
      anchors.verticalCenter: parent.verticalCenter
      onToggled: parent.toggled()
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: root.anchorItem
    owner: root.hostWidget || root
    bar: root.bar
    open: root.opened
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Math.max(Style.space(340), modeGroup.implicitWidth))
    contentHeight: panel.fittedContentHeight(column.implicitHeight)

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }

      Column {
        id: column
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: Style.space(18)

        PanelHero {
          width: parent.width
          title: BudsCore.BudsState.deviceName || "Galaxy Buds"
          meta: BudsCore.BudsState.connected
            ? (BudsCore.BudsState.sku || BudsCore.BudsState.model)
            : "Not connected"
          foreground: root.contentForeground
          fontFamily: root.contentFontFamily
          iconOpacity: BudsCore.BudsState.connected ? 1.0 : 0.5
          iconComponent: Component {
            BudsIcon {
              iconSize: Style.font.display
              color: root.contentForeground
            }
          }
        }

        Column {
          width: parent.width
          spacing: Style.space(6)
          visible: BudsCore.BudsState.connected

          PanelSectionHeader {
            width: parent.width
            text: "Battery"
            foreground: root.contentForeground
            fontFamily: root.contentFontFamily
          }

          Row {
            id: batteryRow
            width: parent.width
            spacing: Style.space(18)

            Repeater {
              model: [
                { label: "Left", key: "left" },
                { label: "Right", key: "right" },
                { label: "Case", key: "case" }
              ]

              delegate: Column {
                required property var modelData
                width: (batteryRow.width - batteryRow.spacing * 2) / 3
                spacing: Style.space(2)

                Text {
                  text: modelData.label
                  color: root.dimForeground
                  font.family: root.contentFontFamily
                  font.pixelSize: Style.font.caption
                }

                Text {
                  text: root.batteryText(modelData.key)
                  color: root.contentForeground
                  font.family: root.contentFontFamily
                  font.pixelSize: Style.font.body
                }
              }
            }
          }
        }

        Column {
          width: parent.width
          spacing: Style.space(6)
          visible: BudsCore.BudsState.connected && root.modeOptions.length > 1

          PanelSectionHeader {
            width: parent.width
            text: "Noise control"
            foreground: root.contentForeground
            fontFamily: root.contentFontFamily
          }

          Row {
            id: modeGroup
            spacing: Style.spacing.md

            Repeater {
              model: root.modeOptions
              Chip {
                text: modelData.label
                selected: modelData.value === BudsCore.BudsState.mode
                onClicked: root.setMode(modelData.value)
              }
            }
          }

          Row {
            spacing: Style.spacing.md
            visible: BudsCore.BudsState.mode === "ambient"
              && BudsCore.BudsState.hasFeature("ambient_volume")

            Repeater {
              model: root.ambientOptions
              Chip {
                text: modelData.label
                selected: BudsCore.BudsState.ambientVolume === modelData.value
                onClicked: root.setAmbient(modelData.value)
              }
            }
          }
        }

        Column {
          width: parent.width
          spacing: Style.space(6)
          visible: BudsCore.BudsState.connected && BudsCore.BudsState.hasFeature("eq")

          PanelSectionHeader {
            width: parent.width
            text: "Equalizer"
            foreground: root.contentForeground
            fontFamily: root.contentFontFamily
          }

          Row {
            spacing: Style.spacing.md
            Repeater {
              model: root.eqOptions
              Chip {
                text: modelData.label
                selected: modelData.value === BudsCore.BudsState.eq
                onClicked: root.setEq(modelData.value)
              }
            }
          }
        }

        Column {
          width: parent.width
          spacing: Style.space(6)
          visible: BudsCore.BudsState.connected

          PanelSectionHeader {
            width: parent.width
            text: "Controls"
            foreground: root.contentForeground
            fontFamily: root.contentFontFamily
          }

          SettingRow {
            visible: BudsCore.BudsState.hasFeature("voice_detect")
              && BudsCore.BudsState.voiceDetect !== null
            label: "Voice Detect"
            checked: BudsCore.BudsState.voiceDetect === true
            onToggled: root.setToggle("voice_detect", BudsCore.BudsState.voiceDetect)
          }

          SettingRow {
            visible: BudsCore.BudsState.hasFeature("onebud")
              && BudsCore.BudsState.oneBud !== null
            label: "One-Bud ANC"
            checked: BudsCore.BudsState.oneBud === true
            onToggled: root.setToggle("onebud", BudsCore.BudsState.oneBud)
          }

          SettingRow {
            visible: BudsCore.BudsState.hasFeature("touch_lock")
            label: "Lock touchpad"
            checked: BudsCore.BudsState.touchLock === true
            onToggled: root.setToggle("touch_lock", BudsCore.BudsState.touchLock)
          }

          SettingRow {
            visible: BudsCore.BudsState.hasFeature("gaming")
            label: "Game mode"
            checked: BudsCore.BudsState.gaming === true
            onToggled: root.setToggle("gaming", BudsCore.BudsState.gaming)
          }

          SettingRow {
            visible: BudsCore.BudsState.hasFeature("find")
            label: "Find My Earbuds"
            checked: BudsCore.BudsState.finding === true
            onToggled: root.setToggle("find", BudsCore.BudsState.finding)
          }
        }

        Column {
          width: parent.width
          spacing: Style.space(6)

          PanelSectionHeader {
            width: parent.width
            text: "Settings"
            foreground: root.contentForeground
            fontFamily: root.contentFontFamily
          }

          Text {
            text: "Pause the music"
            color: root.dimForeground
            font.family: root.contentFontFamily
            font.pixelSize: Style.font.caption
          }

          Row {
            spacing: Style.spacing.md
            Repeater {
              model: ["One out", "Both out", "Never"]
              Chip {
                text: modelData
                selected: modelData === root.earBehavior
                onClicked: root.updateSetting("earBehavior", modelData)
              }
            }
          }

          SettingRow {
            label: "Battery percent in the bar"
            checked: root.showBattery
            onToggled: root.updateSetting("showBattery", !root.showBattery)
          }
        }
      }
    }
  }
}

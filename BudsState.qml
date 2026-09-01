pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io

Item {
  id: root

  property bool connected: false
  property string address: ""
  property string deviceName: ""
  property string model: ""
  property string sku: ""
  property string mode: ""
  property var battery: ({})
  property var charging: ({})
  property var ear: null
  property var eq: null
  property var touchLock: null
  property var voiceDetect: null
  property var oneBud: null
  property var gaming: null
  property var ambientVolume: null
  property bool finding: false
  property var features: []
  property bool lowBatteryNotified: false
  property bool criticalBatteryNotified: false

  readonly property int lowBatteryPercent: 20
  readonly property int criticalBatteryPercent: 10
  readonly property int lowBatteryClearPercent: 30
  readonly property string helperCommand: Qt.resolvedUrl("bin/omabuds").toString().replace("file://", "")

  function hasFeature(name) {
    var list = root.features
    if (!list) return false
    return list.indexOf(name) >= 0
  }

  function send(key, value) {
    if (!watch.running) return
    watch.write(String(key) + " " + String(value) + "\n")
  }

  function applyStatus(text) {
    var data = {}
    try {
      data = JSON.parse(text)
    } catch (error) {
      connected = false
      checkLowBattery()
      return
    }
    connected = data.connected === true
    address = connected ? (data.address || "") : ""
    deviceName = connected ? (data.name || "") : ""
    model = connected ? (data.model || "") : ""
    sku = connected ? (data.sku || "") : ""
    mode = connected ? (data.mode || "") : ""
    battery = connected && data.battery ? data.battery : ({})
    charging = connected && data.charging ? data.charging : ({})
    ear = connected && data.ear ? data.ear : null
    eq = connected && data.eq !== undefined ? data.eq : null
    touchLock = connected && data.touch_lock !== undefined ? data.touch_lock : null
    voiceDetect = connected && data.voice_detect !== undefined ? data.voice_detect : null
    oneBud = connected && data.onebud !== undefined ? data.onebud : null
    gaming = connected && data.gaming !== undefined ? data.gaming : null
    ambientVolume = connected && data.ambient_volume !== undefined ? data.ambient_volume : null
    finding = connected && data.finding === true
    features = connected && data.features instanceof Array ? data.features : []
    checkLowBattery()
  }

  function levelFor(side, index) {
    var battery = root.battery || {}
    var charging = root.charging || {}
    var ear = root.ear
    var value = battery[side]
    if (value === undefined || value === null) return null
    if (charging[side] === true) return null
    if (ear && (ear[index] === "in_case" || ear[index] === "disconnected")) return null
    return value
  }

  function checkLowBattery() {
    if (!connected) {
      lowBatteryNotified = false
      criticalBatteryNotified = false
      return
    }
    var left = levelFor("left", 0)
    var right = levelFor("right", 1)
    var levels = []
    if (left !== null) levels.push({ label: "left", value: left })
    if (right !== null) levels.push({ label: "right", value: right })
    if (!levels.length) return

    var lowest = levels[0].value
    for (var i = 1; i < levels.length; i++)
      if (levels[i].value < lowest) lowest = levels[i].value

    if (lowest > lowBatteryClearPercent) {
      lowBatteryNotified = false
      criticalBatteryNotified = false
      return
    }
    if (lowest > lowBatteryPercent) return

    var parts = []
    for (var j = 0; j < levels.length; j++)
      if (levels[j].value <= lowBatteryPercent)
        parts.push(levels[j].label + " " + levels[j].value + "%")
    var body = parts.join(" · ")
    if (lowest <= criticalBatteryPercent && !criticalBatteryNotified) {
      criticalBatteryNotified = true
      lowBatteryNotified = true
      sendBatteryToast("critical", body)
      return
    }
    if (!lowBatteryNotified) {
      lowBatteryNotified = true
      sendBatteryToast("normal", body)
    }
  }

  function sendBatteryToast(urgency, body) {
    var omarchy = Quickshell.env("OMARCHY_PATH") || "/usr/share/omarchy"
    Quickshell.execDetached([
      omarchy + "/bin/omarchy-notification-send",
      "--app-name", "Galaxy Buds",
      "-u", urgency,
      "-g", "󰥰",
      "-t", "8000",
      "Galaxy Buds battery low",
      body
    ])
  }

  Process {
    id: watch
    command: [root.helperCommand, "watch"]
    running: true
    stdinEnabled: true
    stdout: SplitParser { onRead: function(line) { root.applyStatus(line) } }
    onExited: {
      root.connected = false
      root.checkLowBattery()
      restart.start()
    }
  }

  Timer {
    id: restart
    interval: 2000
    onTriggered: watch.running = true
  }
}

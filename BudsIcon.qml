import QtQuick

Item {
  id: root
  property int iconSize: 18
  property color color: "#ffffff"
  implicitWidth: iconSize
  implicitHeight: iconSize

  Canvas {
    id: canvas
    anchors.fill: parent
    antialiasing: true
    onPaint: {
      var ctx = getContext("2d")
      ctx.reset()
      var s = Math.min(width, height)
      if (s <= 0) return
      ctx.fillStyle = root.color
      ctx.translate((width - s) / 2, (height - s) / 2)

      // Bean earbuds: wide housing out at the top, eartip in at the bottom.
      function bud(flip) {
        ctx.save()
        ctx.translate(s * 0.5 + flip * s * 0.22, s * 0.50)
        ctx.rotate(flip * 0.62)
        ctx.scale(flip, 1)
        ctx.beginPath()
        ctx.moveTo(s * 0.01, -s * 0.26)
        ctx.bezierCurveTo(s * 0.20, -s * 0.26, s * 0.23, s * 0.02, s * 0.07, s * 0.24)
        ctx.bezierCurveTo(s * 0.02, s * 0.34, -s * 0.07, s * 0.28, -s * 0.08, s * 0.12)
        ctx.bezierCurveTo(-s * 0.14, -s * 0.08, -s * 0.12, -s * 0.24, s * 0.01, -s * 0.26)
        ctx.closePath()
        ctx.fill()
        ctx.restore()
      }

      bud(-1)
      bud(1)
    }
  }

  onColorChanged: canvas.requestPaint()
  onWidthChanged: canvas.requestPaint()
  onHeightChanged: canvas.requestPaint()
  onIconSizeChanged: canvas.requestPaint()
}

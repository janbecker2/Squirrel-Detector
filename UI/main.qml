import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQml
import QtCore

ApplicationWindow {
    id: window
    visible: true
    width: 800
    height: 700
    title: "Video Uploader"

    required property var python_bridge

    Connections {
        target: window.python_bridge
        function onDataReady(data) {
            statusText.text = "Done! Total frames: " + data.length
        }
        function onFrameData(frameNum, pixelCount) {
            chartCanvas.addPoint(frameNum, pixelCount)
        }
    }

    FileDialog {
        id: videoFileDialog
        title: "Select a Video"
        currentFolder: StandardPaths.writableLocation(StandardPaths.MoviesLocation)
        nameFilters: ["Video files (*.mp4 *.avi *.mkv)", "All files (*)"]
        onAccepted: {
            statusText.text = "Processing: " + videoFileDialog.selectedFile
            chartCanvas.reset()
            window.python_bridge.handle_video(videoFileDialog.selectedFile.toString())
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "#1e1e2e"

        Column {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 20

            Button {
                id: uploadButton
                text: "Upload Video"
                width: 200
                height: 50
                anchors.horizontalCenter: parent.horizontalCenter
                onClicked: videoFileDialog.open()

                contentItem: Text {
                    text: uploadButton.text
                    color: "white"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.bold: true
                }

                background: Rectangle {
                    color: uploadButton.down ? "#45475a" : "#89b4fa"
                    radius: 10
                }
            }

            Text {
                id: statusText
                text: "No video selected"
                color: "#a6adc8"
                font.pixelSize: 14
                width: parent.width
                wrapMode: Text.Wrap
                horizontalAlignment: Text.AlignHCenter
            }

            Rectangle {
                width: parent.width
                height: parent.height - 120
                color: "#313244"
                radius: 10

                Canvas {
                    id: chartCanvas
                    anchors.fill: parent
                    anchors.margins: 20

                    property var chartData: []
                    property int maxFrames: 0
                    property real currentMax: 0

                    function formatNumber(num) {
                        if (num >= 1000000) return (num / 1000000).toFixed(1) + "M"
                        if (num >= 1000) return (num / 1000).toFixed(1) + "K"
                        return Math.round(num).toString()
                    }

                    function reset() {
                        chartData = []
                        maxFrames = 0
                        currentMax = 0
                        requestPaint()
                    }

                    function addPoint(frameNum, value) {
                        // Push new value
                        chartData.push(value)

                        // Track total frames and running max
                        if (frameNum + 1 > maxFrames) maxFrames = frameNum + 1
                        if (value > currentMax) currentMax = value

                        requestPaint()
                    }

                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.reset()

                        // Placeholder
                        if (chartData.length === 0) {
                            ctx.fillStyle = "#a6adc8"
                            ctx.font = "16px sans-serif"
                            ctx.textAlign = "center"
                            ctx.fillText("Upload a video to see motion analysis", width / 2, height / 2)
                            return
                        }

                        var padLeft = 70
                        var padRight = 30
                        var padTop = 40
                        var padBottom = 40
                        var chartWidth = width - padLeft - padRight
                        var chartHeight = height - padTop - padBottom

                        // Nice Y-axis scaling based on running max
                        var niceMax = currentMax
                        if (niceMax > 0) {
                            var rawStep = currentMax / 5
                            var magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)))
                            var niceStep = Math.ceil(rawStep / magnitude) * magnitude
                            niceMax = niceStep * 5
                        } else {
                            niceMax = 100
                        }

                        // --- BACKGROUND ---
                        ctx.fillStyle = "#1e1e2e"
                        ctx.fillRect(0, 0, width, height)

                        // --- GRID LINES ---
                        ctx.strokeStyle = "#45475a"
                        ctx.lineWidth = 1
                        for (var g = 0; g <= 5; g++) {
                            var gy = padTop + (g / 5) * chartHeight
                            ctx.beginPath()
                            ctx.moveTo(padLeft, gy)
                            ctx.lineTo(padLeft + chartWidth, gy)
                            ctx.stroke()
                        }

                        ctx.strokeStyle = "#3a3a4a"
                        for (var vg = 0; vg <= 5; vg++) {
                            var gx = padLeft + (vg / 5) * chartWidth
                            ctx.beginPath()
                            ctx.moveTo(gx, padTop)
                            ctx.lineTo(gx, padTop + chartHeight)
                            ctx.stroke()
                        }

                        // --- AXES ---
                        ctx.strokeStyle = "#a6adc8"
                        ctx.lineWidth = 2
                        ctx.beginPath()
                        ctx.moveTo(padLeft, padTop)
                        ctx.lineTo(padLeft, padTop + chartHeight)
                        ctx.lineTo(padLeft + chartWidth, padTop + chartHeight)
                        ctx.stroke()

                        // --- TITLE ---
                        ctx.fillStyle = "#cdd6f4"
                        ctx.font = "bold 18px sans-serif"
                        ctx.textAlign = "center"
                        ctx.fillText("MOG2 Background Subtraction", width / 2, 22)

                        // --- PROGRESS TEXT ---
                        ctx.fillStyle = "#89b4fa"
                        ctx.font = "12px sans-serif"
                        ctx.textAlign = "right"
                        ctx.fillText("Frames processed: " + chartData.length, padLeft + chartWidth, padTop - 8)

                        // --- Y-AXIS LABEL ---
                        ctx.save()
                        ctx.translate(14, padTop + chartHeight / 2)
                        ctx.rotate(-Math.PI / 2)
                        ctx.font = "14px sans-serif"
                        ctx.fillStyle = "#a6adc8"
                        ctx.textAlign = "center"
                        ctx.fillText("Motion Pixels", 0, 0)
                        ctx.restore()

                        // --- X-AXIS LABEL ---
                        ctx.fillStyle = "#a6adc8"
                        ctx.font = "14px sans-serif"
                        ctx.textAlign = "center"
                        ctx.fillText("Frame Number", width / 2, height - 5)

                        // --- GRADIENT FILL ---
                        var gradient = ctx.createLinearGradient(0, padTop, 0, padTop + chartHeight)
                        gradient.addColorStop(0, "rgba(243, 139, 168, 0.25)")
                        gradient.addColorStop(1, "rgba(243, 139, 168, 0.0)")

                        ctx.fillStyle = gradient
                        ctx.beginPath()
                        ctx.moveTo(padLeft, padTop + chartHeight)

                        for (var fi = 0; fi < chartData.length; fi++) {
                            var fx = padLeft + (fi / Math.max(chartData.length - 1, 1)) * chartWidth
                            var fy = padTop + chartHeight - (chartData[fi] / niceMax) * chartHeight
                            ctx.lineTo(fx, fy)
                        }
                        ctx.lineTo(padLeft + (chartData.length - 1) / Math.max(chartData.length - 1, 1) * chartWidth, padTop + chartHeight)
                        ctx.closePath()
                        ctx.fill()

                        // --- DRAW LINE ---
                        ctx.strokeStyle = "#f38ba8"
                        ctx.lineWidth = 2
                        ctx.beginPath()

                        for (var i = 0; i < chartData.length; i++) {
                            var x = padLeft + (i / Math.max(chartData.length - 1, 1)) * chartWidth
                            var y = padTop + chartHeight - (chartData[i] / niceMax) * chartHeight

                            if (i === 0) {
                                ctx.moveTo(x, y)
                            } else {
                                ctx.lineTo(x, y)
                            }
                        }
                        ctx.stroke()

                        // --- DRAW LIVE DOT AT END ---
                        if (chartData.length > 0) {
                            var lastX = padLeft + ((chartData.length - 1) / Math.max(chartData.length - 1, 1)) * chartWidth
                            var lastY = padTop + chartHeight - (chartData[chartData.length - 1] / niceMax) * chartHeight

                            // Pulse glow
                            ctx.fillStyle = "rgba(243, 139, 168, 0.3)"
                            ctx.beginPath()
                            ctx.arc(lastX, lastY, 8, 0, 2 * Math.PI)
                            ctx.fill()

                            // Solid dot
                            ctx.fillStyle = "#f38ba8"
                            ctx.beginPath()
                            ctx.arc(lastX, lastY, 4, 0, 2 * Math.PI)
                            ctx.fill()
                        }

                        // --- Y-AXIS LABELS ---
                        ctx.fillStyle = "#a6adc8"
                        ctx.font = "11px sans-serif"
                        ctx.textAlign = "right"
                        for (var k = 0; k <= 5; k++) {
                            var value = niceMax * (5 - k) / 5
                            var labelY = padTop + (k / 5) * chartHeight
                            ctx.fillText(formatNumber(value), padLeft - 8, labelY + 4)
                        }

                        // --- X-AXIS LABELS ---
                        ctx.fillStyle = "#a6adc8"
                        ctx.textAlign = "center"
                        for (var m = 0; m <= 5; m++) {
                            var frameNum = Math.round((chartData.length - 1) * m / 5)
                            var labelX = padLeft + (m / 5) * chartWidth
                            ctx.fillText(frameNum.toString(), labelX, padTop + chartHeight + 18)
                        }

                        // --- LEGEND ---
                        ctx.fillStyle = "#252637"
                        ctx.fillRect(padLeft + chartWidth - 90, padTop + 8, 80, 24)
                        ctx.strokeStyle = "#45475a"
                        ctx.lineWidth = 1
                        ctx.strokeRect(padLeft + chartWidth - 90, padTop + 8, 80, 24)
                        ctx.fillStyle = "#f38ba8"
                        ctx.fillRect(padLeft + chartWidth - 82, padTop + 19, 24, 3)
                        ctx.fillStyle = "#cdd6f4"
                        ctx.font = "12px sans-serif"
                        ctx.textAlign = "left"
                        ctx.fillText("MOG2", padLeft + chartWidth - 53, padTop + 24)
                    }
                }
            }
        }
    }
}
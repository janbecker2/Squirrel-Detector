import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQml
import QtCore

ApplicationWindow {
    id: window
    visible: true
    width: 1000
    height: 700
    title: "Squirrel Video Viewer"

    Rectangle {
        id: loadingOverlay
        visible: false
        width: parent.width - 40
        height: 400
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: 20
        color: "#cc1e1e2e"
        radius: 8

        Column {
            anchors.centerIn: parent
            spacing: 16

            Canvas {
                id: spinnerCanvas
                width: 56
                height: 56
                anchors.horizontalCenter: parent.horizontalCenter

                property real angle: 0
                onAngleChanged: requestPaint()

                NumberAnimation on angle {
                    from: 0
                    to: Math.PI * 2
                    duration: 900
                    loops: Animation.Infinite
                    running: loadingOverlay.visible
                }

                onPaint: {
                    var ctx = getContext("2d")
                    ctx.reset()
                    var cx = width / 2
                    var cy = height / 2
                    var r = 22

                    ctx.strokeStyle = "#313244"
                    ctx.lineWidth = 5
                    ctx.lineCap = "round"
                    ctx.beginPath()
                    ctx.arc(cx, cy, r, 0, Math.PI * 2)
                    ctx.stroke()

                    ctx.strokeStyle = "#89b4fa"
                    ctx.lineWidth = 5
                    ctx.lineCap = "round"
                    ctx.beginPath()
                    ctx.arc(cx, cy, r, angle - 0.3, angle + Math.PI * 1.2)
                    ctx.stroke()
                }
            }

            Text {
                text: "Analysing video..."
                color: "#cdd6f4"
                font.pixelSize: 16
                font.bold: true
                anchors.horizontalCenter: parent.horizontalCenter
            }
        }
    }

    Text {
        id: statusText
        text: "No video loaded"
        anchors.top: loadingOverlay.bottom
        anchors.topMargin: 10
        anchors.horizontalCenter: parent.horizontalCenter
        font.pixelSize: 14
        color: "#a6adc8"
    }

    FileDialog {
        id: videoFileDialog
        title: "Select a Video"
        currentFolder: StandardPaths.writableLocation(StandardPaths.MoviesLocation)
        nameFilters: ["Video files (*.mp4 *.avi *.mkv)", "All files (*)"]
        onAccepted: {
            uploadButton.loading = true
            loadingOverlay.visible = true
            statusText.text = "Loading: " + selectedFile
            chartCanvas.reset()
            python_bridge.load_video(selectedFile.toString())
        }
    }

    Button {
        id: uploadButton
        width: 200
        height: 50
        anchors.top: statusText.bottom
        anchors.topMargin: 10
        anchors.horizontalCenter: parent.horizontalCenter

        property bool loading: false
        text: loading ? "Loading..." : "Upload Video"

        onClicked: videoFileDialog.open()

        contentItem: Item {
            anchors.fill: parent

            Row {
                anchors.centerIn: parent
                spacing: 10

                Text {
                    text: uploadButton.text
                    color: "white"
                    font.bold: true
                    anchors.verticalCenter: parent.verticalCenter
                }

                Rectangle {
                    visible: uploadButton.loading
                    width: 16
                    height: 16
                    color: "transparent"
                    border.width: 2
                    border.color: "white"
                    radius: 8
                    anchors.verticalCenter: parent.verticalCenter

                    RotationAnimator on rotation {
                        from: 0
                        to: 360
                        duration: 800
                        loops: Animation.Infinite
                        running: uploadButton.loading
                    }
                }
            }
        }

        background: Rectangle {
            color: uploadButton.down ? "#45475a" : "#89b4fa"
            radius: 10
        }

        Connections {
            target: python_bridge
            function onMaxFrameChanged(maxFrame) {
                uploadButton.loading = false
            }
        }
    }

    Image {
        id: videoFrame
        width: parent.width - 40
        height: 400
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: 20
        fillMode: Image.PreserveAspectFit
        source: ""  // updated from Python
    }


    Slider {
        id: frameSlider
        from: 0
        to: 0  // will be set dynamically
        stepSize: 1
        anchors.top: uploadButton.bottom
        anchors.topMargin: 20
        anchors.horizontalCenter: parent.horizontalCenter
        width: parent.width - 80

        onValueChanged: {
            python_bridge.request_frame(value)
            chartCanvas.requestPaint()
        }
    }

    Rectangle {
        anchors.top: frameSlider.bottom
        anchors.topMargin: 20
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        color: "#313244"
        radius: 10
        anchors.margins: 20

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
                chartData.push(value)
                if (frameNum + 1 > maxFrames) maxFrames = frameNum + 1
                if (value > currentMax) currentMax = value
                requestPaint()
            }

            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()

                var padLeft = 70
                var padRight = 30
                var padTop = 40
                var padBottom = 40
                var chartWidth = width - padLeft - padRight
                var chartHeight = height - padTop - padBottom

                ctx.fillStyle = "#1e1e2e"
                ctx.fillRect(0, 0, width, height)

                if (chartData.length === 0) {
                    ctx.fillStyle = "#a6adc8"
                    ctx.font = "16px sans-serif"
                    ctx.textAlign = "center"
                    ctx.fillText("Upload a video to see motion analysis", width / 2, height / 2)
                    return
                }

                var niceMax = currentMax
                if (niceMax > 0) {
                    var rawStep = currentMax / 5
                    var magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)))
                    var niceStep = Math.ceil(rawStep / magnitude) * magnitude
                    niceMax = niceStep * 5
                } else {
                    niceMax = 100
                }

                // horizontal grid
                ctx.strokeStyle = "#45475a"
                ctx.lineWidth = 1
                for (var g = 0; g <= 5; g++) {
                    var gy = padTop + (g / 5) * chartHeight
                    ctx.beginPath()
                    ctx.moveTo(padLeft, gy)
                    ctx.lineTo(padLeft + chartWidth, gy)
                    ctx.stroke()
                }

                // vertical grid
                ctx.strokeStyle = "#3a3a4a"
                for (var vg = 0; vg <= 5; vg++) {
                    var gx = padLeft + (vg / 5) * chartWidth
                    ctx.beginPath()
                    ctx.moveTo(gx, padTop)
                    ctx.lineTo(gx, padTop + chartHeight)
                    ctx.stroke()
                }

                // axes
                ctx.strokeStyle = "#a6adc8"
                ctx.lineWidth = 2
                ctx.beginPath()
                ctx.moveTo(padLeft, padTop)
                ctx.lineTo(padLeft, padTop + chartHeight)
                ctx.lineTo(padLeft + chartWidth, padTop + chartHeight)
                ctx.stroke()

                // y-axis labels
                ctx.fillStyle = "#a6adc8"
                ctx.font = "11px sans-serif"
                ctx.textAlign = "right"
                for (var yi = 0; yi <= 5; yi++) {
                    var yVal = niceMax * (1 - yi / 5)
                    var yPos = padTop + (yi / 5) * chartHeight
                    ctx.fillText(formatNumber(yVal), padLeft - 8, yPos + 4)
                }

                // x-axis labels
                ctx.textAlign = "center"
                var xLabelCount = Math.min(6, chartData.length)
                for (var xi = 0; xi <= xLabelCount; xi++) {
                    var xFrame = Math.round((xi / xLabelCount) * (maxFrames - 1))
                    var xPos = padLeft + (xFrame / Math.max(maxFrames - 1, 1)) * chartWidth
                    ctx.fillText(xFrame.toString(), xPos, padTop + chartHeight + 18)
                }

                // chart line
                ctx.strokeStyle = "#89b4fa"
                ctx.lineWidth = 2
                ctx.beginPath()
                for (var i = 0; i < chartData.length; i++) {
                    var px = padLeft + (i / Math.max(maxFrames - 1, 1)) * chartWidth
                    var py = padTop + (1 - chartData[i] / niceMax) * chartHeight
                    if (i === 0) ctx.moveTo(px, py)
                    else ctx.lineTo(px, py)
                }
                ctx.stroke()

                // current frame indicator
                var currentFrame = Math.round(frameSlider.value)
                if (currentFrame >= 0 && currentFrame < chartData.length) {
                    var cx = padLeft + (currentFrame / Math.max(maxFrames - 1, 1)) * chartWidth
                    ctx.strokeStyle = "#f38ba8"
                    ctx.lineWidth = 2
                    ctx.beginPath()
                    ctx.moveTo(cx, padTop)
                    ctx.lineTo(cx, padTop + chartHeight)
                    ctx.stroke()
                }

                // titles
                ctx.fillStyle = "#cdd6f4"
                ctx.font = "bold 18px sans-serif"
                ctx.textAlign = "center"
                ctx.fillText("Motion Analysis", width / 2, 22)

                ctx.fillStyle = "#a6adc8"
                ctx.font = "14px sans-serif"
                ctx.textAlign = "center"
                ctx.fillText("Frame Number", width / 2, height - 5)

                ctx.save()
                ctx.translate(14, padTop + chartHeight / 2)
                ctx.rotate(-Math.PI / 2)
                ctx.font = "14px sans-serif"
                ctx.fillStyle = "#a6adc8"
                ctx.textAlign = "center"
                ctx.fillText("Motion Pixels", 0, 0)
                ctx.restore()
            }
        }
    }

    Connections {
        target: python_bridge

        function onFrameReady(filePath) {
            videoFrame.source = "file:///" + filePath
        }

        function onMaxFrameChanged(maxFrame) {
            frameSlider.to = maxFrame
            uploadButton.loading = false
            loadingOverlay.visible = false
        }
    }

}

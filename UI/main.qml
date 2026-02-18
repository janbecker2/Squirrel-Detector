import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQml
import QtCore

ApplicationWindow {
    id: window
    visible: true
    width: 1000
    height: 800
    title: "Squirrel Video Viewer"
    color: "#1e1e2e"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 15

        // =========================
        // 1. VIDEO DISPLAY AREA
        // =========================
        Rectangle {
            id: videoContainer
            Layout.fillWidth: true
            Layout.preferredHeight: 450
            color: "#181825"
            radius: 12
            clip: true

            Image {
                id: videoFrame
                anchors.fill: parent
                fillMode: Image.PreserveAspectFit
                source: ""
                // Use cache: false to ensure the image updates when the file changes
                cache: false 
                opacity: uploadButton.loading ? 0.3 : 1.0
                Behavior on opacity {
                    NumberAnimation { duration: 250 }
                }

                Text {
                    visible: parent.source == "" && !uploadButton.loading
                    text: "No Video Loaded"
                    anchors.centerIn: parent
                    color: "#585b70"
                    font.pixelSize: 20
                }
            }

            // =========================
            // Loading spinner overlay
            // =========================
            Item {
                anchors.fill: parent
                visible: uploadButton.loading

                Canvas {
                    id: loadingCanvas
                    anchors.centerIn: parent
                    width: 60
                    height: 60
                    property real angle: 0
                    
                    Timer {
                        running: uploadButton.loading
                        repeat: true
                        interval: 16
                        onTriggered: {
                            loadingCanvas.angle += 0.15
                            loadingCanvas.requestPaint()
                        }
                    }

                    onPaint: {
                        var ctx = getContext("2d");
                        ctx.reset();
                        ctx.translate(width / 2, height / 2);
                        ctx.rotate(loadingCanvas.angle);
                        
                        ctx.beginPath();
                        ctx.lineWidth = 4;
                        ctx.strokeStyle = "#89b4fa";
                        ctx.lineCap = "round";
                        
                        // FIX: Changed # to // for syntax correctness
                        // Draw a 270-degree arc
                        ctx.arc(0, 0, 25, 0, Math.PI * 1.5); 
                        ctx.stroke();
                    }
                }

                Text {
                    text: "Analyzing Squirrel..."
                    anchors.top: loadingCanvas.bottom
                    anchors.topMargin: 20
                    anchors.horizontalCenter: parent.horizontalCenter
                    color: "#89b4fa"
                    font.pixelSize: 14
                    font.bold: true
                }
            }
        }

        // =========================
        // 2. PLAYBACK CONTROLS
        // =========================
        RowLayout {
            Layout.fillWidth: true
            spacing: 15

            Button {
                id: uploadButton
                Layout.preferredWidth: 160
                Layout.preferredHeight: 45
                property bool loading: false
                text: loading ? "Working..." : "Open Video"
                enabled: !loading

                background: Rectangle {
                    color: uploadButton.loading ? "#45475a" : (uploadButton.down ? "#74c7ec" : "#89b4fa")
                    radius: 8
                }

                contentItem: Text {
                    text: uploadButton.text
                    color: "white"
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                onClicked: videoFileDialog.open()
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "Frame: " + Math.round(frameSlider.value)
                        color: "#cdd6f4"
                        font.bold: true
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: "Total: " + frameSlider.to
                        color: "#a6adc8"
                        font.pixelSize: 12
                    }
                }

                Slider {
                    id: frameSlider
                    Layout.fillWidth: true
                    from: 0
                    to: 1
                    stepSize: 1
                    enabled: !uploadButton.loading
                    onMoved: if (typeof python_bridge !== "undefined")
                        python_bridge.request_frame(value)
                }
            }
        }

        // =========================
        // 3. CHART AREA
        // =========================
        Rectangle {
            id: chartContainer
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#313244"
            radius: 12
            border.color: "#45475a"

            Canvas {
                id: chartCanvas
                anchors.fill: parent
                anchors.margins: 20
                property var chartData: []
                property int maxFrames: 1
                property real currentMax: 1.0

                onPaint: {
                    var ctx = getContext("2d");
                    ctx.clearRect(0, 0, width, height);
                    if (chartData.length === 0) {
                        ctx.fillStyle = "#6c7086";
                        ctx.font = "14px sans-serif";
                        ctx.textAlign = "center";
                        ctx.fillText("Motion data will appear here after analysis", width / 2, height / 2);
                        return;
                    }
                    ctx.strokeStyle = "#f38ba8";
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    for (var i = 0; i < chartData.length; i++) {
                        var x = (i / maxFrames) * width;
                        var y = height - (chartData[i] / currentMax * height);
                        if (i === 0) ctx.moveTo(x, y);
                        else ctx.lineTo(x, y);
                    }
                    ctx.stroke();
                }
            }
        }
    }

    FileDialog {
        id: videoFileDialog
        onAccepted: {
            uploadButton.loading = true;
            chartCanvas.chartData = [];
            chartCanvas.requestPaint();
            if (typeof python_bridge !== "undefined")
                python_bridge.load_video(selectedFile);
        }
    }

    Connections {
        target: python_bridge
        ignoreUnknownSignals: true
        function onFrameReady(path) {
            // Added Date.now() to the URL to force QML to reload the image from disk
            videoFrame.source = "file:///" + path + "?t=" + Date.now();
        }
        function onMaxFrameChanged(max) {
            frameSlider.to = max;
            chartCanvas.maxFrames = max;
            uploadButton.loading = false;
        }
        function onMotionDataReady(data, val) {
            chartCanvas.chartData = data;
            chartCanvas.currentMax = val;
            chartCanvas.requestPaint();
        }
    }
}
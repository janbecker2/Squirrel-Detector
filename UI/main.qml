import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQml
import QtCore

ApplicationWindow {
    id: window
    visible: true
    width: 1100
    height: 900
    title: "Squirrel Video Viewer"
    color: "#1e1e2e"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 15

        // ==========================================
        // 1. VIDEO DISPLAY AREA (Takes 50% height)
        // ==========================================
        Rectangle {
            id: videoContainer
            Layout.fillWidth: true
            Layout.preferredHeight: parent.height * 0.5 
            color: "#181825"
            radius: 12
            clip: true

            Image {
                id: videoFrame
                anchors.fill: parent
                fillMode: Image.PreserveAspectFit
                source: "image://frames/current" 
                cache: false 
                // Only show image once video is actually loaded to avoid placeholder "rectangles"
                visible: frameSlider.to > 1 
                opacity: uploadButton.loading || propagateButton.loading ? 0.3 : 1.0
                Behavior on opacity { NumberAnimation { duration: 250 } }
            }

            Text {
                visible: frameSlider.to <= 1 && !uploadButton.loading
                text: "No Video Loaded"
                anchors.centerIn: parent
                color: "#585b70"
                font.pixelSize: 20
            }

            // Spinner Overlay
            Item {
                anchors.fill: parent
                visible: uploadButton.loading || propagateButton.loading
                Canvas {
                    id: loadingCanvas
                    anchors.centerIn: parent
                    width: 60; height: 60
                    property real angle: 0
                    Timer {
                        running: uploadButton.loading || propagateButton.loading
                        repeat: true; interval: 16
                        onTriggered: { loadingCanvas.angle += 0.15; loadingCanvas.requestPaint() }
                    }
                    onPaint: {
                        var ctx = getContext("2d");
                        ctx.reset();
                        ctx.translate(width / 2, height / 2);
                        ctx.rotate(loadingCanvas.angle);
                        ctx.beginPath();
                        ctx.lineWidth = 4; ctx.strokeStyle = "#89b4fa"; ctx.lineCap = "round";
                        ctx.arc(0, 0, 25, 0, Math.PI * 1.5); ctx.stroke();
                    }
                }
            }
        }

        // ==========================================
        // 2. CONTROLS ROW (Buttons LEFT, Slider RIGHT)
        // ==========================================
        RowLayout {
            Layout.fillWidth: true
            spacing: 20

            // Left Side: Action Buttons Section
            RowLayout {
                spacing: 10
                Layout.alignment: Qt.AlignBottom 

                Button {
                    id: uploadButton
                    Layout.preferredWidth: 160
                    Layout.preferredHeight: 45
                    property bool loading: false
                    text: loading ? "Working..." : "Open Video"
                    enabled: !loading && !propagateButton.loading
                    background: Rectangle {
                        color: uploadButton.loading ? "#45475a" : (uploadButton.down ? "#74c7ec" : "#89b4fa")
                        radius: 8
                    }
                    contentItem: Text { 
                        text: uploadButton.text; color: "white"; font.bold: true; 
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter 
                    }
                    onClicked: videoFileDialog.open()
                }

                Button {
                    id: propagateButton
                    Layout.preferredWidth: 160
                    Layout.preferredHeight: 45
                    property bool loading: false
                    text: loading ? "Working..." : "Propagate Video"
                    // Only enabled if a video is loaded (Total frames > 1)
                    enabled: frameSlider.to > 1 && !loading && !uploadButton.loading
                    background: Rectangle {
                        color: propagateButton.enabled ? (propagateButton.down ? "#f5c2e7" : "#cba6f7") : "#313244"
                        radius: 8
                        border.color: propagateButton.enabled ? "transparent" : "#45475a"
                    }
                    contentItem: Text { 
                        text: propagateButton.text; color: propagateButton.enabled ? "white" : "#585b70"
                        font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter 
                    }
                    onClicked: {
                        propagateButton.loading = true
                        if (typeof python_bridge !== "undefined")
                            python_bridge.propagate_video()
                    }
                }
            }

            // Right Side: Slider Section
            ColumnLayout {
                Layout.fillWidth: true 
                spacing: 2
                RowLayout {
                    Text { text: "Frame: " + Math.round(frameSlider.value); color: "#cdd6f4"; font.bold: true }
                    Item { Layout.fillWidth: true }
                    Text { text: "Total: " + frameSlider.to; color: "#a6adc8"; font.pixelSize: 12 }
                }
                Slider {
                    id: frameSlider
                    Layout.fillWidth: true
                    from: 0; to: 1; stepSize: 1
                    // Only enabled if a video is loaded
                    enabled: to > 1 && !uploadButton.loading && !propagateButton.loading
                    onMoved: if (typeof python_bridge !== "undefined") python_bridge.request_frame(value)
                }
            }
        }

        // ==========================================
        // 3. CHART AREA
        // ==========================================
        Rectangle {
            id: chartContainer
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#313244"
            radius: 12
            border.color: "#45475a"

            Image {
                id: chartImage
                anchors.fill: parent
                anchors.margins: 10
                fillMode: Image.PreserveAspectFit
                source: ""
                Text {
                    anchors.centerIn: parent
                    text: "Chart will appear after propagation"
                    color: "#585b70"
                    font.pixelSize: 20
                    visible: chartImage.source == ""
                }
            }
        }

        // =========================
        // 4. DOWNLOAD CHART BUTTON
        // =========================
        Button {
            id: downloadChartButton
            Layout.fillWidth: true
            Layout.preferredHeight: 45
            text: "Download Chart"
            enabled: chartImage.source != ""
            background: Rectangle {
                color: downloadChartButton.enabled ? (downloadChartButton.down ? "#45475a" : "#585b70") : "#2a2b3d"
                radius: 8
                border.color: "#45475a"
            }
            contentItem: Text {
                text: downloadChartButton.text
                color: downloadChartButton.enabled ? "white" : "#45475a"
                font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
            }
            onClicked: {
                console.log("Download Chart clicked")
            }
        }
    }

    FileDialog {
        id: videoFileDialog
        onAccepted: {
            uploadButton.loading = true;
            chartImage.source = "";
            if (typeof python_bridge !== "undefined")
                python_bridge.load_video(selectedFile);
        }
    }

    Connections {
        target: python_bridge
        ignoreUnknownSignals: true
        function onFrameUpdated() {
            var oldSource = videoFrame.source;
            videoFrame.source = ""; 
            videoFrame.source = oldSource;
        }
        function onMaxFrameChanged(max) {
            frameSlider.to = max;
            uploadButton.loading = false;
        }
        function onPropagationFinished() {
            propagateButton.loading = false
            python_bridge.request_frame(frameSlider.value)
        }
        function onChartImageUpdated(imgData) {
            chartImage.source = imgData
        }
    }
}
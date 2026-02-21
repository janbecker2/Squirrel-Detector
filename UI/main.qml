import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQml

ApplicationWindow {
    id: window
    visible: true
    width: 1100
    height: 980
    title: "Squirrel Video Viewer"
    color: "#1e1e2e"
    property bool isReset: false


    // Error popup 
    Popup {
        id: errorPopup
        anchors.centerIn: parent
        width: 400
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        property string errorText: ""

        background: Rectangle {
            color: "#1e1e2e" // Main background color
            border.color: "#f38ba8" // Red accent for errors
            border.width: 2
            radius: 12
        }

        contentItem: ColumnLayout {
            spacing: 20
            anchors.margins: 20

            RowLayout {
                spacing: 10
                Text {
                    text: "⚠"
                    color: "#ff0000"
                    font.pixelSize: 24
                    font.bold: true
                }
                Text {
                    text: "ERROR"
                    color: "#cdd6f4"
                    font.pixelSize: 20
                    font.bold: true
                }
            }

            Text {
                text: errorPopup.errorText
                color: "#a6adc8"
                font.pixelSize: 14
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Button {
                text: "Dismiss"
                Layout.alignment: Qt.AlignRight
                Layout.preferredWidth: 100
                Layout.preferredHeight: 35
                
                background: Rectangle {
                    color: parent.hovered ? "#313244" : "#181825"
                    radius: 6
                    border.color: "#45475a"
                }
                contentItem: Text {
                    text: parent.text
                    color: "#cdd6f4"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.bold: true
                }
                onClicked: errorPopup.close()
            }
        }
    }

    property string propagationStatus: "Processing Video..."


    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 15

        // Header Row 
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 150 
            Layout.topMargin: -20     
            Layout.bottomMargin: -20 
            Layout.leftMargin: -20       
            spacing: 15

            Image {
                source: "assets/logo_transparent.png"
                Layout.preferredWidth: 150
                Layout.preferredHeight: 150
                fillMode: Image.PreserveAspectFit
                smooth: true
                horizontalAlignment: Image.AlignLeft
                verticalAlignment: Image.AlignVCenter 
            }

            ColumnLayout {
                spacing: 0
                Layout.alignment: Qt.AlignVCenter
                Layout.leftMargin: -25 

                Text {
                    text: "Squirrel Detector"
                    color: "#f5e0dc" 
                    font.pixelSize: 36
                    font.bold: true
                }
                
            }

            Item { Layout.fillWidth: true } 

            Button {
                id: helpButton
                Layout.preferredWidth: 36
                Layout.preferredHeight: 36
                Layout.alignment: Qt.AlignVCenter
                
                background: Rectangle {
                    color: helpButton.hovered ? "#313244" : "transparent"
                    radius: 18
                    border.color: helpButton.hovered ? "#89b4fa" : "transparent"
                    border.width: 1
                }

                contentItem: Text {
                    text: "?"
                    color: helpButton.hovered ? "#89b4fa" : "#585b70"
                    font.pixelSize: 18
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                ToolTip.visible: hovered
                ToolTip.text: "Open Documentation"

                onClicked: {
                    if (typeof python_bridge !== "undefined")
                        python_bridge.open_help_link();
                }
            }
        }

        // Video display Area 
        Rectangle {
            id: videoContainer
            Layout.fillWidth: true
            Layout.preferredHeight: parent.height * 0.45
            color: "#181825"
            radius: 12
            clip: true

            Image {
                id: videoFrame
                anchors.fill: parent
                fillMode: Image.PreserveAspectFit
                source: "image://frames/current"
                cache: false
                visible: !window.isReset && frameSlider.to > 1
                opacity: uploadButton.loading || propagateButton.loading ? 0.3 : 1.0
                Behavior on opacity {
                    NumberAnimation {
                        duration: 250
                    }
                }
            }

            Text {
                visible: frameSlider.to <= 1 && !uploadButton.loading
                text: "No Video Loaded"
                anchors.centerIn: parent
                color: "#585b70"
                font.pixelSize: 24
            }

            // Loading Overlay
            Item {
                anchors.fill: parent
                visible: uploadButton.loading || propagateButton.loading

                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 20

                    Canvas {
                        id: loadingCanvas
                        Layout.alignment: Qt.AlignHCenter
                        width: 60
                        height: 60
                        property real angle: 0
                        Timer {
                            running: uploadButton.loading || propagateButton.loading
                            repeat: true
                            interval: 16
                            onTriggered: {
                                loadingCanvas.angle += 0.15;
                                loadingCanvas.requestPaint();
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
                            ctx.arc(0, 0, 25, 0, Math.PI * 1.5);
                            ctx.stroke();
                        }
                    }

                    Text {
                        id: statusText
                        text: propagateButton.loading ? window.propagationStatus : "Loading Video..."
                        Layout.alignment: Qt.AlignHCenter
                        color: "#89b4fa"
                        font.pixelSize: 14
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }
        }

        // Controls/Buttons Row
        RowLayout {
            Layout.fillWidth: true
            spacing: 20

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
                        text: uploadButton.text
                        color: "white"
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    onClicked: videoFileDialog.open()
                }

                Button {
                    id: propagateButton
                    Layout.preferredWidth: 160
                    Layout.preferredHeight: 45
                    property bool loading: false
                    text: loading ? "Working..." : "Propagate Video"
                    enabled: frameSlider.to > 1 && !loading && !uploadButton.loading
                    background: Rectangle {
                        color: propagateButton.enabled ? (propagateButton.down ? "#f5c2e7" : "#cba6f7") : "#313244"
                        radius: 8
                        border.color: propagateButton.enabled ? "transparent" : "#45475a"
                    }
                    contentItem: Text {
                        text: propagateButton.text
                        color: propagateButton.enabled ? "white" : "#585b70"
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    onClicked: {
                        propagateButton.loading = true;
                        if (typeof python_bridge !== "undefined")
                            python_bridge.propagate_video();
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                RowLayout {
                    Text {
                        text: "Frame: " + Math.round(frameSlider.value)
                        color: "#cdd6f4"
                        font.bold: true
                    }
                    Item {
                        Layout.fillWidth: true
                    }
                    Text {
                        text: "Total: " + (frameSlider.to > 1 ? frameSlider.to : 0)
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
                    enabled: to > 1 && !uploadButton.loading && !propagateButton.loading
                    onMoved: if (typeof python_bridge !== "undefined")
                        python_bridge.request_frame(value)
                }
            }
        }

        // graph display area
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
                    font.pixelSize: 18
                    text: "Chart will appear after propagation"
                    color: "#585b70"
                    visible: chartImage.source == ""
                }
            }
        }

        // Download Buttons Row
        RowLayout {
            Layout.fillWidth: true
            spacing: 15
            enabled: chartImage.source != ""

            Button {
                id: downloadCsvButton
                Layout.fillWidth: true
                Layout.preferredHeight: 45
                text: "Download Graph Data (CSV)"
                background: Rectangle {
                    color: parent.enabled ? (parent.down ? "#45475a" : "#89b4fa") : "#2a2b3d"
                    radius: 8
                    border.color: "#45475a"
                }
                contentItem: Text {
                    text: parent.text
                    color: parent.enabled ? "white" : "#45475a"
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: csvSaveDialog.open()
            }

            Button {
                id: downloadVideoButton
                Layout.fillWidth: true
                Layout.preferredHeight: 45
                text: "Download Video with Mask Overlay"
                background: Rectangle {
                    color: parent.enabled ? (parent.down ? "#45475a" : "#89b4fa") : "#2a2b3d"
                    radius: 8
                    border.color: "#45475a"
                }
                contentItem: Text {
                    text: parent.text
                    color: parent.enabled ? "white" : "#45475a"
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: videoSaveDialog.open()
            }

            Button {
                id: downloadMaskDataButton
                Layout.fillWidth: true
                Layout.preferredHeight: 45
                text: "Download Mask BBoxes (CSV)" // Updated label for bounding box export
                background: Rectangle {
                    color: parent.enabled ? (parent.down ? "#45475a" : "#89b4fa") : "#2a2b3d"
                    radius: 8
                    border.color: "#45475a"
                }
                contentItem: Text {
                    text: parent.text
                    color: parent.enabled ? "white" : "#45475a"
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: maskSaveDialog.open()
            }
        }
    }

    // Dialogs to handlle file selection and downloads
    FileDialog {
        id: videoFileDialog
        title: "Select Video"
        nameFilters: ["Video files (*.mp4 *.avi *.mov *.mkv)"]
        onAccepted: {
            window.isReset = false;
            uploadButton.loading = true;
            chartImage.source = "";
            if (typeof python_bridge !== "undefined")
                python_bridge.load_video(selectedFile);
        }
    }

    FileDialog {
        id: csvSaveDialog
        title: "Save Graph Data as CSV"
        fileMode: FileDialog.SaveFile
        nameFilters: ["CSV File (*.csv)"]
        currentFile: "squirrel_mask_data.csv"
        onAccepted: {
            if (typeof python_bridge !== "undefined")
                python_bridge.download_csv(selectedFile);
        }
    }

    FileDialog {
        id: videoSaveDialog
        title: "Save Processed Video"
        fileMode: FileDialog.SaveFile
        nameFilters: ["MP4 Video (*.mp4)"]
        currentFile: "squirrel_propagation.mp4"
        onAccepted: {
            if (typeof python_bridge !== "undefined")
                python_bridge.download_video(selectedFile);
        }
    }

    FileDialog {
        id: maskSaveDialog
        title: "Save BBox Training Data as CSV"
        fileMode: FileDialog.SaveFile
        nameFilters: ["CSV File (*.csv)"]
        currentFile: "squirrel_training_bbox.csv"
        onAccepted: {
            if (typeof python_bridge !== "undefined")
                python_bridge.download_training_csv(selectedFile);
        }
    }

    // Connections to handle signals from the Python backend
    Connections {
        target: python_bridge
        ignoreUnknownSignals: true
        function onFrameUpdated() {
            var old = videoFrame.source;
            videoFrame.source = "";
            videoFrame.source = old;
        }
        function onStatusUpdated(status) {
            window.propagationStatus = status;
        }
        function onMaxFrameChanged(max) {
            window.isReset = false;
            frameSlider.to = max;
            uploadButton.loading = false;
            videoFrame.source = "";
            videoFrame.source = "image://frames/current?t=" + Date.now();
            python_bridge.request_frame(0);
        }
        function onPropagationFinished() {
            propagateButton.loading = false;
            window.propagationStatus = "Processing Video...";
            python_bridge.request_frame(frameSlider.value);
        }
        function onChartImageUpdated(imgData) {
            chartImage.source = imgData;
        }
        function resetUI(message, popup = true) {
            window.isReset = true; 

            uploadButton.loading = false;
            propagateButton.loading = false;

            frameSlider.to = 1; 
            frameSlider.value = 0;

            videoFrame.source = "";
            chartImage.source = "";   
            if(popup){
                errorPopup.errorText = message;
                errorPopup.open();
            }
        }
        function onVideo_load_failed(errorMessage) {
            resetUI(errorMessage);
        }
    }
}
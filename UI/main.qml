import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs // Needed for FileDialog

ApplicationWindow {
    id: window
    visible: true
    width: 600
    height: 500
    title: "Video Uploader"

    // 1. The "Magic" File Picker
    FileDialog {
        id: videoFileDialog
        title: "Select a Video to Upload"
        currentFolder: StandardPaths.writableLocation(StandardPaths.MoviesLocation)
        nameFilters: ["Video files (*.mp4 *.avi *.mkv)", "All files (*)"]
        
        onAccepted: {
            // This runs when you click "Open"
            statusText.text = "Selected: " + videoFileDialog.selectedFile
            console.log("File chosen: " + selectedFile)
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "#1e1e2e" // Dark "Cyberpunk" background

        Column {
            anchors.centerIn: parent
            spacing: 20

            // Upload Button
            Button {
                text: "Upload Video"
                width: 200
                height: 50
                anchors.horizontalCenter: parent.horizontalCenter
                
                onClicked: videoFileDialog.open()
                
                contentItem: Text {
                    text: parent.text
                    color: "white"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.bold: true
                }

                background: Rectangle {
                    color: parent.down ? "#45475a" : "#89b4fa"
                    radius: 10
                }
            }

            // Status Text
            Text {
                id: statusText
                text: "No video selected"
                color: "#a6adc8"
                font.pixelSize: 14
                width: 400
                wrapMode: Text.Wrap
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }
}
import sys
from pathlib import Path
from PySide6.QtCore import QObject, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

# This class handles the communication
class Bridge(QObject):
    @Slot(str)
    def handle_video(self, file_path):
        # Clean up the file path (removes 'file:///' prefix)
        clean_path = file_path.replace("file:///", "")
        if sys.platform == "win32":
            clean_path = clean_path.replace("/", "\\")
            
        print(f"✅ Python received the video: {clean_path}")
        # You can now process the video, upload it to a server, etc.

if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    # Create the bridge and expose it to QML
    bridge = Bridge()
    engine.rootContext().setContextProperty("python_bridge", bridge)

    engine.load('./UI/main.qml')

    if not engine.rootObjects():
        sys.exit(-1)
    sys.exit(app.exec())
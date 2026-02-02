import sys
from pathlib import Path
# Added Signal to the import line below
from PySide6.QtCore import QObject, Slot, Signal 
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from videoAnalyzer import VideoAnalyzer

class Bridge(QObject):
    dataReady = Signal(list)       # Keep this for the final full dataset
    frameData = Signal(int, int)   # New: emits (frame_number, pixel_count) live

    def __init__(self):
        super().__init__()
        self.analyzer = VideoAnalyzer(scale=0.5)

    @Slot(str)
    def handle_video(self, video_url):
        path = video_url.replace("file:///", "")
        if sys.platform == "win32":
            path = path.replace("/", "\\")

        print(f"Analyzing video at: {path}")
        data = self.analyzer.process_video(path, self.on_frame_processed)

        if data:
            self.dataReady.emit(data)
        else:
            print("No data was generated from the video.")

    def on_frame_processed(self, frame_number, pixel_count):
        self.frameData.emit(frame_number, pixel_count)

if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    bridge = Bridge()

    # Make sure the path to your QML is correct
    qml_path = Path(__file__).parent / "UI" / "main.qml"
    
    # Set initial properties BEFORE loading
    engine.setInitialProperties({"python_bridge": bridge})
    engine.load(str(qml_path))

    if not engine.rootObjects():
        sys.exit(-1)
    sys.exit(app.exec())
import sys
import os
from pathlib import Path
from PySide6.QtCore import QObject, Slot, Signal, QTimer
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtQml import QQmlApplicationEngine
from sam3_segmenter import Sam3VideoSegmenter
import cv2 as cv


class Bridge(QObject):

    maxFrameChanged = Signal(int)  
    frameReady = Signal(str) 

    def __init__(self):
        super().__init__()
        self.segmenter = Sam3VideoSegmenter()

        # debounce timer
        self.frame_timer = QTimer()
        self.frame_timer.setSingleShot(True)
        self.frame_timer.timeout.connect(self._process_frame)
        self.pending_frame_idx = None

    @Slot(str)
    def load_video(self, video_url):
        path = video_url.replace("file:///", "")
        if sys.platform == "win32":
            path = path.replace("/", "\\")
        print(f"Loading video: {path}")

        self.segmenter.load_video(path)
        self.segmenter.add_text_prompt("Squirrel")

        total_frames = len(self.segmenter.video_frames)
        self.maxFrameChanged.emit(total_frames - 1)

    @Slot(int)
    def request_frame(self, frame_idx):
        """Called from QML on slider change."""
        self.pending_frame_idx = frame_idx
        # restart timer each move; process only after 200ms of inactivity
        self.frame_timer.start(200)

    def _process_frame(self):
        if self.pending_frame_idx is None or not self.segmenter:
            return
        frame_idx = self.pending_frame_idx
        self.pending_frame_idx = None

        # Get frame from segmenter
        frame = self.segmenter.video_frames[frame_idx].copy()

        # Apply mask if available
        frame_output = self.segmenter.showSingleFrame(frame_idx, return_frame_only=False)

        # Save temporarily as PNG
        tmp_path = os.path.join(os.getcwd(), "tmp_frame.png")
        cv.imwrite(tmp_path, frame)

        # Emit to QML
        self.frameReady.emit(tmp_path)


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    bridge = Bridge()

    qml_path = Path(__file__).parent / "UI" / "main.qml"

    engine.rootContext().setContextProperty("python_bridge", bridge)
    engine.load(str(qml_path))

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())

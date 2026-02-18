import sys
import os
from pathlib import Path
from PySide6.QtCore import QObject, Slot, Signal, QTimer, QMetaObject, Qt
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtQml import QQmlApplicationEngine
from sam3_segmenter import Sam3VideoSegmenter
import cv2 as cv
import threading


class Bridge(QObject):

    maxFrameChanged = Signal(int)  
    frameReady = Signal(str) 

    def __init__(self):
        super().__init__()
        self.segmenter = Sam3VideoSegmenter(target_size=512)

        # debounce timer
        self.frame_timer = QTimer()
        self.frame_timer.setSingleShot(True)
        self.frame_timer.timeout.connect(self._process_frame)
        self.pending_frame_idx = None

    @Slot(str)
    def load_video(self, video_url):
        # 1. Sanitize the path
        path = video_url.replace("file:///", "")
        if sys.platform == "win32":
            path = path.replace("/", "\\")
        
        # 2. Kick off the heavy processing in a BACKGROUND thread
        # This allows the main thread to return to QML immediately and draw the spinner
        worker = threading.Thread(target=self._run_segmentation, args=(path,))
        worker.daemon = True # Ensures thread closes if app is closed
        worker.start()

    def _run_segmentation(self, path):
        # The moment this starts, the UI thread is freed
        self.segmenter.load_video(path)
        self.segmenter.add_text_prompt("Squirrel")

        # Give the OS a tiny slice of time to process the UI animations
        total_frames = len(self.segmenter.video_frames)
        
        # Use the thread-safe emit
        self.maxFrameChanged.emit(total_frames - 1)

        if total_frames > 0:
            self.pending_frame_idx = 0
            # This MUST be a QueuedConnection to fire on the Main Thread
            QMetaObject.invokeMethod(self, "_process_frame", Qt.QueuedConnection)


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
        frame_output = self.segmenter.showSingleFrame(frame_idx, return_frame_only=True)

        # Save temporarily as PNG
        tmp_path = os.path.join(os.getcwd(), f"tmp_frame_{frame_idx}.png")
        cv.imwrite(tmp_path, frame_output)

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

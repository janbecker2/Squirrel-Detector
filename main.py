import sys
import os
import threading
from pathlib import Path
from PySide6.QtCore import QObject, Slot, Signal, QTimer, QMetaObject, Qt
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickImageProvider
import cv2 as cv
from sam3_segmenter import Sam3VideoSegmenter

class FrameProvider(QQuickImageProvider): 
    def __init__(self):
        super().__init__(QQuickImageProvider.Image)
        self.current_frame = QImage()

    def requestImage(self, id, size, requestedSize):
        # QML calls this whenever the source "image://frames/..." changes
        if self.current_frame.isNull():
            # Return an empty transparent image if nothing is loaded
            return QImage(1, 1, QImage.Format_ARGB32)
        return self.current_frame

    def update_frame(self, cv_img):
        # Convert OpenCV (BGR) to RGB QImage
        height, width, channel = cv_img.shape
        bytes_per_line = channel * width
        
        # We create the QImage and use .copy() to ensure the memory is 
        # owned by the QImage, preventing crashes when OpenCV releases the buffer
        self.current_frame = QImage(
            cv_img.data, width, height, bytes_per_line, QImage.Format_RGB888
        ).rgbSwapped().copy()

class Bridge(QObject):
    maxFrameChanged = Signal(int)
    frameUpdated = Signal() # Signal QML to refresh the image provider
    propagationFinished = Signal()
    chartImageUpdated = Signal(str)


    def __init__(self, provider):
        super().__init__()
        self.provider = provider
        self.segmenter = Sam3VideoSegmenter(target_size=1024)
        
        self.frame_timer = QTimer()
        self.frame_timer.setSingleShot(True)
        self.frame_timer.timeout.connect(self._process_frame)
        self.pending_frame_idx = None
        
        self.propagationFinished.connect(self.generate_graph)

    @Slot(str)
    def load_video(self, video_url):
        path = video_url.replace("file:///", "")
        if sys.platform == "win32":
            path = path.replace("/", "\\")
            if path.startswith("\\") and ":" in path:
                path = path[1:]
        
        worker = threading.Thread(target=self._run_segmentation, args=(path,))
        worker.daemon = True
        worker.start()

    def _run_segmentation(self, path):
        self.segmenter.load_video(path)
        self.segmenter.add_text_prompt("Squirrel")
        
        total_frames = len(self.segmenter.video_frames)
        self.maxFrameChanged.emit(total_frames - 1)

        if total_frames > 0:
            self.pending_frame_idx = 0
            QMetaObject.invokeMethod(self, "_process_frame", Qt.QueuedConnection)

    @Slot(int)
    def request_frame(self, frame_idx):
        self.pending_frame_idx = frame_idx
        self.frame_timer.start(50) 

    @Slot()
    def _process_frame(self):
        if self.pending_frame_idx is None or not self.segmenter:
            return
        
        frame_idx = self.pending_frame_idx
        self.pending_frame_idx = None

        frame_output = self.segmenter.showSingleFrame(frame_idx, return_frame_only=True)

        self.provider.update_frame(frame_output)
        
        # Notify QML
        self.frameUpdated.emit()
    
    @Slot()
    def propagate_video(self):
        def worker():
            try:
                self.segmenter.propagate_video()
                # Use QMetaObject to ensure generate_graph runs on the main thread
                QMetaObject.invokeMethod(self, "generate_graph", Qt.QueuedConnection)
            except Exception as e:
                print(f"Propagation error: {e}")
            finally:
                self.propagationFinished.emit()

        threading.Thread(target=worker, daemon=True).start()

        
    @Slot()
    def generate_graph(self):
        # Double check data exists
        if not self.segmenter.mask_areas:
            print("No mask data available")
            return

        # Ensure we have standard Python ints
        chart_data = [int(x) for x in self.segmenter.mask_areas]
        
        # Generate the base64 string
        graph_url = self.segmenter.generate_graph_image(chart_data)
        
        if graph_url:
            print("Graph generated successfully, emitting signal...")
            self.chartImageUpdated.emit(graph_url)



if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    # 1. Initialize the Provider
    image_provider = FrameProvider()
    
    # 2. Initialize the Bridge with access to the provider
    bridge = Bridge(image_provider)

    # 3. Register the provider with the engine
    engine.addImageProvider("frames", image_provider)

    qml_path = Path(__file__).parent / "UI" / "main.qml"
    engine.rootContext().setContextProperty("python_bridge", bridge)
    engine.load(str(qml_path))

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())
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
    frameUpdated = Signal() 
    propagationFinished = Signal()
    chartImageUpdated = Signal(str)
    statusUpdated = Signal(str) 
    # 1. Define the signal for the success/error toast notifications
    operationFinished = Signal(str) 

    def __init__(self, provider):
        super().__init__()
        self.provider = provider
        self.segmenter = Sam3VideoSegmenter(target_size=1024)
        
        self.frame_timer = QTimer()
        self.frame_timer.setSingleShot(True)
        self.frame_timer.timeout.connect(self._process_frame)
        self.pending_frame_idx = None
        
        # Store frames here so they can be exported to video later
        self.last_processed_frames = [] 
        
        self.propagationFinished.connect(self.generate_graph)

    # 2. Helper method to handle QML File URLs consistently
    def _parse_path(self, url):
        path = url.replace("file:///", "")
        if sys.platform == "win32":
            path = path.replace("/", "\\")
            if path.startswith("\\") and ":" in path:
                path = path[1:]
        return path

    @Slot(str)
    def load_video(self, video_url):
        path = self._parse_path(video_url)
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
        if frame_output is not None:
            self.provider.update_frame(frame_output)
            self.frameUpdated.emit()
    
    @Slot()
    def propagate_video(self):
        def worker():
            try:
                # 3. Capture the frames returned by the segmenter
                self.last_processed_frames = self.segmenter.propagate_video(status_callback=self.statusUpdated.emit)
            except Exception as e:
                print(f"Propagation error: {e}")
            finally:
                self.propagationFinished.emit()

        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def generate_graph(self):
        if not self.segmenter.mask_areas:
            return
        chart_data = [int(x) for x in self.segmenter.mask_areas]
        graph_url = self.segmenter.generate_graph_image(chart_data)
        if graph_url:
            self.chartImageUpdated.emit(graph_url)
            
    @Slot(str)
    def download_csv(self, file_url):
        path = self._parse_path(file_url)
        def worker():
            success = self.segmenter.export_graph_csv(path)
            if success:
                self.operationFinished.emit("CSV Data Exported Successfully!")
        threading.Thread(target=worker, daemon=True).start()
        
    @Slot(str)
    def download_video(self, file_url):
        path = self._parse_path(file_url)
        def worker():
            try:
                # 4. Pass the saved frames to the export function
                self.segmenter.export_video(self.last_processed_frames, path)
                self.operationFinished.emit("Video Exported Successfully!")
            except Exception as e:
                print(f"Export error: {e}")
                self.operationFinished.emit("Video Export Failed.")

        threading.Thread(target=worker, daemon=True).start()



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
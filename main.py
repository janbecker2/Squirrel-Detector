import sys
from pathlib import Path
import threading

# Core PySide6 imports
from PySide6.QtWidgets import QApplication, QSplashScreen 
from PySide6.QtCore import QObject, Slot, Signal, QTimer, QMetaObject, Qt, QPropertyAnimation
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickImageProvider

import cv2 as cv
from sam3_segmenter import Sam3VideoSegmenter

# --- Image Provider for QML ---
class FrameProvider(QQuickImageProvider): 
    def __init__(self):
        super().__init__(QQuickImageProvider.Image)
        self.current_frame = QImage()

    def requestImage(self, id, size, requestedSize):
        return self.current_frame if not self.current_frame.isNull() else QImage(1, 1, QImage.Format_ARGB32)

    def update_frame(self, cv_img):
        h, w, ch = cv_img.shape
        # Convert BGR to RGB and copy memory to prevent crashes
        self.current_frame = QImage(cv_img.data, w, h, ch * w, QImage.Format_RGB888).rgbSwapped().copy()

# --- Logic Bridge ---
class Bridge(QObject):
    maxFrameChanged = Signal(int)
    frameUpdated = Signal() 
    propagationFinished = Signal()
    chartImageUpdated = Signal(str)
    statusUpdated = Signal(str) 
    operationFinished = Signal(str) 

    def __init__(self, provider):
        super().__init__()
        self.provider = provider
        self.segmenter = Sam3VideoSegmenter(target_size=1024)
        
        self.frame_timer = QTimer(self)
        self.frame_timer.setSingleShot(True)
        self.frame_timer.timeout.connect(self._process_frame)
        self.pending_frame_idx = None
        self.last_processed_frames = [] 
        self.propagationFinished.connect(self.generate_graph)

    def _parse_path(self, url):
        path = url.replace("file:///", "")
        if sys.platform == "win32":
            path = path.replace("/", "\\")
            if path.startswith("\\") and ":" in path: path = path[1:]
        return path

    @Slot(str)
    def load_video(self, video_url):
        path = self._parse_path(video_url)
        threading.Thread(target=self._run_segmentation, args=(path,), daemon=True).start()

    def _run_segmentation(self, path):
        self.segmenter.load_video(path)
        self.segmenter.add_text_prompt("Squirrel")
        self.maxFrameChanged.emit(len(self.segmenter.video_frames) - 1)
        self.pending_frame_idx = 0
        QMetaObject.invokeMethod(self, "_process_frame", Qt.QueuedConnection)

    @Slot(int)
    def request_frame(self, frame_idx):
        self.pending_frame_idx = frame_idx
        self.frame_timer.start(16) # ~60fps response

    @Slot()
    def _process_frame(self):
        if self.pending_frame_idx is None: return
        frame = self.segmenter.showSingleFrame(self.pending_frame_idx, return_frame_only=True)
        if frame is not None:
            self.provider.update_frame(frame)
            self.frameUpdated.emit()
        self.pending_frame_idx = None

    @Slot()
    def propagate_video(self):
        def worker():
            self.last_processed_frames = self.segmenter.propagate_video(status_callback=self.statusUpdated.emit)
            self.propagationFinished.emit()
        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def generate_graph(self):
        if not self.segmenter.mask_areas: return
        url = self.segmenter.generate_graph_image([int(x) for x in self.segmenter.mask_areas])
        if url: self.chartImageUpdated.emit(url)

    @Slot(str)
    def download_csv(self, file_url):
        if self.segmenter.export_graph_csv(self._parse_path(file_url)):
            self.operationFinished.emit("CSV Data Exported Successfully!")

    @Slot(str)
    def download_video(self, file_url):
        try:
            self.segmenter.export_video(self.last_processed_frames, self._parse_path(file_url))
            self.operationFinished.emit("Video Exported Successfully!")
        except Exception:
            self.operationFinished.emit("Video Export Failed.")

# --- Execution ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 1. Setup Splash
    pixmap = QPixmap(str(Path(__file__).parent / "UI" / "assets" / "splash.png"))
    splash = QSplashScreen(pixmap if not pixmap.isNull() else QPixmap(600, 400))
    splash.show()
    splash.showMessage("Initializing SAM3 AI Model...", Qt.AlignBottom | Qt.AlignCenter, Qt.white)
    app.processEvents() 

    # 2. Setup Logic & Engine
    provider = FrameProvider()
    bridge = Bridge(provider)
    engine = QQmlApplicationEngine()
    engine.addImageProvider("frames", provider)
    engine.rootContext().setContextProperty("python_bridge", bridge)
    engine.load(str(Path(__file__).parent / "UI" / "main.qml"))

    if not engine.rootObjects():
        sys.exit(-1)

    # 3. Transition Splash -> Main
    main_window = engine.rootObjects()[0]
    
    # Create fade animation
    fade = QPropertyAnimation(splash, b"windowOpacity")
    fade.setDuration(500)
    fade.setStartValue(1.0)
    fade.setEndValue(0.0)
    fade.finished.connect(splash.close)
    
    # Finalize UI
    main_window.show()
    main_window.raise_() # Fixed: Added underscore to avoid SyntaxError
    main_window.requestActivate()
    fade.start()

    sys.exit(app.exec())
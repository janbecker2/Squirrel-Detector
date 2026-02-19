import sys
import os
import threading
import time
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Slot, Signal, QTimer, QMetaObject, Qt, QPropertyAnimation, QUrl
from PySide6.QtGui import QImage, QPixmap, QDesktopServices
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickImageProvider

# Internal imports
from splash import SplashScreen 
from sam3_segmenter import Sam3VideoSegmenter

class FrameProvider(QQuickImageProvider): 
    def __init__(self):
        super().__init__(QQuickImageProvider.Image)
        self.current_frame = QImage()

    def requestImage(self, id, size, requestedSize):
        return self.current_frame if not self.current_frame.isNull() else QImage(1, 1, QImage.Format_ARGB32)

    def update_frame(self, cv_img):
        h, w, ch = cv_img.shape
        # Convert BGR to RGB and copy memory to ensure safety between threads
        self.current_frame = QImage(cv_img.data, w, h, ch * w, QImage.Format_RGB888).rgbSwapped().copy()

class Bridge(QObject):
    maxFrameChanged = Signal(int)
    frameUpdated = Signal() 
    propagationFinished = Signal()
    chartImageUpdated = Signal(str)
    statusUpdated = Signal(str) 
    operationFinished = Signal(str) 

    def __init__(self, provider, splash=None):
        super().__init__()
        self.provider = provider
        
        # 1. Update Splash Progress: Start
        if splash: splash.set_progress(20)
        self.segmenter = Sam3VideoSegmenter(target_size=1024)
        
        # 2. Update Splash Progress: Model Loaded
        if splash: splash.set_progress(80)
        
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
        self.frame_timer.start(16)

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
    
    @Slot(str)
    def download_training_csv(self, file_url):
        path = self._parse_path(file_url)
        if self.segmenter.export_mask_csv(path):
            self.operationFinished.emit("Training CSV Exported Successfully!")
        else:
            self.operationFinished.emit("Training Export Failed: No mask data found.")
            
    @Slot()
    def open_help_link(self):
        """Opens the help documentation in the system browser."""
        # Replace with your actual URL
        QDesktopServices.openUrl(QUrl("https://github.com/janbecker2/Squirrel-App/blob/main/README.md"))

# --- Execution ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Enable high-quality pixmaps for the logo    
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    # 2. Load the transparent logo
    logo_path = Path(__file__).parent / "UI" / "assets" / "logo_transparent.png"
    logo_img = QPixmap(str(logo_path))
    
    if logo_img.isNull():
        print(f"!!! Error: Logo not found at {logo_path}")

    # 2. Initialize and Show Splash
    splash = SplashScreen(logo_img, width=500, height=350)
    splash.show()
    
    # 3. FORCE DISPLAY
    # We call this multiple times to ensure the window is painted 
    # before the CPU gets locked by the AI model.
    for _ in range(10):
        app.processEvents()
        
    # 4. Heavy Initialization
    provider = FrameProvider()
    bridge = Bridge(provider, splash=splash)
    
    # 3. Engine Setup
    if splash: splash.set_progress(90)
    engine = QQmlApplicationEngine()
    engine.addImageProvider("frames", provider)
    engine.rootContext().setContextProperty("python_bridge", bridge)
    engine.load(str(Path(__file__).parent / "UI" / "main.qml"))

    if not engine.rootObjects():
        sys.exit(-1)

    if splash: splash.set_progress(100)
    time.sleep(0.5)  # Brief pause to let users see the completed splash before transition
    # 4. Professional Transition Splash -> Main
    main_window = engine.rootObjects()[0]
    fade = QPropertyAnimation(splash, b"windowOpacity")
    fade.setDuration(600)
    fade.setStartValue(1.0)
    fade.setEndValue(0.0)
    fade.finished.connect(splash.close)
    
    main_window.show()
    main_window.raise_() # Fixed: Added underscore to avoid Python keyword conflict
    main_window.requestActivate()
    fade.start()

    sys.exit(app.exec())
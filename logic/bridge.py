import sys
import threading
from PySide6.QtCore import QObject, Slot, Signal, QTimer, QMetaObject, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from logic.sam3_authenticator import SAM3Auth
from logic.sam3_segmenter import Sam3VideoSegmenter

# Bridge class to connect QML and Segmenter logic
class Bridge(QObject):
    maxFrameChanged = Signal(int)
    frameUpdated = Signal() 
    propagationFinished = Signal()
    chartImageUpdated = Signal(str)
    statusUpdated = Signal(str) 
    operationFinished = Signal(str) 
    video_load_failed = Signal(str)

    # Initializing bridge 
    def __init__(self, provider, app_instance, splash=None):
        # Initialize the QObject and store the provider
        super().__init__()
        self.provider = provider
        self.app = app_instance
        
        # Show initial progress on splash screen
        if splash: splash.set_progress(20)
        self.app.processEvents() 

        # authenticate user for access to models
        auth = SAM3Auth()
        if not auth.login():
            print("Login failed. Closing App...")
            sys.exit(-1)
            
        if splash: splash.set_progress(50)
        self.app.processEvents()
        
        # Initialisierung des Segmenters (Blackwell-optimiert via Torch 2.10)
        self.segmenter = Sam3VideoSegmenter(target_size=1024)
        
        if splash: splash.set_progress(80)
        self.app.processEvents()
        
        # Timer for frame processing
        self.frame_timer = QTimer(self)
        self.frame_timer.setSingleShot(True)
        self.frame_timer.timeout.connect(self._process_frame)
        self.pending_frame_idx = None
        self.last_processed_frames = [] 
        self.propagationFinished.connect(self.generate_graph)

    # herlper method to convert file URLs to paths
    def _parse_path(self, url):
        path = url.replace("file:///", "")
        if sys.platform == "win32":
            path = path.replace("/", "\\")
            if path.startswith("\\") and ":" in path: path = path[1:]
        return path

    # load video function called from QML
    @Slot(str)
    def load_video(self, video_url):
        path = self._parse_path(video_url)
        threading.Thread(target=self._run_segmentation, args=(path,), daemon=True).start()

     # runs segmentation in another thread to avoid crashing UI!!!
    def _run_segmentation(self, path):
        try:
            self.segmenter.load_video(path)

            self.segmenter.add_text_prompt("Squirrel")
            self.maxFrameChanged.emit(len(self.segmenter.video_frames) - 1)
            self.pending_frame_idx = 0
            QMetaObject.invokeMethod(self, "_process_frame", Qt.QueuedConnection)
            
        except Exception as e:
            self.pending_frame_idx = None
            error_message = "Error loading video: Downsize the video or try a shorter sequence to avoid VRAM overflow!"
            self.video_load_failed.emit(error_message)

    # Slot to handle frame requests of QML
    @Slot(int)
    def request_frame(self, frame_idx):
        self.pending_frame_idx = frame_idx
        self.frame_timer.start(16)

    # processes a single frame and showing in qml
    @Slot()
    def _process_frame(self):
        if self.pending_frame_idx is None: return
        frame = self.segmenter.showSingleFrame(self.pending_frame_idx, return_frame_only=True)
        if frame is not None:
            self.provider.update_frame(frame)
            self.frameUpdated.emit()
        self.pending_frame_idx = None

    # starts video propagation; again in seperate thread to avoid UI crash!
    @Slot()
    def propagate_video(self):
        def worker():
            self.last_processed_frames = self.segmenter.propagate_video(status_callback=self.statusUpdated.emit)
            self.propagationFinished.emit()
        threading.Thread(target=worker, daemon=True).start()

    # generates graph image and sends URL to QML;
    @Slot()
    def generate_graph(self):
        if not self.segmenter.mask_areas: return
        # Maskendaten für die Chart-Visualisierung aufbereiten
        url = self.segmenter.generate_graph_image([int(x) for x in self.segmenter.mask_areas])
        if url: self.chartImageUpdated.emit(url)

    # export function for CSV of graph data
    @Slot(str)
    def download_csv(self, file_url):
        if self.segmenter.export_graph_csv(self._parse_path(file_url)):
            self.operationFinished.emit("CSV Data Exported Successfully!")

    # export function for video with masks
    @Slot(str)
    def download_video(self, file_url):
        try:
            self.segmenter.export_video(self.last_processed_frames, self._parse_path(file_url))
            self.operationFinished.emit("Video Exported Successfully!")
        except Exception:
            self.operationFinished.emit("Video Export Failed.")
    
    # export function for CSV of mask bounding boxes per frame
    @Slot(str)
    def download_training_csv(self, file_url):
        path = self._parse_path(file_url)
        if self.segmenter.export_mask_csv(path):
            self.operationFinished.emit("Training CSV Exported Successfully!")
        else:
            self.operationFinished.emit("Training Export Failed: No mask data found.")
    # function to open github readme in browser
    @Slot()
    def open_help_link(self):
        QDesktopServices.openUrl(QUrl("https://github.com/janbecker2/Squirrel-App/blob/main/README.md"))
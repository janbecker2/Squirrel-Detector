from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider

# Frame Provider for QML to fetch video frames from the segmenter
class FrameProvider(QQuickImageProvider): 
    def __init__(self):
        super().__init__(QQuickImageProvider.Image)
        self.current_frame = QImage()

    def requestImage(self, id, size, requestedSize):
        return self.current_frame if not self.current_frame.isNull() else QImage(1, 1, QImage.Format_ARGB32)

    def update_frame(self, cv_img):
        h, w, ch = cv_img.shape
        self.current_frame = QImage(cv_img.data, w, h, ch * w, QImage.Format_RGB888).rgbSwapped().copy()
from PySide6.QtWidgets import QSplashScreen, QApplication
from PySide6.QtGui import QPainter, QColor, QBrush, QPixmap, QLinearGradient, QFont, QPen
from PySide6.QtCore import Qt, QRect, QPoint

# Splash Screen class
class SplashScreen(QSplashScreen):
    # initializing the splash screen with a logo and custom design
    def __init__(self, logo_pixmap, width=600, height=400):
        base_pixmap = QPixmap(width, height)
        base_pixmap.fill(Qt.transparent) 
        super().__init__(base_pixmap)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.logo = logo_pixmap
        self.progress = 0
        self.status_text = "Initializing..."

    # function to update progress
    def set_progress(self, value, text=None):
        self.progress = value
        if text:
            self.status_text = text
        self.update()
        QApplication.processEvents()

    # function to draw on splash screen
    def drawContents(self, painter: QPainter):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        rect = self.rect()
        
        # Background
        bg_color = QColor(30, 30, 46, 240) 
        painter.setBrush(bg_color)
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1)) 
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 15, 15)

        # Logo
        if self.logo and not self.logo.isNull():
            logo_size = int(self.height() * 0.35)
            scaled_logo = self.logo.scaled(
                logo_size, logo_size, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            
            lx = (self.width() - scaled_logo.width()) // 2
            ly = (self.height() // 2) - (scaled_logo.height() // 2) - 40
            painter.drawPixmap(lx, ly, scaled_logo)
        
        # Title    
        title_font = QFont("Segoe UI", 18, QFont.Bold) if "Segoe UI" in QFont().family() else QFont("Sans Serif", 18, QFont.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor(0, 0, 0, 100))
        title_rect = QRect(0, ly + scaled_logo.height() + 10, self.width(), 40)
        painter.drawText(title_rect.adjusted(2, 2, 2, 2), Qt.AlignCenter, "Squirrel Detector")
        painter.setPen(QColor("#f5e0dc")) 
        painter.drawText(title_rect, Qt.AlignCenter, "Squirrel Detector")

        # Status Text
        font = QFont("Segoe UI", 10) if "Segoe UI" in QFont().family() else QFont("Sans Serif", 10)
        painter.setFont(font)
        painter.setPen(QColor(205, 214, 244)) 
        status_rect = QRect(0, self.height() - 110, self.width(), 30)
        painter.drawText(status_rect, Qt.AlignCenter, self.status_text)

        # Progress Bar
        bar_w = int(self.width() * 0.6)
        bar_h = 6 
        bar_x = (self.width() - bar_w) // 2
        bar_y = self.height() - 70

        # Background 
        painter.setBrush(QColor(49, 50, 68)) 
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 3, 3)

        # Foreground
        if self.progress > 0:
            fill_w = int((self.progress / 100) * bar_w)
            
            grad = QLinearGradient(bar_x, 0, bar_x + bar_w, 0)
            grad.setColorAt(0, QColor("#89dceb"))
            grad.setColorAt(1, QColor("#74c7ec")) 
            
            painter.setBrush(grad)
            painter.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 3, 3)
            
            if fill_w > 5:
                painter.setBrush(QColor(255, 255, 255, 100))
                painter.drawEllipse(QPoint(bar_x + fill_w, bar_y + (bar_h // 2)), 2, 2)
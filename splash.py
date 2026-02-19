from PySide6.QtWidgets import QSplashScreen, QApplication
from PySide6.QtGui import QPainter, QColor, QBrush, QPixmap, QLinearGradient, QFont, QPen
from PySide6.QtCore import Qt, QRect, QPoint

class SplashScreen(QSplashScreen):
    def __init__(self, logo_pixmap, width=600, height=400):
        base_pixmap = QPixmap(width, height)
        base_pixmap.fill(Qt.transparent) 
        super().__init__(base_pixmap)
        
        # Ensure the window itself is frameless and translucent
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.logo = logo_pixmap
        self.progress = 0
        self.status_text = "Initializing..."

    def set_progress(self, value, text=None):
        self.progress = value
        if text:
            self.status_text = text
        self.update()
        QApplication.processEvents()

    def drawContents(self, painter: QPainter):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        rect = self.rect()
        
        # 1. Main Background Container (Rounded Glass Look)
        # Using a slightly transparent dark theme (Catppuccin Mocha style)
        bg_color = QColor(30, 30, 46, 240) 
        painter.setBrush(bg_color)
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1)) # Thin border
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 15, 15)

        # 2. Logo with Soft Shadow/Glow
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
            
        title_font = QFont("Segoe UI", 18, QFont.Bold) if "Segoe UI" in QFont().family() else QFont("Sans Serif", 18, QFont.Bold)
        painter.setFont(title_font)
        
        # Create a subtle drop shadow for the text
        painter.setPen(QColor(0, 0, 0, 100))
        title_rect = QRect(0, ly + scaled_logo.height() + 10, self.width(), 40)
        painter.drawText(title_rect.adjusted(2, 2, 2, 2), Qt.AlignCenter, "Squirrel Detector")

        # Main Title Text
        painter.setPen(QColor("#f5e0dc")) # Rosewater/Off-white color
        painter.drawText(title_rect, Qt.AlignCenter, "Squirrel Detector")

        # 3. Modern Typography (Status Text)
        font = QFont("Segoe UI", 10) if "Segoe UI" in QFont().family() else QFont("Sans Serif", 10)
        painter.setFont(font)
        painter.setPen(QColor(205, 214, 244)) # Light lavender text
        status_rect = QRect(0, self.height() - 110, self.width(), 30)
        painter.drawText(status_rect, Qt.AlignCenter, self.status_text)

        # 4. Modern Progress Bar (Slim & Glowing)
        bar_w = int(self.width() * 0.6)
        bar_h = 6 # Slimmer is more modern
        bar_x = (self.width() - bar_w) // 2
        bar_y = self.height() - 70

        # Background Track
        painter.setBrush(QColor(49, 50, 68)) 
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 3, 3)

        # Foreground (Accent Gradient)
        if self.progress > 0:
            fill_w = int((self.progress / 100) * bar_w)
            
            # Neon Gradient: Cyan to Blue
            grad = QLinearGradient(bar_x, 0, bar_x + bar_w, 0)
            grad.setColorAt(0, QColor("#89dceb")) # Sky Blue
            grad.setColorAt(1, QColor("#74c7ec")) # Sapphire
            
            painter.setBrush(grad)
            # Add a subtle glow/inner shadow effect
            painter.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 3, 3)
            
            # Small "Lead" Glow (The tip of the progress bar)
            if fill_w > 5:
                painter.setBrush(QColor(255, 255, 255, 100))
                painter.drawEllipse(QPoint(bar_x + fill_w, bar_y + (bar_h // 2)), 2, 2)
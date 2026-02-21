import sys
import os
import time
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPropertyAnimation
from PySide6.QtGui import QPixmap
from PySide6.QtQml import QQmlApplicationEngine

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from UI.splash import SplashScreen 
from logic.frame_provider import FrameProvider
from logic.bridge import Bridge

def main():
    # app setup
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps) 
    logo_path = Path(__file__).parent / "UI" / "assets" / "logo_transparent.png"
    logo_img = QPixmap(str(logo_path))

    if logo_img.isNull():
        print(f"!!! Error: Logo not found at {logo_path}")

    # laoding screen setup
    splash = SplashScreen(logo_img, width=500, height=350)
    splash.show()
    
    for _ in range(10):
        app.processEvents()
        
    # setup frame provider and bridge for interacting with qml
    provider = FrameProvider()
    bridge = Bridge(provider, app, splash=splash)
    
    # Load QML and show main window
    if splash: splash.set_progress(90)
    engine = QQmlApplicationEngine()
    engine.addImageProvider("frames", provider)
    engine.rootContext().setContextProperty("python_bridge", bridge)
    engine.load(str(Path(__file__).parent / "UI" / "main.qml"))
    
    if not engine.rootObjects():
        sys.exit(-1)

    if splash: splash.set_progress(100)
    
    time.sleep(0.5)  
    main_window = engine.rootObjects()[0]
    fade = QPropertyAnimation(splash, b"windowOpacity")
    fade.setDuration(600)
    fade.setStartValue(1.0)
    fade.setEndValue(0.0)
    fade.finished.connect(splash.close)
    main_window.show()
    main_window.raise_() 
    main_window.requestActivate()
    fade.start()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
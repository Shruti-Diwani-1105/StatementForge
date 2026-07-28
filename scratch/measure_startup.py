import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

t0 = time.perf_counter()

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import PyQt6.QtWebEngineWidgets

QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)

app = QApplication(sys.argv)

t1 = time.perf_counter()
print(f"[MEASUREMENT] QApplication created in {(t1 - t0)*1000:.2f} ms")

from ui.splash_screen import SplashScreen
splash = SplashScreen()
splash.show()
app.processEvents()

t2 = time.perf_counter()
print(f"[MEASUREMENT] Splash Screen shown in {(t2 - t1)*1000:.2f} ms")

from utils.asset_generator import generate_assets
from utils.theme_manager import ThemeManager

splash.set_progress(20, "Initializing Assets & Resources...")
generate_assets()

splash.set_progress(40, "Applying Enterprise Stylesheet...")
ThemeManager.initialize_theme()

splash.set_progress(65, "Loading Application Interfaces...")
from controllers.navigation import NavigationController
main_window = NavigationController()

t3 = time.perf_counter()
print(f"[MEASUREMENT] Main Navigation Controller initialized in {(t3 - t2)*1000:.2f} ms")

splash.set_progress(100, "Ready")
t4 = time.perf_counter()
print(f"[MEASUREMENT] Total real initialization pipeline time: {(t4 - t0)*1000:.2f} ms")

sys.exit(0)

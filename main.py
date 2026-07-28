import sys
import os
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import PyQt6.QtWebEngineWidgets  # Mandatory import before QApplication initialization

# Ensure project root is in the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.asset_generator import generate_assets
from utils.theme_manager import ThemeManager

def load_stylesheet(app):
    """Loads the global stylesheet via ThemeManager."""
    ThemeManager.initialize_theme()

def main():
    # 1. Enable High DPI support and OpenGL Context Sharing for WebEngine
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # 2. Create the Qt application instance
    app = QApplication(sys.argv)
    
    # Initialize global responsive scaling and Ctrl+Scroll/Key zoom filter
    from utils.responsive_scaling import apply_responsive_patches
    apply_responsive_patches(app)
    
    # Set default modern font weight/style
    default_font = QFont("Times New Roman", 10)
    app.setFont(default_font)

    # 3. Show Splash Screen IMMEDIATELY
    from ui.splash_screen import SplashScreen
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    # 4. Milestone 1: Asset Verification/Generation
    splash.set_progress(20, "Initializing Assets & Resources...")
    try:
        generate_assets()
    except Exception as e:
        print(f"Error generating placeholder assets: {e}")
        sys.exit(1)

    # 5. Milestone 2: Apply Theme QSS
    splash.set_progress(40, "Applying Enterprise Stylesheet...")
    load_stylesheet(app)

    # 6. Milestone 3: Parallel Main Window & Screen Instantiation
    splash.set_progress(65, "Loading Application Interfaces...")
    from controllers.navigation import NavigationController
    
    main_window = None
    try:
        main_window = NavigationController()
    except Exception as e:
        print(f"Error launching main interface: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 7. Milestone 4: Application Ready State
    splash.set_progress(100, "Ready")

    # Transition from splash screen to main window as soon as loading completes
    splash.finish_and_show(main_window)
    
    # Execute the application event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

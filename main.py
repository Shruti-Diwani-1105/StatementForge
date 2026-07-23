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
    
    # 3. Generate visual assets programmatically if they are missing
    try:
        generate_assets()
    except Exception as e:
        print(f"Error generating placeholder assets: {e}")
        sys.exit(1)
        
    # 4. Apply global theme QSS
    load_stylesheet(app)
    
    # 5. Initialize and show the Splash Screen
    from ui.splash_screen import SplashScreen
    splash = SplashScreen()
    splash.show()
    
    # Keep reference to the main window controller so it doesn't get garbage-collected
    main_window = None
    
    def on_loading_complete():
        nonlocal main_window
        from controllers.navigation import NavigationController
        try:
            # Instantiate main window controller containing stacked screens
            main_window = NavigationController()
            main_window.show()
        except Exception as e:
            print(f"Error launching main interface: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    # Transition to main interface when loading completes
    splash.loadingFinished.connect(on_loading_complete)
    
    # Execute the application event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

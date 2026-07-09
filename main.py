import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Ensure project root is in the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.asset_generator import generate_assets

def load_stylesheet(app):
    """Loads the global stylesheet and applies it to the application."""
    qss_path = os.path.join("styles", "theme.qss")
    if os.path.exists(qss_path):
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                stylesheet = f.read()
                app.setStyleSheet(stylesheet)
        except Exception as e:
            print(f"Warning: Failed to load stylesheet from {qss_path}. Error: {e}")
    else:
        print(f"Warning: Stylesheet not found at {qss_path}.")

def main():
    # 1. Enable High DPI support for sharp text and clean assets
    # (High DPI is default in PyQt6, but explicitly adjusting scale policies ensures consistency across OS)
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # 2. Create the Qt application instance
    app = QApplication(sys.argv)
    
    # Set default modern font weight/style
    default_font = QFont("Segoe UI", 10)
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

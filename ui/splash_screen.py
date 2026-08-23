import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap

class SplashScreen(QWidget):
    """
    Clean, modern HTML/CSS-styled startup splash screen for StatementForge.
    Renders the fintech visual layout instantly without GPU/WebEngine compositor delay.
    """
    loadingFinished = pyqtSignal()

    def __init__(self):
        super().__init__()
        
        # Configure frameless stay-on-top splash window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        
        self.setFixedSize(620, 420)
        self.center_on_screen()
        
        # Apply dark blue/indigo fintech gradient background
        self.setStyleSheet("""
            QWidget#SplashRoot {
                background-color: #080c14;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #090d16, stop:0.5 #111a2e, stop:1 #080c14);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
            }
        """)
        self.setObjectName("SplashRoot")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(10)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 1. Project Logo (assets/logo.png)
        self.logo_label = QLabel()
        logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png"))
        if not os.path.exists(logo_path):
            logo_path = os.path.abspath("assets/logo.png")
            
        pixmap = QPixmap(logo_path)
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(84, 84, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(scaled_pixmap)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setStyleSheet("background: transparent; border: none;")
        main_layout.addWidget(self.logo_label)
        
        main_layout.addSpacing(6)
        
        # 2. Main Title: StatementForge
        self.title_label = QLabel("StatementForge")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("""
            font-size: 32px;
            font-weight: 800;
            color: #FFFFFF;
            font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
            letter-spacing: -0.5px;
            background: transparent;
            border: none;
        """)
        main_layout.addWidget(self.title_label)
        
        # 3. Subtitle: AI POWERED ACCOUNTING HUB
        self.subtitle_label = QLabel("AI POWERED ACCOUNTING HUB")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setStyleSheet("""
            font-size: 11px;
            font-weight: 700;
            color: #3B82F6;
            letter-spacing: 2px;
            font-family: 'Segoe UI', 'Inter', sans-serif;
            background: transparent;
            border: none;
        """)
        main_layout.addWidget(self.subtitle_label)
        
        # 4. Tagline: Parse • Verify • Analyze • Export
        self.tagline_label = QLabel("Parse • Verify • Analyze • Export")
        self.tagline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tagline_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 500;
            color: #94A3B8;
            letter-spacing: 1px;
            font-family: 'Segoe UI', 'Inter', sans-serif;
            background: transparent;
            border: none;
        """)
        main_layout.addWidget(self.tagline_label)
        
        main_layout.addSpacing(24)
        
        # 5. Subtle Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1D4ED8, stop:1 #60A5FA);
                border-radius: 2px;
            }
        """)
        main_layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)
        
        main_layout.addSpacing(8)
        
        # 6. Status Text: Loading StatementForge...
        self.loading_label = QLabel("Loading StatementForge...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("""
            font-size: 11px;
            font-weight: 500;
            color: #64748B;
            font-family: 'Segoe UI', 'Inter', sans-serif;
            background: transparent;
            border: none;
        """)
        main_layout.addWidget(self.loading_label)
        
        self.main_window_ref = None

    def center_on_screen(self):
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geo = screen.geometry()
            x = (screen_geo.width() - self.width()) // 2
            y = (screen_geo.height() - self.height()) // 2
            self.move(x, y)

    def set_progress(self, val, text=None):
        """Sets real loading progress and status message."""
        self.progress_bar.setValue(int(max(0, min(100, val))))
        if text:
            self.loading_label.setText(text)
        QApplication.processEvents()

    def set_loading_text(self, text):
        if text:
            self.loading_label.setText(text)
            QApplication.processEvents()

    def finish_and_show(self, main_window):
        """Transitions from splash screen to main window immediately without artificial delay."""
        self.main_window_ref = main_window
        if self.main_window_ref:
            self.main_window_ref.show()
        self.close()
        self.loadingFinished.emit()

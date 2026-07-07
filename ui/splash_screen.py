from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPixmap, QColor, QFont

class SplashScreen(QWidget):
    """
    A premium frameless splash screen that displays the app logo,
    simulates module loading over 3 seconds, updates loading labels,
    and runs a smooth fade-out animation when complete.
    """
    loadingFinished = pyqtSignal()

    def __init__(self):
        super().__init__()
        
        # Make the window frameless and translucent
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setFixedSize(650, 420)
        self.center_on_screen()
        
        # Setup fade effect
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)
        
        # Layout and Visuals
        self.init_ui()
        
        # Progress Tracking Timer
        self.progress_value = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(30) # ~3 seconds total (100 * 30ms = 3000ms)

    def init_ui(self):
        # Master container styled as a card with rounded corners and a premium deep space gradient
        self.container = QWidget(self)
        self.container.setObjectName("SplashContainer")
        self.container.setStyleSheet("""
            QWidget#SplashContainer {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, 
                                                  stop: 0 #0F172A, 
                                                  stop: 1 #1E1B4B); /* Deep Space/Navy Gradient */
                border: 1px solid #1E293B;
                border-radius: 16px;
            }
        """)
        
        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(16)
        
        # Logo (centered)
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_pixmap = QPixmap("assets/logo.png")
        if not logo_pixmap.isNull():
            self.logo_label.setPixmap(logo_pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        main_layout.addWidget(self.logo_label)
        
        # App Title (Glowing White)
        self.title_label = QLabel("StatementForge")
        self.title_label.setMinimumHeight(48)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 32px; font-weight: 800; color: #FFFFFF; letter-spacing: -0.5px; border: 0px solid transparent; padding-bottom: 6px;")
        main_layout.addWidget(self.title_label)
        
        # Subtitle (Muted Slate Blue)
        self.subtitle_label = QLabel("Multi-Bank Financial Statement Parser & Verification Tool")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setStyleSheet("font-size: 13px; color: #94A3B8; font-weight: 500;")
        main_layout.addWidget(self.subtitle_label)
        
        main_layout.addSpacing(20)
        
        # Progress Bar (Cyan-Blue gradient progress chunk)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1E293B;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, 
                                                  stop: 0 #3B82F6, 
                                                  stop: 1 #2563EB);
                border-radius: 3px;
            }
        """)
        main_layout.addWidget(self.progress_bar)
        
        # Loading Info label
        self.loading_label = QLabel("Loading Modules...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("font-size: 12px; color: #64748B; font-weight: 500;")
        main_layout.addWidget(self.loading_label)
        
        # Fit container in QWidget
        widget_layout = QVBoxLayout(self)
        widget_layout.setContentsMargins(0, 0, 0, 0)
        widget_layout.addWidget(self.container)

    def center_on_screen(self):
        """Center the widget on the user's primary display screen."""
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geo = screen.geometry()
            x = (screen_geo.width() - self.width()) // 2
            y = (screen_geo.height() - self.height()) // 2
            self.move(x, y)

    def update_progress(self):
        self.progress_value += 1
        self.progress_bar.setValue(self.progress_value)
        
        # Update text description at different stages
        if self.progress_value < 25:
            self.loading_label.setText("Loading Modules...")
        elif self.progress_value < 50:
            self.loading_label.setText("Loading Interface...")
        elif self.progress_value < 75:
            self.loading_label.setText("Loading Components...")
        elif self.progress_value < 100:
            self.loading_label.setText("Loading Complete...")
            
        if self.progress_value >= 100:
            self.timer.stop()
            self.fade_out_and_finish()

    def fade_out_and_finish(self):
        """Play fade-out animation, then notify main window to transition."""
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(500)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.finished.connect(self.on_animation_finished)
        self.anim.start()

    def on_animation_finished(self):
        self.close()
        self.loadingFinished.emit()

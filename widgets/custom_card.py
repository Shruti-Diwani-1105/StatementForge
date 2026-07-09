from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QPixmap, QColor, QCursor

class CustomCard(QFrame):
    """
    A premium card widget featuring rounded corners, soft shadows,
    hover transformations, and click handling.
    """
    clicked = pyqtSignal()

    def __init__(self, title, description, icon_path=None, icon_bg=None, parent=None):
        super().__init__(parent)
        self.setObjectName("CardFrame")
        self.setProperty("class", "CardFrame")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # Setup Card Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # Icon Label with circular backdrop
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(48, 48)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if icon_bg:
            self.icon_label.setStyleSheet(f"background-color: {icon_bg}; border-radius: 24px; border: none;")
        else:
            self.icon_label.setStyleSheet("background-color: #F1F5F9; border-radius: 24px; border: none;")
            
        if icon_path:
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                self.icon_label.setPixmap(pixmap.scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(self.icon_label)
        
        # Title Label
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: 600; font-size: 16px; color: #0F172A;")
        layout.addWidget(self.title_label)
        
        # Description Label
        self.desc_label = QLabel(description)
        self.desc_label.setStyleSheet("color: #64748B; font-size: 13px; line-height: 18px;")
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)
        
        # Make layouts stretch nicely
        layout.addStretch()
        
        # Setup Soft Drop Shadow
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(16)
        self.shadow.setColor(QColor(15, 23, 42, 20)) # Very soft slate shadow
        self.shadow.setOffset(0, 4)
        self.setGraphicsEffect(self.shadow)
        
        self.normal_style = ""
        self.hover_style = ""
        
        from utils.theme_manager import ThemeManager
        self.update_theme_style(ThemeManager.get_theme())

    def update_theme_style(self, theme):
        if theme == "dark":
            self.normal_style = """
                QFrame#CardFrame {
                    background-color: #1E293B;
                    border: 1px solid #334155;
                    border-radius: 12px;
                }
            """
            self.hover_style = """
                QFrame#CardFrame {
                    background-color: #1E293B;
                    border: 1px solid #3B82F6;
                    border-radius: 12px;
                }
            """
            self.title_label.setStyleSheet("font-weight: 600; font-size: 16px; color: #F8FAFC;")
            self.desc_label.setStyleSheet("color: #94A3B8; font-size: 13px; line-height: 18px;")
        else:
            self.normal_style = """
                QFrame#CardFrame {
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 12px;
                }
            """
            self.hover_style = """
                QFrame#CardFrame {
                    background-color: #FFFFFF;
                    border: 1px solid #3B82F6;
                    border-radius: 12px;
                }
            """
            self.title_label.setStyleSheet("font-weight: 600; font-size: 16px; color: #0F172A;")
            self.desc_label.setStyleSheet("color: #64748B; font-size: 13px; line-height: 18px;")
            
        self.setStyleSheet(self.normal_style)

    def enterEvent(self, event):
        # Update stylesheet on hover for border change
        self.setStyleSheet(self.hover_style)
        # Shift and increase shadow
        self.shadow.setBlurRadius(24)
        self.shadow.setOffset(0, 8)
        self.shadow.setColor(QColor(37, 99, 235, 30)) # Slight blue tint shadow
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(self.normal_style)
        self.shadow.setBlurRadius(16)
        self.shadow.setOffset(0, 4)
        self.shadow.setColor(QColor(15, 23, 42, 20))
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

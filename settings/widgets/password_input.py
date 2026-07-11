from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QEvent
from PyQt6.QtGui import QPixmap, QIcon, QCursor

class PasswordInput(QFrame):
    """
    A premium password entry field wrapping a toggleable show/hide eye icon button.
    Maintains a professional focus border, supports placeholder text, and
    supports standard password mask mode.
    """
    textChanged = pyqtSignal(str)
    returnPressed = pyqtSignal()

    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setObjectName("PasswordInputContainer")
        self.setFixedHeight(40)
        
        # Layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(12, 0, 8, 0)
        self.layout.setSpacing(8)
        
        # Line edit
        self.line_edit = QLineEdit(self)
        self.line_edit.setPlaceholderText(placeholder)
        self.line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.line_edit.setStyleSheet("background: transparent; border: none; padding: 0; font-size: 13px;")
        self.line_edit.textChanged.connect(self.textChanged.emit)
        self.line_edit.returnPressed.connect(self.returnPressed.emit)
        self.line_edit.installEventFilter(self)
        self.layout.addWidget(self.line_edit)
        
        # Show/Hide Toggle button
        self.toggle_btn = QPushButton(self)
        self.toggle_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.toggle_btn.setFixedSize(20, 20)
        self.toggle_btn.setStyleSheet("background: transparent; border: none; padding: 0;")
        
        self.eye_open_pixmap = QPixmap("assets/icons/eye.png").scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.eye_closed_pixmap = QPixmap("assets/icons/eye_closed.png").scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        self.toggle_btn.setIcon(QIcon(self.eye_closed_pixmap))
        self.toggle_btn.clicked.connect(self.toggle_visibility)
        self.layout.addWidget(self.toggle_btn)
        
        # Apply themes
        from utils.theme_manager import ThemeManager
        self.current_theme = ThemeManager.get_theme()
        self.update_style(focused=False)

    def eventFilter(self, watched, event):
        if watched == self.line_edit:
            if event.type() == QEvent.Type.FocusIn:
                self.update_style(focused=True)
            elif event.type() == QEvent.Type.FocusOut:
                self.update_style(focused=False)
        return super().eventFilter(watched, event)

    def update_style(self, focused=False):
        """Updates borders, text colors, and background dynamically."""
        if self.current_theme == "dark":
            border_color = "#3B82F6" if focused else "#334155"
            bg_color = "#0F172A"
            text_color = "#F8FAFC"
        else:
            border_color = "#2563EB" if focused else "#CBD5E1"
            bg_color = "#FFFFFF"
            text_color = "#0F172A"

        self.setStyleSheet(f"""
            QFrame#PasswordInputContainer {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 10px;
            }}
        """)
        self.line_edit.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                border: none;
                padding: 0;
                font-size: 13px;
                color: {text_color};
            }}
        """)

    def update_theme(self, theme):
        self.current_theme = theme
        self.update_style(focused=self.line_edit.hasFocus())

    def toggle_visibility(self):
        if self.line_edit.echoMode() == QLineEdit.EchoMode.Password:
            self.line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_btn.setIcon(QIcon(self.eye_open_pixmap))
        else:
            self.line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_btn.setIcon(QIcon(self.eye_closed_pixmap))

    # Accessors
    def text(self):
        return self.line_edit.text()

    def setText(self, text):
        self.line_edit.setText(text)

    def clear(self):
        self.line_edit.clear()

    def setReadOnly(self, read_only):
        self.line_edit.setReadOnly(read_only)
        self.toggle_btn.setEnabled(not read_only)

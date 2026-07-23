from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QFrame, QPushButton, QGridLayout, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QTimer, QEvent
from PyQt6.QtGui import QPixmap, QCursor, QIcon

class ToastNotification(QWidget):
    """
    Floating animated toast notification banner for displaying success / error alerts.
    """
    def __init__(self, parent=None, text="Action Completed", duration=3000):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        
        self.container = QFrame()
        self.container.setStyleSheet("""
            QFrame {
                background-color: #1E293B;
                color: #FFFFFF;
                border-radius: 8px;
                border: 1px solid #334155;
            }
        """)
        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(14, 8, 14, 8)
        
        self.label = QLabel(text)
        self.label.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 600; font-family: 'Times New Roman'; border: none; background: transparent;")
        container_layout.addWidget(self.label)
        
        layout.addWidget(self.container)
        
        # Position at top center of parent widget
        if parent:
            parent_rect = parent.rect()
            self.adjustSize()
            x = (parent_rect.width() - self.width()) // 2
            y = 20
            self.move(x, y)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(250)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()
        
        self.show()
        self.raise_()
        
        QTimer.singleShot(duration, self.fade_out)

    def show_toast(self):
        self.show()
        self.raise_()


    def fade_out(self):
        self.anim_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_out.setDuration(250)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.finished.connect(self.close)
        self.anim_out.start()


class PasswordRequirementsWidget(QWidget):
    """
    Compact horizontal grid containing validation checklists for password criteria.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(4)

        self.reqs = [
            {"id": "len", "text": "Minimum 8 characters", "valid": False},
            {"id": "upper", "text": "Uppercase letter", "valid": False},
            {"id": "lower", "text": "Lowercase letter", "valid": False},
            {"id": "num", "text": "Number", "valid": False},
            {"id": "special", "text": "Special character", "valid": False}
        ]

        self.labels = {}
        for idx, req in enumerate(self.reqs):
            lbl = QLabel(f"✓ {req['text']}")
            lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600; font-family: 'Times New Roman';")
            row = idx // 3
            col = idx % 3
            layout.addWidget(lbl, row, col)
            self.labels[req["id"]] = lbl

    def update_requirements(self, password):
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        self.reqs[0]["valid"] = len(password) >= 8
        self.reqs[1]["valid"] = any(c.isupper() for c in password)
        self.reqs[2]["valid"] = any(c.islower() for c in password)
        self.reqs[3]["valid"] = any(c.isdigit() for c in password)
        self.reqs[4]["valid"] = any(c in special_chars for c in password)

        for req in self.reqs:
            lbl = self.labels[req["id"]]
            if req["valid"]:
                lbl.setStyleSheet("color: #10B981; font-size: 11px; font-weight: 600; font-family: 'Times New Roman';")
            else:
                lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600; font-family: 'Times New Roman';")


class PremiumInputGroup(QWidget):
    """
    Custom text field component with label, styled input box, icon, and error label.
    """
    textChanged = pyqtSignal(str)

    def __init__(self, label_text, placeholder, icon_path, is_password=False, parent=None):
        super().__init__(parent)
        self.is_password = is_password
        self.has_error = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.label = QLabel(label_text)
        self.label.setObjectName("FormLabel")
        self.label.setStyleSheet("font-weight: bold; font-size: 12px; color: #191c1e; font-family: 'Times New Roman'; border: none;")
        layout.addWidget(self.label)

        self.container = QFrame()
        self.container.setObjectName("InputContainer")
        self.container.setFixedHeight(44)

        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(12, 0, 12, 0)
        container_layout.setSpacing(8)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(18, 18)
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            self.icon_label.setPixmap(pixmap.scaled(
                18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            ))
        container_layout.addWidget(self.icon_label)

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText(placeholder)
        self.line_edit.setStyleSheet("background: transparent; border: none; padding: 0; font-size: 13px; font-family: 'Times New Roman';")
        if is_password:
            self.line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.line_edit.textChanged.connect(self.textChanged.emit)
        container_layout.addWidget(self.line_edit)

        self.toggle_btn = None
        if is_password:
            self.toggle_btn = QPushButton()
            self.toggle_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.toggle_btn.setFixedSize(18, 18)
            self.toggle_btn.setStyleSheet("background: transparent; border: none; padding: 0;")
            self.eye_open_pixmap = QPixmap("assets/icons/eye.png").scaled(
                18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.eye_closed_pixmap = QPixmap("assets/icons/eye_closed.png").scaled(
                18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.toggle_btn.setIcon(QIcon(self.eye_closed_pixmap))
            self.toggle_btn.clicked.connect(self.toggle_password_visibility)
            container_layout.addWidget(self.toggle_btn)

        layout.addWidget(self.container)

        self.error_label = QLabel(" ")
        self.error_label.setFixedHeight(18)
        self.error_label.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 500; font-family: 'Times New Roman';")
        layout.addWidget(self.error_label)
        
        self.set_container_style(focused=False)

    def set_container_style(self, focused=False):
        if self.has_error:
            border_style = "border: 1px solid #EF4444;"
        elif focused:
            border_style = "border: 2px solid #0037b0;"
        else:
            border_style = "border: 1px solid #c4c5d7;"

        self.container.setStyleSheet(f"""
            QFrame#InputContainer {{
                background-color: #FFFFFF;
                {border_style}
                border-radius: 6px;
            }}
        """)

    def set_error(self, message):
        if message:
            self.has_error = True
            self.error_label.setText(message)
        else:
            self.has_error = False
            self.error_label.setText(" ")
        self.set_container_style(focused=self.line_edit.hasFocus())

    def toggle_password_visibility(self):
        if self.line_edit.echoMode() == QLineEdit.EchoMode.Password:
            self.line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            if self.toggle_btn:
                self.toggle_btn.setIcon(QIcon(self.eye_open_pixmap))
        else:
            self.line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            if self.toggle_btn:
                self.toggle_btn.setIcon(QIcon(self.eye_closed_pixmap))

    def text(self):
        return self.line_edit.text()

    def setText(self, text):
        self.line_edit.setText(text)

    def clear(self):
        self.line_edit.clear()
        self.set_error(None)

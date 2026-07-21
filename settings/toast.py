from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QPropertyAnimation, QTimer
from PyQt6.QtGui import QColor, QFont

class Toast(QWidget):
    """
    A premium animated toast notification widget for desktop notifications.
    Supports fade animations, auto-dismiss, custom icons, and theme integration.
    """
    def __init__(self, parent_widget, message, toast_type="success"):
        super().__init__(parent_widget)
        self.parent_widget = parent_widget
        self.toast_type = toast_type

        # Ensure it floats above other widgets
        self.setWindowFlags(Qt.WindowType.SubWindow)
        
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Style based on type
        self.icon_label = QLabel()
        self.icon_label.setStyleSheet("font-size: 14px; font-weight: bold; background: transparent;")
        
        self.msg_label = QLabel(message)
        self.msg_label.setWordWrap(True)
        self.msg_label.setStyleSheet("font-size: 13px; font-weight: 600; background: transparent;")
        
        if toast_type == "success":
            self.icon_label.setText("✓")
            self.icon_label.setStyleSheet("color: #10B981; font-size: 14px; font-weight: bold;") # Emerald 500
            self.msg_label.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 600;")
            bg_style = "background-color: #1E293B; border: 1px solid #10B981; border-radius: 10px;"
        elif toast_type == "error":
            self.icon_label.setText("❌")
            self.icon_label.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: bold;") # Red 500
            self.msg_label.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 600;")
            bg_style = "background-color: #1E293B; border: 1px solid #EF4444; border-radius: 10px;"
        else: # info / processing
            self.icon_label.setText("ℹ️")
            self.icon_label.setStyleSheet("color: #3B82F6; font-size: 14px; font-weight: bold;") # Blue 500
            self.msg_label.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 600;")
            bg_style = "background-color: #1E293B; border: 1px solid #3B82F6; border-radius: 10px;"

        self.setObjectName("SettingsToastWidget")
        self.setStyleSheet(f"QWidget#SettingsToastWidget {{ {bg_style} }}")
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.msg_label)

        # Set sizing
        self.adjustSize()
        if self.width() > 360:
            self.setFixedWidth(360)
            self.adjustSize()

        # Set up opacity for animation
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.setWindowOpacity(0.0)
        
        # Position toast
        self.update_position()
        
        # Connect position update if parent resizes
        if hasattr(self.parent_widget, "installEventFilter"):
            self.parent_widget.installEventFilter(self)

    def update_position(self):
        """Places toast in the top-right corner of its parent widget."""
        parent_rect = self.parent_widget.rect()
        x = parent_rect.right() - self.width() - 24
        y = parent_rect.top() + 24
        self.move(x, y)

    def eventFilter(self, watched, event):
        # Update toast position if the parent widget resizes
        if watched == self.parent_widget and event.type() == event.Type.Resize:
            self.update_position()
        return super().eventFilter(watched, event)

    def show_toast(self):
        """Fades in and schedules auto dismiss."""
        self.show()
        self.raise_()
        self.update_position()

        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(250)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

        # Auto dismiss after 3 seconds
        QTimer.singleShot(3000, self.fade_out)

    def fade_out(self):
        """Fades out and deletes itself."""
        self.anim_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_out.setDuration(250)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.finished.connect(self.deleteLater)
        self.anim_out.start()

    @classmethod
    def success(cls, parent, message):
        """Convenience method to show success toast."""
        toast = cls(parent, message, "success")
        toast.show_toast()
        return toast

    @classmethod
    def error(cls, parent, message):
        """Convenience method to show error toast."""
        toast = cls(parent, message, "error")
        toast.show_toast()
        return toast

    @classmethod
    def info(cls, parent, message):
        """Convenience method to show info toast."""
        toast = cls(parent, message, "info")
        toast.show_toast()
        return toast

    @classmethod
    def warning(cls, parent, message):
        """Convenience method for warning toast."""
        toast = cls(parent, message, "info")
        toast.show_toast()
        return toast

    @classmethod
    def display_toast(cls, parent, message, toast_type="info"):
        """Convenience method to show toast by type string."""
        if toast_type == "success":
            return cls.success(parent, message)
        elif toast_type == "error":
            return cls.error(parent, message)
        elif toast_type == "warning":
            return cls.warning(parent, message)
        else:
            return cls.info(parent, message)

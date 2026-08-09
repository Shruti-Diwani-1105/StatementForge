from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QPropertyAnimation, QPoint, QTimer
from PyQt6.QtGui import QColor, QFont

class Toast(QWidget):
    """
    A premium enterprise toast notification widget for desktop applications.
    Displays bottom-right aligned notifications with smooth right-side slide animations,
    theme adaptability (Light/Dark), stacked vertical positioning, and auto-dismiss.
    """
    def __init__(self, parent_widget, message, title=None, toast_type="success"):
        super().__init__(parent_widget)
        self.parent_widget = parent_widget
        self.toast_type = toast_type.lower() if toast_type else "success"
        
        # Determine theme state
        from utils.theme_manager import ThemeManager
        self.is_dark = (ThemeManager.get_theme() == "dark")
        
        # SubWindow flag to stay on top of parent surface
        self.setWindowFlags(Qt.WindowType.SubWindow)
        
        # Track active instances on parent for stacking
        if not hasattr(self.parent_widget, "_active_toasts"):
            self.parent_widget._active_toasts = []
        if self not in self.parent_widget._active_toasts:
            self.parent_widget._active_toasts.append(self)
        
        # Configure Main Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)
        
        # Default Titles & Descriptions
        if not title:
            titles = {
                "success": "Changes saved",
                "info": "Information",
                "warning": "Warning",
                "error": "Error"
            }
            title = titles.get(self.toast_type, "Notification")
            
        if not message:
            messages = {
                "success": "Your notification settings have been saved successfully.",
                "info": "Information update processed.",
                "warning": "Please review your input configuration.",
                "error": "Unable to complete requested operation."
            }
            message = messages.get(self.toast_type, "")

        # 1. Circular Icon Badge
        self.icon_badge = QLabel()
        self.icon_badge.setFixedSize(28, 28)
        self.icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icon & Color definitions
        if self.toast_type == "success":
            symbol = "✓"
            icon_color = "#10B981"
            circle_bg = "rgba(16, 185, 129, 0.15)" if self.is_dark else "#ECFDF5"
            border_color = "rgba(16, 185, 129, 0.3)" if self.is_dark else "#A7F3D0"
        elif self.toast_type == "error":
            symbol = "✕"
            icon_color = "#EF4444"
            circle_bg = "rgba(239, 68, 68, 0.15)" if self.is_dark else "#FEF2F2"
            border_color = "rgba(239, 68, 68, 0.3)" if self.is_dark else "#FECACA"
        elif self.toast_type == "warning":
            symbol = "⚠"
            icon_color = "#F59E0B"
            circle_bg = "rgba(245, 158, 11, 0.15)" if self.is_dark else "#FFFBEB"
            border_color = "rgba(245, 158, 11, 0.3)" if self.is_dark else "#FDE68A"
        else: # info
            symbol = "ℹ"
            icon_color = "#3B82F6"
            circle_bg = "rgba(59, 130, 246, 0.15)" if self.is_dark else "#EFF6FF"
            border_color = "rgba(59, 130, 246, 0.3)" if self.is_dark else "#BFDBFE"
            
        self.icon_badge.setText(symbol)
        self.icon_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {circle_bg};
                color: {icon_color};
                border: 1px solid {border_color};
                border-radius: 14px;
                font-size: 13px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(self.icon_badge, 0, Qt.AlignmentFlag.AlignTop)

        # 2. Text Column (Title + Description)
        text_column = QWidget()
        text_column.setStyleSheet("background: transparent;")
        col_layout = QVBoxLayout(text_column)
        col_layout.setContentsMargins(0, 0, 0, 0)
        col_layout.setSpacing(2)
        
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet(f"""
            QLabel {{
                color: {"#F8FAFC" if self.is_dark else "#0F172A"};
                font-size: 13.5px;
                font-weight: 700;
                background: transparent;
            }}
        """)
        col_layout.addWidget(self.title_lbl)

        if message and message.strip() != title.strip():
            self.desc_lbl = QLabel(message)
            self.desc_lbl.setWordWrap(True)
            self.desc_lbl.setStyleSheet(f"""
                QLabel {{
                    color: {"#94A3B8" if self.is_dark else "#64748B"};
                    font-size: 12px;
                    font-weight: 400;
                    background: transparent;
                }}
            """)
            col_layout.addWidget(self.desc_lbl)
            
        layout.addWidget(text_column, 1)

        # 3. Close Button ×
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {"#94A3B8" if self.is_dark else "#94A3B8"};
                font-size: 16px;
                font-weight: 400;
                line-height: 1;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                color: {"#F8FAFC" if self.is_dark else "#0F172A"};
                background-color: {"#334155" if self.is_dark else "#F1F5F9"};
            }}
        """)
        self.close_btn.clicked.connect(self.fade_out)
        layout.addWidget(self.close_btn, 0, Qt.AlignmentFlag.AlignTop)

        # Card Container Stylesheet
        bg_color = "#1E293B" if self.is_dark else "#FFFFFF"
        border_col = "#334155" if self.is_dark else "#E2E8F0"
        
        self.setObjectName("EnterpriseToastCard")
        self.setStyleSheet(f"""
            QWidget#EnterpriseToastCard {{
                background-color: {bg_color};
                border: 1px solid {border_col};
                border-radius: 12px;
            }}
        """)
        
        self.setFixedWidth(360)
        self.adjustSize()

        # Opacity & Position Animation Setup
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.setWindowOpacity(0.0)
        
        self.update_position()
        
        if hasattr(self.parent_widget, "installEventFilter"):
            self.parent_widget.installEventFilter(self)

    def update_position(self):
        """Places toast in the bottom-right corner, handling vertical stacking of active toasts."""
        parent_rect = self.parent_widget.rect()
        target_x = max(24, parent_rect.right() - self.width() - 24)
        
        offset = 0
        if hasattr(self.parent_widget, "_active_toasts"):
            active = [t for t in self.parent_widget._active_toasts if t.isVisible() and t != self]
            for t in active:
                offset += t.height() + 10
                
        target_y = max(24, parent_rect.bottom() - self.height() - 24 - offset)
        self.move(target_x, target_y)

    def eventFilter(self, watched, event):
        if watched == self.parent_widget and event.type() == event.Type.Resize:
            self.update_position()
        return super().eventFilter(watched, event)

    def show_toast(self):
        """Slides in from right and fades in, then schedules 3.5s auto dismiss."""
        self.show()
        self.raise_()
        self.update_position()

        # Opacity animation
        self.anim_opacity = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_opacity.setDuration(280)
        self.anim_opacity.setStartValue(0.0)
        self.anim_opacity.setEndValue(1.0)
        self.anim_opacity.start()

        # Position slide in animation
        current_pos = self.pos()
        start_pos = QPoint(current_pos.x() + 30, current_pos.y())
        
        self.anim_pos = QPropertyAnimation(self, b"pos")
        self.anim_pos.setDuration(280)
        self.anim_pos.setStartValue(start_pos)
        self.anim_pos.setEndValue(current_pos)
        self.anim_pos.start()

        # Auto dismiss after 3 seconds
        QTimer.singleShot(3000, self.fade_out)

    def fade_out(self):
        """Slides right and fades out before destroying widget."""
        if not self.isVisible():
            return
            
        if hasattr(self.parent_widget, "_active_toasts") and self in self.parent_widget._active_toasts:
            self.parent_widget._active_toasts.remove(self)

        self.anim_out_op = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_out_op.setDuration(220)
        self.anim_out_op.setStartValue(1.0)
        self.anim_out_op.setEndValue(0.0)

        current_pos = self.pos()
        end_pos = QPoint(current_pos.x() + 30, current_pos.y())

        self.anim_out_pos = QPropertyAnimation(self, b"pos")
        self.anim_out_pos.setDuration(220)
        self.anim_out_pos.setStartValue(current_pos)
        self.anim_out_pos.setEndValue(end_pos)

        self.anim_out_op.finished.connect(self.deleteLater)
        self.anim_out_op.start()
        self.anim_out_pos.start()

    @classmethod
    def success(cls, parent, message="Your notification settings have been saved successfully.", title="Changes saved"):
        """Convenience method to show success toast."""
        toast = cls(parent, message, title=title, toast_type="success")
        toast.show_toast()
        return toast

    @classmethod
    def error(cls, parent, message="Unable to complete requested operation.", title="Error"):
        """Convenience method to show error toast."""
        toast = cls(parent, message, title=title, toast_type="error")
        toast.show_toast()
        return toast

    @classmethod
    def info(cls, parent, message="Information update processed.", title="Information"):
        """Convenience method to show info toast."""
        toast = cls(parent, message, title=title, toast_type="info")
        toast.show_toast()
        return toast

    @classmethod
    def warning(cls, parent, message="Please review your input configuration.", title="Warning"):
        """Convenience method for warning toast."""
        toast = cls(parent, message, title=title, toast_type="warning")
        toast.show_toast()
        return toast

    @classmethod
    def display_toast(cls, parent, message, title=None, toast_type="info"):
        """Convenience method to show toast by type string."""
        if toast_type == "success":
            return cls.success(parent, message, title=title or "Changes saved")
        elif toast_type == "error":
            return cls.error(parent, message, title=title or "Error")
        elif toast_type == "warning":
            return cls.warning(parent, message, title=title or "Warning")
        else:
            return cls.info(parent, message, title=title or "Information")

from PyQt6.QtWidgets import QAbstractButton
from PyQt6.QtCore import Qt, pyqtProperty, QPropertyAnimation, QEasingCurve, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen

class ToggleSwitch(QAbstractButton):
    """
    A premium animated custom toggle switch widget mimicking iOS style.
    Features smooth thumb transition animation, hover effects, and theme integration.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(50, 26)
        
        # Animatable thumb position (0.0 means fully left, 1.0 means fully right)
        self._thumb_position = 0.0
        
        # Animation setup
        self.animation = QPropertyAnimation(self, b"thumb_position", self)
        self.animation.setDuration(180)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # State variables for hover/press
        self.hovered = False
        
        # Theme integration
        from utils.theme_manager import ThemeManager
        self.current_theme = ThemeManager.get_theme()
        
    @pyqtProperty(float)
    def thumb_position(self):
        return self._thumb_position
        
    @thumb_position.setter
    def thumb_position(self, pos):
        self._thumb_position = pos
        self.update()

    def update_theme(self, theme):
        self.current_theme = theme
        self.update()

    def nextCheckState(self):
        super().nextCheckState()
        # Trigger animation on check state change
        end_val = 1.0 if self.isChecked() else 0.0
        self.animation.stop()
        self.animation.setStartValue(self._thumb_position)
        self.animation.setEndValue(end_val)
        self.animation.start()

    def setChecked(self, checked):
        super().setChecked(checked)
        self.animation.stop()
        self._thumb_position = 1.0 if checked else 0.0
        self.update()

    def enterEvent(self, event):
        self.hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Color definitions based on state
        if self.isChecked():
            # Active accent color (Blue)
            bg_color = QColor("#2563EB") if self.hovered else QColor("#3B82F6")
            thumb_color = QColor("#FFFFFF")
        else:
            # Inactive gray/slate based on theme
            if self.current_theme == "dark":
                bg_color = QColor("#475569") if self.hovered else QColor("#334155")
            else:
                bg_color = QColor("#94A3B8") if self.hovered else QColor("#CBD5E1")
            thumb_color = QColor("#FFFFFF")
            
        # Draw background pill
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        rect = QRectF(0, 0, self.width(), self.height())
        painter.drawRoundedRect(rect, 13, 13)
        
        # Calculate thumb size and position
        thumb_diameter = 20
        margin = 3
        start_x = margin
        end_x = self.width() - thumb_diameter - margin
        
        current_x = start_x + (end_x - start_x) * self._thumb_position
        current_y = (self.height() - thumb_diameter) / 2
        
        # Draw thumb
        painter.setBrush(QBrush(thumb_color))
        painter.drawEllipse(QRectF(current_x, current_y, thumb_diameter, thumb_diameter))
        
        painter.end()

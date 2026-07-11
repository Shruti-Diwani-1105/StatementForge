from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QCursor

class SettingsSidebarItem(QPushButton):
    """
    Horizontal checkable button representing a tab in the top segmented Settings bar.
    Delegates all visual styling to the centralized theme QSS files.
    """
    def __init__(self, label, key, icon_name, parent=None):
        super().__init__(label, parent)
        self.key = key
        self.setCheckable(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setObjectName("SettingsTabButton")
        self.setFixedHeight(36)
        
        # Load icon dynamically
        icon_path = f"assets/icons/{icon_name}.png"
        self.setIcon(QIcon(icon_path))
        self.setIconSize(QSize(16, 16))

    def update_theme_style(self, theme):
        # Kept for interface compatibility but styling is handled globally in QSS
        pass

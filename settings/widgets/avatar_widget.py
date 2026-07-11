from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class AvatarWidget(QWidget):
    """
    A custom circular avatar badge for the Account profile view.
    Displays user initials dynamically and supports updating sizes or theme colors.
    """
    def __init__(self, size=96, parent=None):
        super().__init__(parent)
        self.size_val = size
        self.initials = "U"
        
        # Layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Label circle
        self.lbl = QLabel(self.initials, self)
        self.lbl.setFixedSize(self.size_val, self.size_val)
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Initial styling
        font_sz = int(self.size_val * 0.4)
        self.lbl.setStyleSheet(f"""
            QLabel {{
                background-color: #2563EB; /* Premium Blue */
                color: #FFFFFF;
                font-weight: 800;
                font-size: {font_sz}px;
                border-radius: {self.size_val // 2}px;
                border: none;
            }}
        """)
        self.layout.addWidget(self.lbl)

    def set_name(self, full_name):
        """Generates initials from the full name and updates text."""
        if not full_name or not full_name.strip():
            self.initials = "U"
        else:
            parts = full_name.strip().split()
            if len(parts) >= 2:
                self.initials = (parts[0][0] + parts[-1][0]).upper()
            elif len(parts) == 1:
                self.initials = parts[0][:2].upper() if len(parts[0]) >= 2 else parts[0][0].upper()
            else:
                self.initials = "U"
        self.lbl.setText(self.initials)

    def update_theme(self, theme):
        """Adapts styling based on theme if required."""
        font_sz = int(self.size_val * 0.4)
        # We keep the solid blue backdrop as it is premium and offers good contrast in both themes
        # but we can adjust border highlights if desired.
        border_qss = "border: 2px solid #38BDF8;" if theme == "dark" else "border: none;"
        self.lbl.setStyleSheet(f"""
            QLabel {{
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: 800;
                font-size: {font_sz}px;
                border-radius: {self.size_val // 2}px;
                {border_qss}
            }}
        """)

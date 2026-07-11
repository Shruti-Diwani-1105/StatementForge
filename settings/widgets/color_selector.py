from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QCursor

class ColorSelector(QWidget):
    """
    A custom horizontal selector widget for picking application accent colors.
    Options: Blue, Green, Purple, Orange.
    Draws a distinct selection outline and emits a colorChanged signal.
    """
    colorChanged = pyqtSignal(str) # Emits the name of the chosen color ("blue", "green", "purple", "orange")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ColorSelector")
        
        # Horizontal Layout
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(12)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # Swatches definition (name, hex_color)
        self.colors = [
            ("blue", "#2563EB"),
            ("green", "#16A34A"),
            ("purple", "#7C3AED"),
            ("orange", "#EA580C")
        ]
        
        self.buttons = {}
        self.selected_color = "blue"
        
        # Create buttons
        for name, hex_color in self.colors:
            btn = QPushButton(self)
            btn.setFixedSize(32, 32)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda checked, n=name: self.set_selected_color(n))
            self.main_layout.addWidget(btn)
            self.buttons[name] = (btn, hex_color)
            
        self.update_buttons_style()

    def set_selected_color(self, name):
        """Sets selected color visually and emits colorChanged signal."""
        if name not in self.buttons:
            name = "blue"
            
        if self.selected_color != name:
            self.selected_color = name
            self.update_buttons_style()
            self.colorChanged.emit(name)

    def get_selected_color(self):
        """Returns currently selected color name."""
        return self.selected_color

    def update_buttons_style(self):
        """Redraws background and border styling for all swatches."""
        for name, (btn, hex_color) in self.buttons.items():
            if name == self.selected_color:
                # Active selection border
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {hex_color};
                        border: 3px solid #0F172A;
                        border-radius: 16px;
                    }}
                """)
            else:
                # Standard swatch
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {hex_color};
                        border: 1px solid #E2E8F0;
                        border-radius: 16px;
                    }}
                    QPushButton:hover {{
                        border: 2px solid #94A3B8;
                    }}
                """)

    def update_theme(self, theme):
        """Updates selections when theme is dark, to use a lighter border for selection contrast."""
        for name, (btn, hex_color) in self.buttons.items():
            if name == self.selected_color:
                border_color = "#F8FAFC" if theme == "dark" else "#0F172A"
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {hex_color};
                        border: 3px solid {border_color};
                        border-radius: 16px;
                    }}
                """)
            else:
                border_color = "#334155" if theme == "dark" else "#E2E8F0"
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {hex_color};
                        border: 1px solid {border_color};
                        border-radius: 16px;
                    }}
                """)

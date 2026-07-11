from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

class SettingCard(QFrame):
    """
    A premium card widget for grouping related settings.
    Features rounded corners, padding, and
    an optional header layout (title & description).
    """
    def __init__(self, title, description=None, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingCardFrame")
        
        # Main Layout
        self.card_layout = QVBoxLayout(self)
        self.card_layout.setContentsMargins(24, 24, 24, 24)
        self.card_layout.setSpacing(16)
        
        # Header Layout
        if title:
            self.header_layout = QVBoxLayout()
            self.header_layout.setSpacing(4)
            
            self.title_lbl = QLabel(title)
            self.title_lbl.setStyleSheet("font-weight: 700; font-size: 16px; color: #0F172A;")
            self.title_lbl.setObjectName("SettingCardTitle")
            self.header_layout.addWidget(self.title_lbl)
            
            if description:
                self.desc_lbl = QLabel(description)
                self.desc_lbl.setStyleSheet("color: #64748B; font-size: 13px; line-height: 18px;")
                self.desc_lbl.setWordWrap(True)
                self.desc_lbl.setObjectName("SettingCardDesc")
                self.header_layout.addWidget(self.desc_lbl)
                
            self.card_layout.addLayout(self.header_layout)
            
        # Content layout for settings inputs
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(12)
        self.card_layout.addLayout(self.content_layout)
        
        # Local Theme Styling
        from utils.theme_manager import ThemeManager
        self.update_theme_style(ThemeManager.get_theme())

    def update_theme_style(self, theme):
        """Updates internal stylesheet variables dynamically based on theme."""
        if theme == "dark":
            self.setStyleSheet("""
                QFrame#SettingCardFrame {
                    background-color: #1E293B; /* Slate 800 */
                    border: 1px solid #334155; /* Slate 700 */
                    border-radius: 12px;
                }
            """)
            if hasattr(self, "title_lbl"):
                self.title_lbl.setStyleSheet("font-weight: 700; font-size: 16px; color: #F8FAFC;")
            if hasattr(self, "desc_lbl"):
                self.desc_lbl.setStyleSheet("color: #94A3B8; font-size: 13px; line-height: 18px;")
        else:
            self.setStyleSheet("""
                QFrame#SettingCardFrame {
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0; /* Slate 200 */
                    border-radius: 12px;
                }
            """)
            if hasattr(self, "title_lbl"):
                self.title_lbl.setStyleSheet("font-weight: 700; font-size: 16px; color: #0F172A;")
            if hasattr(self, "desc_lbl"):
                self.desc_lbl.setStyleSheet("color: #64748B; font-size: 13px; line-height: 18px;")

    def add_widget(self, widget):
        """Adds a widget to the card's content area."""
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        """Adds a nested layout to the card's content area."""
        self.content_layout.addLayout(layout)

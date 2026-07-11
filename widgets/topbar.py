from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon, QCursor

class SearchBar(QLineEdit):
    """Modern search bar with embedded icon overlay."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SearchBox")
        self.setPlaceholderText("Search transactions, statements...")
        
        # Magnifying glass overlay
        self.icon_label = QLabel(self)
        pixmap = QPixmap("assets/icons/search.png")
        if not pixmap.isNull():
            self.icon_label.setPixmap(pixmap.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.icon_label.setStyleSheet("background: transparent; border: none; padding: 0px;")
        self.icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.icon_label.setFixedSize(16, 16)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Center icon vertically inside the text field
        self.icon_label.move(14, (self.height() - 16) // 2)


class ClickableProfileWidget(QFrame):
    """Single clickable user profile widget featuring hover and cursor animations."""
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ClickableProfileWidget")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self.setStyleSheet("""
            QFrame#ClickableProfileWidget {
                background-color: transparent;
                border-radius: 8px;
                border: none;
            }
            QFrame#ClickableProfileWidget:hover {
                background-color: #EFF6FF; /* Soft Blue hover highlight */
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 12, 6)
        layout.setSpacing(10)

        # Large-ish circular avatar badge
        self.avatar = QLabel("")
        self.avatar.setFixedSize(36, 36)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar.setStyleSheet("""
            QLabel {
                background-color: #2563EB; /* Solid Blue Background */
                color: #FFFFFF;
                font-weight: 700;
                font-size: 15px;
                border-radius: 18px;
                border: none;
            }
        """)
        layout.addWidget(self.avatar)

        # Profile Full Name
        self.user_name = QLabel("")
        self.user_name.setStyleSheet("font-weight: 600; font-size: 13px; border: none; background: transparent;")
        layout.addWidget(self.user_name)
        
        # Profile Dropdown Arrow
        self.arrow = QLabel("▼")
        self.arrow.setObjectName("ProfileArrow")
        self.arrow.setStyleSheet("font-size: 8px; border: none; background: transparent;")
        layout.addWidget(self.arrow)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def update_profile(self, full_name):
        """Displays user's full name and first letter of name in avatar."""
        self.user_name.setText(full_name)
        
        initial = ""
        if full_name.strip():
            initial = full_name.strip()[0].upper()
        self.avatar.setText(initial)


class TopBar(QFrame):
    """
    Top navigation bar containing search, notification system, and user profile metadata.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TopBar")
        self.setFixedHeight(70)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(16)
        
        # 1. Search Bar
        self.search_bar = SearchBar()
        self.search_bar.setFixedWidth(360)
        layout.addWidget(self.search_bar)
        
        # Spacer
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # 2. Theme Toggle Button
        from utils.theme_manager import ThemeManager
        current_theme = ThemeManager.get_theme()
        
        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("ThemeButton")
        self.theme_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.theme_btn.setFixedSize(36, 36)
        self.update_theme_icon(current_theme)
        self.theme_btn.clicked.connect(self.toggle_theme)
        layout.addWidget(self.theme_btn)
        
        # 3. Notification Button
        self.noti_btn = QPushButton()
        self.noti_btn.setObjectName("NotificationButton")
        self.noti_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        noti_pixmap = QPixmap("assets/icons/bell.png")
        if not noti_pixmap.isNull():
            self.noti_btn.setIcon(QIcon(noti_pixmap))
            self.noti_btn.setIconSize(QSize(18, 18))
        self.noti_btn.setFixedSize(36, 36)
        layout.addWidget(self.noti_btn)
        
        # 4. Clickable Profile Group
        self.profile_widget = ClickableProfileWidget()
        layout.addWidget(self.profile_widget)

    def toggle_theme(self):
        """Toggles the current application theme and updates the icon."""
        from utils.theme_manager import ThemeManager
        new_theme = ThemeManager.toggle_theme()
        self.update_theme_icon(new_theme)
        
        # Propagate theme change to the main controller window
        win = self.window()
        if win and hasattr(win, "sync_theme_styles"):
            win.sync_theme_styles(new_theme)

    def update_theme_icon(self, theme):
        """Updates the button character representation based on the theme."""
        if theme == "dark":
            self.theme_btn.setText("☀️")
        else:
            self.theme_btn.setText("🌙")

    def update_profile(self, full_name):
        """Updates the active user's avatar letter and name details."""
        self.profile_widget.update_profile(full_name)

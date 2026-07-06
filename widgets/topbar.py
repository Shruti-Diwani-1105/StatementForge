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
        self.icon_label.move(12, (self.height() - 16) // 2)


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
        self.user_name.setStyleSheet("font-weight: 600; font-size: 13px; color: #0F172A; border: none; background: transparent;")
        layout.addWidget(self.user_name)

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
        self.setFixedHeight(70)
        self.setStyleSheet("background-color: #FFFFFF; border-bottom: 1px solid #E2E8F0;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(16)
        
        # 1. Search Bar
        self.search_bar = SearchBar()
        self.search_bar.setFixedWidth(360)
        layout.addWidget(self.search_bar)
        
        # Spacer
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # 2. Notification Button
        self.noti_btn = QPushButton()
        self.noti_btn.setObjectName("NotificationButton")
        self.noti_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        noti_pixmap = QPixmap("assets/icons/bell.png")
        if not noti_pixmap.isNull():
            self.noti_btn.setIcon(QIcon(noti_pixmap))
            self.noti_btn.setIconSize(QSize(18, 18))
        self.noti_btn.setFixedSize(36, 36)
        layout.addWidget(self.noti_btn)
        
        # 3. Clickable Profile Group
        self.profile_widget = ClickableProfileWidget()
        layout.addWidget(self.profile_widget)

    def update_profile(self, full_name):
        """Updates the active user's avatar letter and name details."""
        self.profile_widget.update_profile(full_name)

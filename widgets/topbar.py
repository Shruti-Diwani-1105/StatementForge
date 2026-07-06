from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt, QSize
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
        
        # 3. Profile Group
        profile_layout = QHBoxLayout()
        profile_layout.setSpacing(10)
        
        # Initials badge (circular avatar)
        self.avatar = QLabel("JD")
        self.avatar.setFixedSize(36, 36)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar.setStyleSheet("""
            QLabel {
                background-color: #3B82F6;
                color: #FFFFFF;
                font-weight: 600;
                font-size: 13px;
                border-radius: 18px;
                border: none;
            }
        """)
        profile_layout.addWidget(self.avatar)
        
        # Profile Name details
        name_details = QVBoxLayout()
        name_details.setSpacing(0)
        
        user_name = QLabel("John Doe")
        user_name.setStyleSheet("font-weight: 600; font-size: 13px; color: #0F172A; border: none;")
        
        user_role = QLabel("Administrator")
        user_role.setStyleSheet("font-size: 11px; color: #64748B; border: none;")
        
        name_details.addWidget(user_name)
        name_details.addWidget(user_role)
        profile_layout.addLayout(name_details)
        
        layout.addLayout(profile_layout)

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QButtonGroup, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QIcon, QCursor

class Sidebar(QFrame):
    """
    Left-hand sidebar menu for application navigation. Exposes signals when items
    are clicked to switch pages.
    """
    nav_changed = pyqtSignal(str)  # Emits the page key, e.g. "dashboard", "upload", etc.
    logout_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarFrame")
        
        # Setup vertical layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 24, 16, 24)
        layout.setSpacing(8)
        
        # 1. Header (Logo + Title)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        
        logo_label = QLabel()
        logo_label.setFixedSize(32, 32)
        logo_pixmap = QPixmap("assets/logo.png")
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        header_layout.addWidget(logo_label)
        
        title_info = QVBoxLayout()
        title_info.setSpacing(0)
        
        app_title = QLabel("StatementForge")
        app_title.setObjectName("SidebarAppTitle")
        app_title.setMinimumHeight(24)
        app_title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        app_version = QLabel("v1.0")
        app_version.setObjectName("SidebarAppVersion")
        
        title_info.addWidget(app_title)
        title_info.addWidget(app_version)
        header_layout.addLayout(title_info)
        
        layout.addLayout(header_layout)
        
        # Spacer below header
        layout.addSpacing(24)
        
        # 2. Navigation Group
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        
        # Define menu items (label, key, icon filename)
        self.menu_items = [
            ("Dashboard", "dashboard", "dashboard"),
            ("Upload Statement", "upload", "upload"),
            ("AI Auditor", "ai_auditor", "ai"),
            ("Duplicate Finder", "duplicate_finder", "duplicate"),
            ("Statement History", "history", "history"),
            ("Reports", "reports", "reports"),
            ("Settings", "settings", "settings")
        ]
        
        self.buttons = {}
        for label, key, icon_name in self.menu_items:
            btn = QPushButton(label)
            btn.setObjectName("SidebarButton")
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            
            # Load icon
            icon_path = f"assets/icons/{icon_name}.png"
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(18, 18))
            
            # Set default checked item to dashboard
            if key == "dashboard":
                btn.setChecked(True)
                
            # Connect clicked signal
            btn.clicked.connect(lambda checked, k=key: self.nav_changed.emit(k))
            
            self.btn_group.addButton(btn)
            layout.addWidget(btn)
            self.buttons[key] = btn
            
        # Spacer to push logout to bottom
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        # 3. Logout Button
        self.logout_btn = QPushButton("Logout")
        self.logout_btn.setObjectName("LogoutButton")
        self.logout_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.logout_btn.setIcon(QIcon("assets/icons/logout.png"))
        self.logout_btn.setIconSize(QSize(18, 18))
        self.logout_btn.clicked.connect(self.logout_clicked.emit)
        
        layout.addWidget(self.logout_btn)
        
        self.setFixedWidth(260)

    def set_active_page(self, key):
        """Sets a specific sidebar button as checked programmatically without triggering signals again."""
        if key in self.buttons:
            self.buttons[key].setChecked(True)

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QGridLayout, QFrame, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from widgets.custom_button import PrimaryButton, SecondaryButton
from widgets.custom_card import CustomCard

class WelcomeScreen(QWidget):
    """
    Landing / Welcome Screen of the application. Displays branding,
    information cards, and shortcuts to register or login.
    """
    gotoLogin = pyqtSignal()
    gotoRegister = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Header Navigation Bar (Logo on left, Auth Buttons on right)
        header_widget = QFrame()
        header_widget.setObjectName("HeaderWidget")
        header_widget.setStyleSheet("""
            QFrame#HeaderWidget {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E2E8F0;
            }
        """)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(32, 16, 32, 16)
        
        # Header Left: Logo & Name
        left_header = QHBoxLayout()
        left_header.setSpacing(12)
        logo_label = QLabel()
        logo_label.setFixedSize(36, 36)
        logo_pixmap = QPixmap("assets/logo.png")
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        left_header.addWidget(logo_label)
        
        app_name_label = QLabel("StatementForge")
        app_name_label.setMinimumHeight(30)
        app_name_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        app_name_label.setStyleSheet("font-weight: 700; font-size: 18px; color: #0F172A; border: 0px solid transparent; padding-bottom: 4px;")
        left_header.addWidget(app_name_label)
        header_layout.addLayout(left_header)
        
        header_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Header Right: Auth Buttons
        right_header = QHBoxLayout()
        right_header.setSpacing(12)
        
        self.login_nav_btn = SecondaryButton("Login")
        self.login_nav_btn.clicked.connect(self.gotoLogin.emit)
        right_header.addWidget(self.login_nav_btn)
        
        self.register_nav_btn = PrimaryButton("Register")
        self.register_nav_btn.clicked.connect(self.gotoRegister.emit)
        right_header.addWidget(self.register_nav_btn)
        
        header_layout.addLayout(right_header)
        main_layout.addWidget(header_widget)
        
        # 2. Central Scroll Area
        self.setObjectName("WelcomeBackground")
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("background-color: transparent; border: none;")
        
        scroll_content = QWidget()
        scroll_content.setObjectName("ScrollContent")
        scroll_content.setStyleSheet("background-color: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(64, 48, 64, 48)
        scroll_layout.setSpacing(32)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        
        # Hero Branding Section
        hero_widget = QWidget()
        hero_layout = QVBoxLayout(hero_widget)
        hero_layout.setSpacing(12)
        hero_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        hero_title = QLabel("StatementForge")
        hero_title.setMinimumHeight(64)
        hero_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_title.setStyleSheet("font-size: 42px; font-weight: 800; color: #0F172A; letter-spacing: -1px; border: 0px solid transparent; padding-bottom: 8px;")
        
        hero_subtitle = QLabel("Multi-Bank Financial Statement Parser & Verification Tool")
        hero_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_subtitle.setStyleSheet("font-size: 18px; font-weight: 600; color: #2563EB;")
        
        hero_desc = QLabel(
            "An intelligent offline desktop application that extracts, verifies, and organizes "
            "financial transactions from multiple bank statement formats."
        )
        hero_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_desc.setWordWrap(True)
        hero_desc.setFixedWidth(750)
        hero_desc.setStyleSheet("font-size: 15px; color: #64748B; line-height: 22px; margin-bottom: 8px;")
        
        # Primary Call To Action Button
        self.get_started_btn = PrimaryButton("Get Started →")
        self.get_started_btn.setFixedWidth(180)
        self.get_started_btn.clicked.connect(self.gotoLogin.emit)
        
        hero_layout.addWidget(hero_title)
        hero_layout.addWidget(hero_subtitle)
        hero_layout.addWidget(hero_desc)
        hero_layout.addWidget(self.get_started_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        scroll_layout.addWidget(hero_widget)
        
        scroll_layout.addSpacing(16)
        
        # Grid layout for Feature Cards
        grid_widget = QWidget()
        grid_widget.setFixedWidth(1080)
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(24)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        
        # Features setup: (Title, Description, Icon path, Icon Backdrop Color)
        features = [
            ("AI Bank Detection", "Auto-detects statement formats from supported banks.", "assets/icons/ai.png", "#F5F3FF"), # Soft Purple
            ("OCR Support", "Scans paper and image-based statements using Tesseract.", "assets/icons/dashboard.png", "#EFF6FF"), # Soft Blue
            ("Excel Export", "Exports transactions to clean, formatted Excel sheets.", "assets/icons/excel.png", "#F0FDF4"), # Soft Green
            ("Financial Reports", "Generates beautiful charts and cash-flow summaries.", "assets/icons/reports.png", "#F0FDFA"), # Soft Teal
            ("GST Reports", "Prepares tax-ready reports for simple GST filings.", "assets/icons/gst.png", "#FFFBEB"), # Soft Amber
            ("Duplicate Detection", "Detects duplicate transactions and entry anomalies.", "assets/icons/duplicate.png", "#FEF2F2"), # Soft Rose
            ("Database History", "Saves processed transactions to a local SQLite log.", "assets/icons/history.png", "#EFF6FF"), # Soft Blue
            ("Email Export", "Exports financial reports securely via local mail clients.", "assets/icons/email.png", "#ECFDF5") # Soft Emerald
        ]
        
        # 4 columns grid
        cols = 4
        for idx, (title, desc, icon, icon_bg) in enumerate(features):
            row = idx // cols
            col = idx % cols
            card = CustomCard(title, desc, icon, icon_bg)
            # Make card click trigger login redirect by default as action placeholder
            card.clicked.connect(self.gotoLogin.emit)
            grid_layout.addWidget(card, row, col)
            
        scroll_layout.addWidget(grid_widget)
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        # 3. Footer Bar
        footer_widget = QFrame()
        footer_widget.setObjectName("FooterWidget")
        footer_widget.setStyleSheet("""
            QFrame#FooterWidget {
                background-color: #FFFFFF;
                border-top: 1px solid #E2E8F0;
            }
        """)
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(32, 12, 32, 12)
        
        version_label = QLabel("Version v1.0")
        version_label.setStyleSheet("font-size: 12px; color: #64748B; font-weight: 500;")
        footer_layout.addWidget(version_label)
        
        footer_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        pyqt_label = QLabel("Developed using Python & PyQt6")
        pyqt_label.setStyleSheet("font-size: 12px; color: #64748B; font-weight: 500;")
        footer_layout.addWidget(pyqt_label)
        
        main_layout.addWidget(footer_widget)

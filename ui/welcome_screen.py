from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QGridLayout, QFrame, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from widgets.custom_button import PrimaryButton, SecondaryButton, LinkButton
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
        
        # 1. Header Navigation Bar (Logo on left, Links in center, Auth Buttons on right)
        header_widget = QFrame()
        header_widget.setObjectName("HeaderWidget")
        header_widget.setStyleSheet("background-color: #FFFFFF; border-bottom: 1px solid #E5E7EB;")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(32, 16, 32, 16)
        
        # Header Left: Logo & Name
        left_header = QHBoxLayout()
        left_header.setSpacing(12)
        logo_label = QLabel()
        logo_label.setFixedSize(32, 32)
        logo_pixmap = QPixmap("assets/logo.png")
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        left_header.addWidget(logo_label)
        
        app_name_label = QLabel("StatementForge")
        app_name_label.setObjectName("WelcomeAppName")
        app_name_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #0037b0; font-family: 'Times New Roman'; border: none;")
        left_header.addWidget(app_name_label)
        header_layout.addLayout(left_header)
        
        header_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Header Center: Static/Auxiliary Links
        center_header = QHBoxLayout()
        center_header.setSpacing(24)
        for link_text in ["Features", "Pricing", "Documentation", "Support"]:
            link_btn = LinkButton(link_text)
            link_btn.setStyleSheet("color: #4B5563; font-size: 14px; font-weight: 500; border: none; background: transparent; font-family: 'Times New Roman';")
            center_header.addWidget(link_btn)
        header_layout.addLayout(center_header)
        
        header_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Header Right: Auth Buttons
        right_header = QHBoxLayout()
        right_header.setSpacing(12)
        
        self.login_nav_btn = SecondaryButton("Login")
        self.login_nav_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #0037b0;
                border: 1px solid #0037b0;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 600;
                font-size: 13px;
                font-family: 'Times New Roman';
            }
            QPushButton:hover {
                background-color: #EFF6FF;
            }
        """)
        self.login_nav_btn.clicked.connect(self.gotoLogin.emit)
        right_header.addWidget(self.login_nav_btn)
        
        self.register_nav_btn = PrimaryButton("Register")
        self.register_nav_btn.setStyleSheet("""
            QPushButton {
                background-color: #0037b0;
                color: white;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 600;
                font-size: 13px;
                font-family: 'Times New Roman';
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        self.register_nav_btn.clicked.connect(self.gotoRegister.emit)
        right_header.addWidget(self.register_nav_btn)
        
        header_layout.addLayout(right_header)
        main_layout.addWidget(header_widget)
        
        # 2. Central Scroll Area
        self.setObjectName("WelcomeBackground")
        self.setStyleSheet("background-color: #f7f9fb;")
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("background-color: transparent; border: none;")
        
        scroll_content = QWidget()
        scroll_content.setObjectName("ScrollContent")
        scroll_content.setStyleSheet("background-color: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(64, 48, 64, 32)
        scroll_layout.setSpacing(32)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        
        # Hero Branding Section
        hero_widget = QWidget()
        hero_layout = QVBoxLayout(hero_widget)
        hero_layout.setSpacing(16)
        hero_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Text badge above title
        badge_label = QLabel("StatementForge")
        badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_label.setStyleSheet("""
            background-color: rgba(0, 55, 176, 0.1);
            color: #0037b0;
            font-weight: bold;
            font-size: 11px;
            padding: 6px 14px;
            border-radius: 12px;
            text-transform: uppercase;
            font-family: 'Times New Roman';
            letter-spacing: 2px;
        """)
        badge_label.setFixedWidth(140)
        hero_layout.addWidget(badge_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Headline title
        hero_title = QLabel("Automated Bank Statement\nParser & Accounting Hub")
        hero_title.setObjectName("HeroTitle")
        hero_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_title.setStyleSheet("""
            font-size: 38px;
            font-weight: bold;
            color: #0037b0;
            line-height: 46px;
            font-family: 'Times New Roman';
            border: none;
            padding-bottom: 8px;
        """)
        
        # Subtitle description
        hero_desc = QLabel(
            "An intelligent offline desktop application that extracts, verifies, and organizes "
            "financial transactions from multiple bank statement formats."
        )
        hero_desc.setObjectName("HeroDesc")
        hero_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_desc.setWordWrap(True)
        hero_desc.setFixedWidth(750)
        hero_desc.setStyleSheet("""
            font-size: 16px;
            color: #4B5563;
            line-height: 24px;
            font-family: 'Times New Roman';
        """)
        
        # Primary CTA
        self.get_started_btn = PrimaryButton("Get Started  →")
        self.get_started_btn.setFixedWidth(180)
        self.get_started_btn.setFixedHeight(48)
        self.get_started_btn.setStyleSheet("""
            QPushButton {
                background-color: #0037b0;
                color: white;
                border-radius: 10px;
                font-weight: bold;
                font-size: 15px;
                font-family: 'Times New Roman';
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        self.get_started_btn.clicked.connect(self.gotoLogin.emit)
        
        hero_layout.addWidget(hero_title)
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
            card.clicked.connect(self.gotoLogin.emit)
            grid_layout.addWidget(card, row, col)
            
        scroll_layout.addWidget(grid_widget)
        
        # 3. Footer Section (Branding on Left, Copyright in Center, Links on Right)
        footer_widget = QFrame()
        footer_widget.setObjectName("FooterWidget")
        footer_widget.setStyleSheet("""
            QFrame#FooterWidget {
                border-top: 1px solid #E5E7EB;
                background-color: transparent;
                margin-top: 48px;
                padding-top: 24px;
            }
        """)
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(16, 0, 16, 0)
        
        brand_lbl = QLabel("StatementForge")
        brand_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #111827; font-family: 'Times New Roman'; border: none;")
        footer_layout.addWidget(brand_lbl)
        
        footer_layout.addStretch()
        
        copyright_lbl = QLabel("© 2024 StatementForge Inc. All rights reserved. Precision in Financial Data.")
        copyright_lbl.setStyleSheet("font-size: 13px; color: #6B7280; font-family: 'Times New Roman'; border: none;")
        footer_layout.addWidget(copyright_lbl)
        
        footer_layout.addStretch()
        
        right_links = QHBoxLayout()
        right_links.setSpacing(16)
        for link_text in ["Privacy Policy", "Terms of Service", "Security", "Contact"]:
            link_btn = LinkButton(link_text)
            link_btn.setStyleSheet("color: #6B7280; font-size: 13px; border: none; background: transparent; font-family: 'Times New Roman';")
            right_links.addWidget(link_btn)
        footer_layout.addLayout(right_links)
        
        scroll_layout.addWidget(footer_widget)
        
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

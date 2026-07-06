import datetime
import re
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QFrame, QPushButton, QGridLayout, QScrollArea, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QCursor, QPixmap, QIcon
from ui.register import ToastNotification, PasswordRequirementsWidget

class ProfileWindow(QMainWindow):
    """
    Dedicated user profile management window. Allows editing personal details,
    viewing account stats, and changing passwords.
    """
    save_requested = pyqtSignal(str, str, str)  # name, phone, username
    password_change_requested = pyqtSignal(str, str)  # old_password, new_password
    logout_requested = pyqtSignal()
    back_to_dashboard = pyqtSignal()
    profile_updated = pyqtSignal(dict)  # Emitted on successful profile save

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("My Profile - StatementForge")
        self.setFixedSize(1100, 780)
        self.setStyleSheet("QMainWindow { background-color: #F6F8FC; }")

        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Main Layout
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(40, 24, 40, 32)
        self.main_layout.setSpacing(24)

        # 1. Top Navigation Bar
        top_bar = QHBoxLayout()
        self.back_btn = QPushButton("←  Back to Dashboard")
        self.back_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #475569;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #F8FAFC;
                color: #0F172A;
                border-color: #CBD5E1;
            }
        """)
        self.back_btn.clicked.connect(self.back_to_dashboard.emit)
        top_bar.addWidget(self.back_btn)
        top_bar.addStretch()
        self.main_layout.addLayout(top_bar)

        # Page Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        title_lbl = QLabel("My Profile")
        title_lbl.setStyleSheet("font-size: 26px; font-weight: 800; color: #0F172A;")
        sub_lbl = QLabel("Manage your personal information and account settings.")
        sub_lbl.setStyleSheet("font-size: 13px; color: #64748B; font-weight: 500;")
        header_layout.addWidget(title_lbl)
        header_layout.addWidget(sub_lbl)
        self.main_layout.addLayout(header_layout)

        # 2. Main Content Split (Left Sidebar Panel & Right Form Panel)
        content_split = QHBoxLayout()
        content_split.setSpacing(24)

        # ==========================================
        # LEFT COLUMN (Avatar, Stats, Action Buttons)
        # ==========================================
        left_panel = QFrame()
        left_panel.setFixedWidth(320)
        left_panel.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 16px;
            }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(24, 32, 24, 24)
        left_layout.setSpacing(24)

        # Large Circular Avatar Badge
        avatar_container = QHBoxLayout()
        self.avatar_lbl = QLabel("K")
        self.avatar_lbl.setFixedSize(120, 120)
        self.avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_lbl.setStyleSheet("""
            QLabel {
                background-color: #2563EB; /* Solid Premium Blue */
                color: #FFFFFF;
                font-weight: 800;
                font-size: 52px;
                border-radius: 60px;
                border: none;
            }
        """)
        avatar_container.addWidget(self.avatar_lbl)
        left_layout.addLayout(avatar_container)

        self.name_heading = QLabel("User Name")
        self.name_heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_heading.setStyleSheet("font-size: 18px; font-weight: 700; color: #0F172A; border: none;")
        left_layout.addWidget(self.name_heading)

        # Divider line
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background-color: #E2E8F0; max-height: 1px; border: none;")
        left_layout.addWidget(divider)

        # Account Info section (Status, Created Date, Last Login)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(12)

        info_header = QLabel("Account Information")
        info_header.setStyleSheet("font-weight: 700; font-size: 12px; color: #64748B; border: none; text-transform: uppercase; letter-spacing: 0.5px;")
        info_layout.addWidget(info_header)

        # Status badge line
        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        status_lbl = QLabel("Account Status:")
        status_lbl.setStyleSheet("font-size: 12px; color: #64748B; border: none; font-weight: 500;")
        self.status_badge = QLabel("Active")
        self.status_badge.setFixedSize(70, 20)
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_badge.setStyleSheet("""
            QLabel {
                background-color: #ECFDF5;
                color: #059669;
                font-weight: 700;
                font-size: 10px;
                border-radius: 10px;
                border: 1px solid #A7F3D0;
            }
        """)
        status_row.addWidget(status_lbl)
        status_row.addWidget(self.status_badge)
        status_row.addStretch()
        info_layout.addLayout(status_row)

        # Created Date
        self.created_lbl = QLabel("Joined: N/A")
        self.created_lbl.setStyleSheet("font-size: 12px; color: #475569; border: none; font-weight: 500;")
        info_layout.addWidget(self.created_lbl)

        # Last Login
        self.login_lbl = QLabel("Last Login: N/A")
        self.login_lbl.setStyleSheet("font-size: 12px; color: #475569; border: none; font-weight: 500;")
        info_layout.addWidget(self.login_lbl)

        left_layout.addLayout(info_layout)

        # Spacer to push action buttons down
        left_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Action Buttons Section
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(10)

        # Save changes button
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.setFixedHeight(42)
        self.save_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #2563EB);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #1D4ED8);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1D4ED8, stop:1 #1E40AF);
            }
        """)
        self.save_btn.clicked.connect(self.on_save_clicked)
        btn_layout.addWidget(self.save_btn)

        # Logout button
        self.logout_btn = QPushButton("Logout")
        self.logout_btn.setFixedHeight(42)
        self.logout_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.logout_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #EF4444;
                border: 1px solid #FCA5A5;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #FEF2F2;
                color: #B91C1C;
                border-color: #F87171;
            }
        """)
        self.logout_btn.clicked.connect(self.logout_requested.emit)
        btn_layout.addWidget(self.logout_btn)

        left_layout.addLayout(btn_layout)
        content_split.addWidget(left_panel)

        # ==========================================
        # RIGHT COLUMN (Form Inputs Scroll Area)
        # ==========================================
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background-color: transparent; border: none;")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        right_layout = QVBoxLayout(scroll_content)
        right_layout.setContentsMargins(0, 0, 8, 0)
        right_layout.setSpacing(24)

        # 1. Personal Information Section
        personal_card = QFrame()
        personal_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 16px;
            }
        """)
        personal_layout = QVBoxLayout(personal_card)
        personal_layout.setContentsMargins(24, 24, 24, 24)
        personal_layout.setSpacing(16)

        personal_title = QLabel("Personal Information")
        personal_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #0F172A; border: none;")
        personal_layout.addWidget(personal_title)

        form_grid = QGridLayout()
        form_grid.setSpacing(12)

        # QSS for editable vs read-only inputs
        input_style = """
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 10px;
                padding: 10px 14px;
                font-size: 14px;
                color: #0F172A;
            }
            QLineEdit:focus {
                border: 2px solid #2563EB;
            }
            QLineEdit:disabled {
                background-color: #F1F5F9;
                color: #64748B;
                border-color: #E2E8F0;
            }
        """

        # Username Field
        un_label = QLabel("Username")
        un_label.setStyleSheet("font-weight: 600; font-size: 12px; color: #475569; border: none;")
        self.username_input = QLineEdit()
        self.username_input.setStyleSheet(input_style)
        form_grid.addWidget(un_label, 0, 0)
        form_grid.addWidget(self.username_input, 1, 0)

        # Role Field (Read-only, shows User)
        role_label = QLabel("Role")
        role_label.setStyleSheet("font-weight: 600; font-size: 12px; color: #475569; border: none;")
        self.role_input = QLineEdit("User")
        self.role_input.setEnabled(False)
        self.role_input.setStyleSheet(input_style)
        form_grid.addWidget(role_label, 0, 1)
        form_grid.addWidget(self.role_input, 1, 1)

        # Full Name Field
        fn_label = QLabel("Full Name *")
        fn_label.setStyleSheet("font-weight: 600; font-size: 12px; color: #475569; border: none;")
        self.name_input = QLineEdit()
        self.name_input.setStyleSheet(input_style)
        form_grid.addWidget(fn_label, 2, 0)
        form_grid.addWidget(self.name_input, 3, 0)

        # Email Address Field
        em_label = QLabel("Email Address *")
        em_label.setStyleSheet("font-weight: 600; font-size: 12px; color: #475569; border: none;")
        self.email_input = QLineEdit()
        self.email_input.setStyleSheet(input_style)
        form_grid.addWidget(em_label, 2, 1)
        form_grid.addWidget(self.email_input, 3, 1)

        # Phone Number Field
        ph_label = QLabel("Phone Number *")
        ph_label.setStyleSheet("font-weight: 600; font-size: 12px; color: #475569; border: none;")
        self.phone_input = QLineEdit()
        self.phone_input.setStyleSheet(input_style)
        form_grid.addWidget(ph_label, 4, 0)
        form_grid.addWidget(self.phone_input, 5, 0)

        personal_layout.addLayout(form_grid)
        right_layout.addWidget(personal_card)

        # 2. Change Password Section
        password_card = QFrame()
        password_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 16px;
            }
        """)
        pwd_layout = QVBoxLayout(password_card)
        pwd_layout.setContentsMargins(24, 24, 24, 24)
        pwd_layout.setSpacing(14)

        pwd_title = QLabel("Change Password")
        pwd_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #0F172A; border: none;")
        pwd_layout.addWidget(pwd_title)

        pwd_form = QGridLayout()
        pwd_form.setSpacing(12)

        # Old Password
        old_label = QLabel("Old Password")
        old_label.setStyleSheet("font-weight: 600; font-size: 12px; color: #475569; border: none;")
        self.old_pwd_input = QLineEdit()
        self.old_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.old_pwd_input.setStyleSheet(input_style)
        pwd_form.addWidget(old_label, 0, 0)
        pwd_form.addWidget(self.old_pwd_input, 1, 0)

        # Confirm Password
        confirm_label = QLabel("Confirm New Password")
        confirm_label.setStyleSheet("font-weight: 600; font-size: 12px; color: #475569; border: none;")
        self.confirm_pwd_input = QLineEdit()
        self.confirm_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pwd_input.setStyleSheet(input_style)
        pwd_form.addWidget(confirm_label, 0, 1)
        pwd_form.addWidget(self.confirm_pwd_input, 1, 1)

        # New Password (spans both columns for width)
        new_label = QLabel("New Password")
        new_label.setStyleSheet("font-weight: 600; font-size: 12px; color: #475569; border: none;")
        self.new_pwd_input = QLineEdit()
        self.new_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pwd_input.setStyleSheet(input_style)
        self.new_pwd_input.textChanged.connect(self.on_new_password_changed)
        pwd_form.addWidget(new_label, 2, 0, 1, 2)
        pwd_form.addWidget(self.new_pwd_input, 3, 0, 1, 2)

        pwd_layout.addLayout(pwd_form)

        # Live Horizontal Password validation checklist
        self.reqs_widget = PasswordRequirementsWidget()
        pwd_layout.addWidget(self.reqs_widget)

        # Password Error label
        self.pwd_error_lbl = QLabel("")
        self.pwd_error_lbl.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 500; border: none;")
        pwd_layout.addWidget(self.pwd_error_lbl)

        # Action Change password button
        self.change_pwd_btn = QPushButton("Change Password")
        self.change_pwd_btn.setFixedHeight(42)
        self.change_pwd_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.change_pwd_btn.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #EFF6FF;
                color: #2563EB;
                border-color: #93C5FD;
            }
            QPushButton:disabled {
                background-color: #F1F5F9;
                color: #94A3B8;
                border-color: #E2E8F0;
            }
        """)
        self.change_pwd_btn.clicked.connect(self.on_change_password_clicked)
        pwd_layout.addWidget(self.change_pwd_btn)

        right_layout.addWidget(password_card)
        scroll_area.setWidget(scroll_content)
        content_split.addWidget(scroll_area)

        self.main_layout.addLayout(content_split)

    def load_user_data(self, user):
        """Populates UI controls with user details from the session model."""
        self.name_heading.setText(user.get("name", "User Name"))
        self.username_input.setText(user.get("username", ""))
        self.name_input.setText(user.get("name", ""))
        self.email_input.setText(user.get("email", ""))
        self.phone_input.setText(user.get("phone", ""))
        
        # Display first letter dynamically in avatar
        initial = "U"
        if user.get("name", "").strip():
            initial = user.get("name", "").strip()[0].upper()
        self.avatar_lbl.setText(initial)

        # Setup Dates
        created_dt = user.get("created_at")
        self.created_lbl.setText(f"Joined: {self.format_date(created_dt)}")
        
        login_dt = user.get("last_login")
        self.login_lbl.setText(f"Last Login: {self.format_date(login_dt)}")

    def format_date(self, dt):
        if not dt:
            return "N/A"
        if isinstance(dt, datetime.datetime):
            return dt.strftime("%B %d, %Y")
        return str(dt)

    def on_new_password_changed(self, password):
        self.reqs_widget.update_requirements(password)

    def on_save_clicked(self):
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        phone = self.phone_input.text().strip()
        username = self.username_input.text().strip()

        # Simple client side check
        if not name or not email or not phone or not username:
            self.show_error("Please fill in all required fields.")
            return

        self.save_requested.emit(name, phone, username)

    def on_change_password_clicked(self):
        old_pwd = self.old_pwd_input.text()
        new_pwd = self.new_pwd_input.text()
        confirm_pwd = self.confirm_pwd_input.text()

        self.pwd_error_lbl.setText("")

        if not old_pwd or not new_pwd or not confirm_pwd:
            self.pwd_error_lbl.setText("❌ All password fields are required.")
            return

        # Check new password rules
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        if len(new_pwd) < 8:
            self.pwd_error_lbl.setText("❌ New password must be at least 8 characters.")
            return
        if not any(c.isupper() for c in new_pwd):
            self.pwd_error_lbl.setText("❌ New password must contain an uppercase letter.")
            return
        if not any(c.islower() for c in new_pwd):
            self.pwd_error_lbl.setText("❌ New password must contain a lowercase letter.")
            return
        if not any(c.isdigit() for c in new_pwd):
            self.pwd_error_lbl.setText("❌ New password must contain a number.")
            return
        if not any(c in special_chars for c in new_pwd):
            self.pwd_error_lbl.setText("❌ New password must contain a special character.")
            return

        if new_pwd != confirm_pwd:
            self.pwd_error_lbl.setText("❌ New passwords do not match.")
            return

        self.password_change_requested.emit(old_pwd, new_pwd)

    def show_success_toast(self, message):
        """Displays a green Success Toast in the top right corner."""
        toast = ToastNotification(self, f"✓ {message}")
        toast.show_toast()

    def show_error(self, message):
        """Displays an error toast message (red theme notification)."""
        toast = ToastNotification(self, f"❌ {message}")
        # Customize background to red
        toast.setStyleSheet("QWidget#Toast { background-color: #EF4444; border-radius: 8px; }")
        toast.show_toast()

    def clear_password_fields(self):
        self.old_pwd_input.clear()
        self.new_pwd_input.clear()
        self.confirm_pwd_input.clear()
        self.reqs_widget.update_requirements("")
        self.pwd_error_lbl.setText("")

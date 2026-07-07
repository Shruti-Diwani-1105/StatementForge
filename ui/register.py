import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QFrame, QPushButton, QGraphicsOpacityEffect, QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QTimer, QEvent
from PyQt6.QtGui import QPixmap, QCursor, QIcon, QColor

class PremiumInputGroup(QWidget):
    """
    Custom text field component containing:
    - Field Label
    - Styled input box wrapping:
      - Leading icon
      - Transparent text line input
      - Show/hide password button (if password field)
    - Fixed-height validation error label below to ensure zero layout shifting.
    """
    textChanged = pyqtSignal(str)

    def __init__(self, label_text, placeholder, icon_path, is_password=False, parent=None):
        super().__init__(parent)
        self.is_password = is_password
        self.has_error = False

        # Compact vertical layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Label
        self.label = QLabel(label_text)
        self.label.setStyleSheet("font-weight: 600; font-size: 13px; color: #475569;")
        layout.addWidget(self.label)

        # Custom Bordered Input Container
        self.container = QFrame()
        self.container.setObjectName("InputContainer")
        self.container.setFixedHeight(48)

        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(12, 0, 12, 0)
        container_layout.setSpacing(8)

        # Leading Icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(18, 18)
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            self.icon_label.setPixmap(pixmap.scaled(
                18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            ))
        container_layout.addWidget(self.icon_label)

        # Text input field
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText(placeholder)
        self.line_edit.setStyleSheet(
            "background: transparent; border: none; padding: 0; font-size: 14px; color: #0F172A;"
        )
        if is_password:
            self.line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.line_edit.textChanged.connect(self.textChanged.emit)
        
        # Install self as event filter on line edit to capture FocusIn/FocusOut
        self.line_edit.installEventFilter(self)
        container_layout.addWidget(self.line_edit)

        # Trailing toggle password visibility button
        self.toggle_btn = None
        if is_password:
            self.toggle_btn = QPushButton()
            self.toggle_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.toggle_btn.setFixedSize(18, 18)
            self.toggle_btn.setStyleSheet("background: transparent; border: none; padding: 0;")

            self.eye_open_pixmap = QPixmap("assets/icons/eye.png").scaled(
                18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.eye_closed_pixmap = QPixmap("assets/icons/eye_closed.png").scaled(
                18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )

            self.toggle_btn.setIcon(QIcon(self.eye_closed_pixmap))
            self.toggle_btn.clicked.connect(self.toggle_password_visibility)
            container_layout.addWidget(self.toggle_btn)

        layout.addWidget(self.container)

        # Fixed height error message label to ensure zero layout shifting on error toggle
        self.error_label = QLabel(" ")
        self.error_label.setFixedHeight(18)
        self.error_label.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 500;")
        layout.addWidget(self.error_label)
        
        self.set_container_style(focused=False)

    def eventFilter(self, watched, event):
        if watched == self.line_edit:
            if event.type() == QEvent.Type.FocusIn:
                self.set_container_style(focused=True)
            elif event.type() == QEvent.Type.FocusOut:
                self.set_container_style(focused=False)
        return super().eventFilter(watched, event)

    def set_container_style(self, focused=False):
        """Applies dynamic stylesheet updates directly to avoid native unpolish/polish reflow bugs."""
        if self.has_error:
            border_style = "border: 1px solid #EF4444;"
        elif focused:
            border_style = "border: 2px solid #2563EB;"
        else:
            border_style = "border: 1px solid #CBD5E1;"

        self.container.setStyleSheet(f"""
            QFrame#InputContainer {{
                background-color: #FFFFFF;
                {border_style}
                border-radius: 10px;
            }}
        """)

    def set_error(self, message):
        """Sets error state and text. Reverts to non-empty space placeholder to preserve layout height."""
        if message:
            self.has_error = True
            self.error_label.setText(message)
        else:
            self.has_error = False
            self.error_label.setText(" ")
        self.set_container_style(focused=self.line_edit.hasFocus())

    def toggle_password_visibility(self):
        if self.line_edit.echoMode() == QLineEdit.EchoMode.Password:
            self.line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_btn.setIcon(QIcon(self.eye_open_pixmap))
        else:
            self.line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_btn.setIcon(QIcon(self.eye_closed_pixmap))

    def text(self):
        return self.line_edit.text()

    def setText(self, text):
        self.line_edit.setText(text)

    def clear(self):
        self.line_edit.clear()
        self.set_error(None)


class PasswordRequirementsWidget(QWidget):
    """Compact horizontal grid containing validation checklists."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(4)

        self.reqs = [
            {"id": "len", "text": "Minimum 8 characters", "valid": False},
            {"id": "upper", "text": "Uppercase letter", "valid": False},
            {"id": "lower", "text": "Lowercase letter", "valid": False},
            {"id": "num", "text": "Number", "valid": False},
            {"id": "special", "text": "Special character", "valid": False}
        ]

        self.labels = {}
        for idx, req in enumerate(self.reqs):
            lbl = QLabel(f"✓ {req['text']}")
            lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
            row = idx // 3
            col = idx % 3
            layout.addWidget(lbl, row, col)
            self.labels[req["id"]] = lbl

    def update_requirements(self, password):
        self.reqs[0]["valid"] = len(password) >= 8
        self.reqs[1]["valid"] = any(c.isupper() for c in password)
        self.reqs[2]["valid"] = any(c.islower() for c in password)
        self.reqs[3]["valid"] = any(c.isdigit() for c in password)

        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        self.reqs[4]["valid"] = any(c in special_chars for c in password)

        all_valid = True
        for req in self.reqs:
            lbl = self.labels[req["id"]]
            if req["valid"]:
                lbl.setStyleSheet("color: #10B981; font-size: 11px; font-weight: 600;")
            else:
                lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 500;")
                all_valid = False
        return all_valid


class PasswordStrengthWidget(QWidget):
    """Sleek horizontal password strength meter."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(10)

        # Three segments
        self.segments_layout = QHBoxLayout()
        self.segments_layout.setSpacing(4)
        self.segments = []
        for _ in range(3):
            seg = QFrame()
            seg.setFixedHeight(4)
            seg.setStyleSheet("background-color: #E2E8F0; border-radius: 2px;")
            self.segments_layout.addWidget(seg)
            self.segments.append(seg)

        layout.addLayout(self.segments_layout, stretch=2)

        self.strength_label = QLabel("")
        self.strength_label.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600;")
        layout.addWidget(self.strength_label, stretch=1)

    def update_strength(self, password):
        if not password:
            self.strength_label.setText("")
            for seg in self.segments:
                seg.setStyleSheet("background-color: #E2E8F0; border-radius: 2px;")
            return

        has_len = len(password) >= 8
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_num = any(c.isdigit() for c in password)
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        has_special = any(c in special_chars for c in password)

        criteria_met = sum([has_len, has_upper, has_lower, has_num, has_special])

        if criteria_met < 3:
            label = "Weak"
            color = "#EF4444"
            active_segs = 1
        elif criteria_met < 5:
            label = "Medium"
            color = "#F59E0B"
            active_segs = 2
        else:
            label = "Strong"
            color = "#10B981"
            active_segs = 3

        self.strength_label.setText(label)
        self.strength_label.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 700;")

        for i, seg in enumerate(self.segments):
            if i < active_segs:
                seg.setStyleSheet(f"background-color: {color}; border-radius: 2px;")
            else:
                seg.setStyleSheet("background-color: #E2E8F0; border-radius: 2px;")


class ToastNotification(QWidget):
    """Success toast in the top-right corner."""
    def __init__(self, parent_widget, message):
        super().__init__(parent_widget)
        self.parent_widget = parent_widget

        self.setWindowFlags(Qt.WindowType.SubWindow)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        self.icon_label = QLabel("✓")
        self.icon_label.setStyleSheet("color: #FFFFFF; font-size: 14px; font-weight: 700;")
        layout.addWidget(self.icon_label)

        self.msg_label = QLabel(message)
        self.msg_label.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 600;")
        layout.addWidget(self.msg_label)

        self.setObjectName("Toast")
        self.setStyleSheet("QWidget#Toast { background-color: #10B981; border-radius: 8px; }")

        self.adjustSize()

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.update_position()

    def update_position(self):
        parent_rect = self.parent_widget.rect()
        x = parent_rect.right() - self.width() - 24
        y = parent_rect.top() + 24
        self.move(x, y)

    def show_toast(self):
        self.show()
        self.update_position()

        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(250)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

        QTimer.singleShot(3000, self.fade_out)

    def fade_out(self):
        self.anim_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_out.setDuration(250)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.finished.connect(self.deleteLater)
        self.anim_out.start()


class RegisterScreen(QWidget):
    """
    Redesigned, premium Register Screen that dynamically fits within 1440x900
    without scrolling. Uses proper nested layouts and layout preservation techniques.
    """
    registerSuccess = pyqtSignal()
    gotoLogin = pyqtSignal()
    gotoWelcome = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.name_touched = False
        self.email_touched = False
        self.phone_touched = False
        self.password_touched = False
        self.confirm_touched = False
        self.init_ui()

    def init_ui(self):
        self.setObjectName("RegisterBackground")
        # Style sheet is strictly scoped to RegisterBackground ID to prevent stylesheet leakage onto children
        self.setStyleSheet("QWidget#RegisterBackground { background-color: #F6F8FC; }")

        # Outer Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top Bar (Back Button)
        top_bar_layout = QHBoxLayout()
        top_bar_layout.setContentsMargins(32, 24, 32, 0)
        
        self.back_btn = QPushButton("←  Back")
        self.back_btn.setObjectName("BackButton")
        self.back_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.back_btn.setStyleSheet("""
            QPushButton#BackButton {
                background-color: #FFFFFF;
                color: #475569;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
                padding: 8px 16px;
            }
            QPushButton#BackButton:hover {
                background-color: #F8FAFC;
                color: #0F172A;
                border-color: #CBD5E1;
            }
            QPushButton#BackButton:pressed {
                background-color: #F1F5F9;
            }
        """)
        self.back_btn.clicked.connect(self.gotoWelcome.emit)
        top_bar_layout.addWidget(self.back_btn)
        top_bar_layout.addStretch()
        main_layout.addLayout(top_bar_layout)

        # Centering Layout
        center_layout = QHBoxLayout()
        center_layout.addStretch()

        # The Registration Card Frame
        # Styled with a sleek border instead of buggy graphics drop shadow to prevent repaint page blanking issues
        self.card = QFrame()
        self.card.setObjectName("RegisterCard")
        self.card.setFixedWidth(620)
        self.card.setStyleSheet("""
            QFrame#RegisterCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 18px;
            }
        """)

        # Card Stacked Widget
        self.card_stack = QStackedWidget(self.card)
        card_outer_layout = QVBoxLayout(self.card)
        card_outer_layout.setContentsMargins(0, 0, 0, 0)
        card_outer_layout.addWidget(self.card_stack)

        # PAGE 1: The registration form (represented as QFrame for scoped repaints)
        self.form_widget = QFrame()
        self.form_widget.setObjectName("FormWidget")
        self.form_widget.setStyleSheet("""
            QFrame#FormWidget {
                background-color: #FFFFFF;
                border: none;
                border-radius: 18px;
            }
        """)
        form_layout = QVBoxLayout(self.form_widget)
        form_layout.setContentsMargins(40, 32, 40, 32)
        form_layout.setSpacing(10)

        # Branding Header
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_pixmap = QPixmap("assets/logo.png")
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(
                40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            ))
        header_layout.addWidget(logo_label)

        title_label = QLabel("StatementForge")
        title_label.setMinimumHeight(34)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 22px; font-weight: 800; color: #0F172A; letter-spacing: -0.5px; border: 0px solid transparent; padding-bottom: 4px;")
        header_layout.addWidget(title_label)

        subtitle_label = QLabel("Create your account to securely manage and process financial statements.")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setWordWrap(True)
        subtitle_label.setStyleSheet("font-size: 13px; color: #64748B; font-weight: 500;")
        header_layout.addWidget(subtitle_label)
        form_layout.addWidget(header_widget)

        # Inputs section
        self.name_input = PremiumInputGroup(
            "Full Name *", "Enter your full name", "assets/icons/profile.png"
        )
        self.email_input = PremiumInputGroup(
            "Email Address *", "Enter your email address", "assets/icons/email.png"
        )
        self.phone_input = PremiumInputGroup(
            "Phone Number *", "Enter your phone number", "assets/icons/phone.png"
        )
        self.pass_input = PremiumInputGroup(
            "Password *", "Enter password", "assets/icons/lock.png", is_password=True
        )

        form_layout.addWidget(self.name_input)
        form_layout.addWidget(self.email_input)
        form_layout.addWidget(self.phone_input)
        form_layout.addWidget(self.pass_input)

        # Password checklist & strength
        self.req_widget = PasswordRequirementsWidget()
        self.strength_widget = PasswordStrengthWidget()
        form_layout.addWidget(self.req_widget)
        form_layout.addWidget(self.strength_widget)

        # Spacer between widgets
        form_layout.addSpacing(4)

        # Confirm password
        self.confirm_input = PremiumInputGroup(
            "Confirm Password *", "Confirm password", "assets/icons/lock.png", is_password=True
        )
        form_layout.addWidget(self.confirm_input)

        # Spacer
        form_layout.addSpacing(6)

        # Create Account Button (Height 50px)
        self.register_btn = QPushButton("Create Account")
        self.register_btn.setObjectName("CreateAccountButton")
        self.register_btn.setFixedHeight(50)
        self.register_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.register_btn.setStyleSheet("""
            QPushButton#CreateAccountButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #2563EB);
                color: #FFFFFF;
                border: none;
                border-radius: 12px;
                font-weight: 700;
                font-size: 15px;
            }
            QPushButton#CreateAccountButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #1D4ED8);
            }
            QPushButton#CreateAccountButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1D4ED8, stop:1 #1E40AF);
            }
            QPushButton#CreateAccountButton:disabled {
                background-color: #CBD5E1;
                color: #94A3B8;
            }
        """)
        self.register_btn.clicked.connect(self.handle_registration)
        form_layout.addWidget(self.register_btn)

        # Already have an account redirects
        login_link_layout = QHBoxLayout()
        login_link_layout.setSpacing(4)
        login_link_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        login_lbl = QLabel("Already have an account?")
        login_lbl.setStyleSheet("color: #64748B; font-size: 13px; font-weight: 500;")

        self.login_btn = QPushButton("Sign In")
        self.login_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.login_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #2563EB;
                border: none;
                font-weight: 700;
                font-size: 13px;
                padding: 0;
            }
            QPushButton:hover {
                color: #1D4ED8;
                text-decoration: underline;
            }
        """)
        self.login_btn.clicked.connect(self.gotoLogin.emit)

        login_link_layout.addWidget(login_lbl)
        login_link_layout.addWidget(self.login_btn)
        form_layout.addLayout(login_link_layout)


        # PAGE 2: The registration success screen (represented as QFrame for scoped repaints)
        self.success_widget = QFrame()
        self.success_widget.setObjectName("SuccessWidget")
        self.success_widget.setStyleSheet("""
            QFrame#SuccessWidget {
                background-color: #FFFFFF;
                border: none;
                border-radius: 18px;
            }
        """)
        success_layout = QVBoxLayout(self.success_widget)
        success_layout.setContentsMargins(40, 60, 40, 60)
        success_layout.setSpacing(24)
        success_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        success_icon = QLabel("✓")
        success_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_icon.setFixedSize(64, 64)
        success_icon.setStyleSheet("""
            background-color: #EFF6FF;
            color: #2563EB;
            font-size: 32px;
            font-weight: bold;
            border-radius: 32px;
        """)
        success_layout.addWidget(success_icon, alignment=Qt.AlignmentFlag.AlignCenter)

        success_title = QLabel("✓ Registration Successful")
        success_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_title.setStyleSheet("font-size: 20px; font-weight: 800; color: #10B981;")
        success_layout.addWidget(success_title)

        success_desc = QLabel("Your account has been created successfully.")
        success_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_desc.setStyleSheet("font-size: 14px; color: #64748B; font-weight: 500;")
        success_layout.addWidget(success_desc)

        self.success_login_btn = QPushButton("Go to Login")
        self.success_login_btn.setFixedHeight(50)
        self.success_login_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.success_login_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #2563EB);
                color: #FFFFFF;
                border: none;
                border-radius: 12px;
                font-weight: 700;
                font-size: 15px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #1D4ED8);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1D4ED8, stop:1 #1E40AF);
            }
        """)
        self.success_login_btn.clicked.connect(self.on_go_to_login_clicked)
        success_layout.addWidget(self.success_login_btn)

        # Add pages to card stacked layout
        self.card_stack.addWidget(self.form_widget)
        self.card_stack.addWidget(self.success_widget)
        self.card_stack.setCurrentIndex(0)

        center_layout.addWidget(self.card)
        center_layout.addStretch()

        main_layout.addStretch()
        main_layout.addLayout(center_layout)
        main_layout.addStretch()

        # Connect text change events for validations once (never reconnect)
        self.name_input.textChanged.connect(lambda: self.on_field_changed("name"))
        self.email_input.textChanged.connect(lambda: self.on_field_changed("email"))
        self.phone_input.textChanged.connect(lambda: self.on_field_changed("phone"))
        self.pass_input.textChanged.connect(lambda: self.on_field_changed("password"))
        self.confirm_input.textChanged.connect(lambda: self.on_field_changed("confirm"))

        # Trigger validation check initially
        self.run_validation()

    def on_field_changed(self, field_name):
        if field_name == "name":
            self.name_touched = True
        elif field_name == "email":
            self.email_touched = True
        elif field_name == "phone":
            self.phone_touched = True
        elif field_name == "password":
            self.password_touched = True
            pwd = self.pass_input.text()
            self.req_widget.update_requirements(pwd)
            self.strength_widget.update_strength(pwd)
        elif field_name == "confirm":
            self.confirm_touched = True

        self.run_validation()

    def run_validation(self):
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        phone = self.phone_input.text().strip()
        password = self.pass_input.text()
        confirm = self.confirm_input.text()

        name_err = None
        email_err = None
        phone_err = None
        pass_err = None
        confirm_err = None

        # 1. Full name validation
        if not name:
            name_err = "❌ Full name is required"
        elif len(name) < 3:
            name_err = "❌ Full name must contain at least 3 letters"
        elif not all(c.isalpha() or c.isspace() for c in name):
            name_err = "❌ Full name can only contain alphabets and spaces"

        # 2. Email validation
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not email:
            email_err = "❌ Email is required"
        elif not re.match(email_regex, email):
            email_err = "❌ Email is invalid"

        # 3. Phone validation
        if not phone:
            phone_err = "❌ Phone number is required"
        elif not phone.isdigit():
            phone_err = "❌ Phone number must contain digits only"
        elif len(phone) != 10:
            phone_err = "❌ Phone number must contain exactly 10 digits"
        elif phone[0] not in "6789":
            phone_err = "❌ Phone number must be in Indian mobile format"

        # 4. Password validation
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        if not password:
            pass_err = "❌ Password is required"
        elif len(password) < 8:
            pass_err = "❌ Password must contain at least 8 characters"
        elif not any(c.isupper() for c in password):
            pass_err = "❌ Password must contain at least one uppercase letter"
        elif not any(c.islower() for c in password):
            pass_err = "❌ Password must contain at least one lowercase letter"
        elif not any(c.isdigit() for c in password):
            pass_err = "❌ Password must contain at least one number"
        elif not any(c in special_chars for c in password):
            pass_err = "❌ Password must contain one special character"

        # 5. Confirm password validation
        if not confirm:
            confirm_err = "❌ Confirm password is required"
        elif confirm != password:
            confirm_err = "❌ Passwords do not match"

        # Display validation
        if self.name_touched:
            self.name_input.set_error(name_err)
        if self.email_touched:
            self.email_input.set_error(email_err)
        if self.phone_touched:
            self.phone_input.set_error(phone_err)
        if self.password_touched:
            self.pass_input.set_error(pass_err)
        if self.confirm_touched:
            self.confirm_input.set_error(confirm_err)

        all_valid = (
            name_err is None and
            email_err is None and
            phone_err is None and
            pass_err is None and
            confirm_err is None
        )

        self.register_btn.setEnabled(all_valid)
        return all_valid

    def handle_registration(self):
        if not self.run_validation():
            return

        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        phone = self.phone_input.text().strip()
        password = self.pass_input.text()

        # Insert user details into AuthDB (MongoDB or local fallback)
        from utils.auth_db import AuthDB
        registered = AuthDB.register_user(name, email, phone, password)
        if not registered:
            self.email_input.set_error("❌ This email address is already registered.")
            return

        # Green toast notification in top-right corner
        toast = ToastNotification(self, "Account created successfully")
        toast.show_toast()

        # Transition stack to show success screen directly inside the card
        self.card_stack.setCurrentIndex(1)

    def on_go_to_login_clicked(self):
        """Emits transition to go back to login screen."""
        self.registerSuccess.emit()

    def clear_fields(self):
        """Resets field values and touches."""
        self.name_touched = False
        self.email_touched = False
        self.phone_touched = False
        self.password_touched = False
        self.confirm_touched = False

        self.name_input.clear()
        self.email_input.clear()
        self.phone_input.clear()
        self.pass_input.clear()
        self.confirm_input.clear()

        self.req_widget.update_requirements("")
        self.strength_widget.update_strength("")
        self.card_stack.setCurrentIndex(0)

        self.run_validation()

from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QWidget, QVBoxLayout
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt

from ui.welcome_screen import WelcomeScreen
from ui.login import LoginScreen
from ui.register import RegisterScreen
from ui.dashboard import DashboardScreen

class NavigationController(QMainWindow):
    """
    Main Window container for StatementForge. Manages the top-level
    stacked widgets and coordinates transitions between screens.
    """
    def __init__(self):
        super().__init__()
        
        # Configure Window
        self.setWindowTitle("StatementForge - Multi-Bank Statement Parser")
        self.setMinimumSize(1280, 720)
        self.resize(1440, 900)
        
        # Load and set application window icon
        app_icon = QIcon("assets/logo.png")
        self.setWindowIcon(app_icon)
        
        # Central stacked widget
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.stacked_widget = QStackedWidget(self)
        self.main_layout.addWidget(self.stacked_widget)
        
        # Instantiate Screens
        self.welcome_screen = WelcomeScreen(self)
        self.login_screen = LoginScreen(self)
        self.register_screen = RegisterScreen(self)
        self.dashboard_screen = DashboardScreen(self)
        
        # Add screens to stacked widget
        # Indices: 0: Welcome, 1: Login, 2: Register, 3: Dashboard
        self.stacked_widget.addWidget(self.welcome_screen)
        self.stacked_widget.addWidget(self.login_screen)
        self.stacked_widget.addWidget(self.register_screen)
        self.stacked_widget.addWidget(self.dashboard_screen)
        
        # Connect Navigation Signals
        self.connect_signals()
        
        # Default start page is Welcome
        self.show_welcome_page()

    def connect_signals(self):
        # Welcome Page transitions
        self.welcome_screen.gotoLogin.connect(self.show_login_page)
        self.welcome_screen.gotoRegister.connect(self.show_register_page)
        
        # Login Page transitions
        self.login_screen.gotoWelcome.connect(self.show_welcome_page)
        self.login_screen.gotoRegister.connect(self.show_register_page)
        self.login_screen.loginSuccess.connect(self.show_dashboard_page)
        
        # Register Page transitions
        self.register_screen.gotoWelcome.connect(self.show_welcome_page)
        self.register_screen.gotoLogin.connect(self.show_login_page)
        self.register_screen.registerSuccess.connect(self.show_login_page)
        
        # Dashboard Page transitions
        self.dashboard_screen.logoutRequested.connect(self.handle_logout)

    # --- Transition Helpers ---

    def show_welcome_page(self):
        self.stacked_widget.setCurrentIndex(0)

    def show_login_page(self):
        self.login_screen.clear_fields()
        self.stacked_widget.setCurrentIndex(1)

    def show_register_page(self):
        self.register_screen.clear_fields()
        self.stacked_widget.setCurrentIndex(2)

    def show_dashboard_page(self):
        # Reset dashboard page index to the home Dashboard tab view
        self.dashboard_screen.switch_dashboard_page("dashboard")
        self.stacked_widget.setCurrentIndex(3)

    def handle_logout(self):
        # Clear fields and redirect
        self.login_screen.clear_fields()
        self.register_screen.clear_fields()
        self.show_welcome_page()

from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QWidget, QVBoxLayout
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt

from ui.welcome_screen import WelcomeScreen
from ui.login import LoginScreen
from ui.register import RegisterScreen
from ui.dashboard import DashboardScreen
from utils.user_session import UserSession

class NavigationController(QMainWindow):
    """
    Main Window container for StatementForge. Manages the top-level
    stacked widgets and coordinates transitions between screens,
    including the dedicated ProfileWindow.
    """
    def __init__(self):
        super().__init__()
        
        # Configure Window
        self.setWindowTitle("StatementForge: Automated Bank Statement Parser and Accounting Hub")
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
        
        from ui.profile_window import ProfileWindow
        from controllers.profile_controller import ProfileController
        
        self.profile_window = ProfileWindow(self)
        self.profile_controller = ProfileController(self.profile_window)
        
        # Add screens to stacked widget
        # Indices: 0: Welcome, 1: Login, 2: Register, 3: Dashboard, 4: Profile
        self.stacked_widget.addWidget(self.welcome_screen)
        self.stacked_widget.addWidget(self.login_screen)
        self.stacked_widget.addWidget(self.register_screen)
        self.stacked_widget.addWidget(self.dashboard_screen)
        self.stacked_widget.addWidget(self.profile_window)

        # Connect Navigation Signals
        self.connect_signals()
        
        # Check for active persistent session and auto-login
        saved_user = UserSession.load_session()
        if saved_user:
            self.show_dashboard_page(saved_user)
        else:
            self.show_welcome_page()

        # Synchronize theme at startup
        from utils.theme_manager import ThemeManager
        self.sync_theme_styles(ThemeManager.get_theme())

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
        
        # Connect Topbar User Profile Click
        self.dashboard_screen.topbar.profile_widget.clicked.connect(self.open_profile_window)
        
        # Profile Page transitions
        self.profile_window.back_to_dashboard.connect(self.close_profile_window)
        self.profile_window.logout_requested.connect(self.handle_profile_logout)
        self.profile_window.profile_updated.connect(self.sync_profile_details)

    # --- Transition Helpers ---

    def show_welcome_page(self):
        self.stacked_widget.setCurrentIndex(0)

    def show_login_page(self):
        self.login_screen.clear_fields()
        self.stacked_widget.setCurrentIndex(1)

    def show_register_page(self):
        self.register_screen.clear_fields()
        self.stacked_widget.setCurrentIndex(2)

    def show_dashboard_page(self, user_details):
        # Start user session
        UserSession.start_session(user_details)
        
        # Update user profile in dashboard
        self.dashboard_screen.set_user_profile(user_details)
        # Reset dashboard page index to the home Dashboard tab view
        self.dashboard_screen.switch_dashboard_page("dashboard")
        self.stacked_widget.setCurrentIndex(3)

    def handle_logout(self):
        # Clear User Session
        UserSession.clear_session()
        
        # Clear fields and redirect
        self.login_screen.clear_fields()
        self.register_screen.clear_fields()
        self.show_welcome_page()

    def open_profile_window(self):
        """Switches to the profile page."""
        user = UserSession.get_current_user()
        if user:
            self.profile_window.load_user_data(user)
            
        self.stacked_widget.setCurrentWidget(self.profile_window)

    def close_profile_window(self):
        """Restores the main window dashboard view."""
        # Re-sync welcome label & topbar details
        user = UserSession.get_current_user()
        if user:
            self.dashboard_screen.set_user_profile(user)
            
        self.stacked_widget.setCurrentWidget(self.dashboard_screen)

    def handle_profile_logout(self):
        """Redirects logout events originating from the profile window."""
        self.handle_logout()

    def sync_profile_details(self, user_details):
        """Syncs updated details in real-time onto the dashboard layout."""
        self.dashboard_screen.set_user_profile(user_details)

    def sync_theme_styles(self, theme):
        """Propagates active theme settings to all instantiated pages."""
        if hasattr(self, "dashboard_screen") and self.dashboard_screen is not None:
            self.dashboard_screen.update_theme_styles(theme)
            if hasattr(self.dashboard_screen, "topbar") and self.dashboard_screen.topbar is not None:
                self.dashboard_screen.topbar.update_theme_icon(theme)

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal
from ui.html_screen_wrapper import HtmlScreenWrapper

class WelcomeScreen(QWidget):
    """
    Landing / Welcome Screen of the application rendered via HTML, CSS, and JS.
    """
    gotoLogin = pyqtSignal()
    gotoRegister = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.html_wrapper = HtmlScreenWrapper("web/welcome.html", self)
        layout.addWidget(self.html_wrapper)
        
        # Connect bridge signals to window signals
        self.html_wrapper.bridge.gotoLogin.connect(self.gotoLogin.emit)
        self.html_wrapper.bridge.gotoRegister.connect(self.gotoRegister.emit)

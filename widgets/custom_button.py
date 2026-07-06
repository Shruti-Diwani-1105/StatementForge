from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor

class BaseButton(QPushButton):
    """Base button that sets the pointing hand cursor."""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))


class PrimaryButton(BaseButton):
    """A premium primary action button (Royal Blue)."""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setObjectName("PrimaryButton")


class SecondaryButton(BaseButton):
    """A premium outline action button (White/Slate Gray)."""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setObjectName("SecondaryButton")


class LinkButton(BaseButton):
    """A flat text link button for auxiliary actions (Register/Forgot Password)."""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setObjectName("LinkButton")

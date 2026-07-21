import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget,
    QScrollArea, QFrame, QLineEdit, QPushButton, QComboBox, QCheckBox,
    QSlider, QTextEdit, QFileDialog, QSizePolicy, QSpacerItem, QGraphicsOpacityEffect,
    QGridLayout, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QTimer, pyqtProperty, QRectF
from PyQt6.QtGui import QCursor, QPixmap, QFont, QPainter, QColor, QBrush, QPen

from settings.widgets.setting_card import SettingCard
from settings.widgets.toggle_switch import ToggleSwitch
from settings.widgets.sidebar_item import SettingsSidebarItem
from settings.widgets.password_input import PasswordInput
from settings.widgets.color_selector import ColorSelector
from settings.widgets.avatar_widget import AvatarWidget

class AnimatedButton(QPushButton):
    def __init__(self, text, button_type="secondary", parent=None):
        super().__init__(text, parent)
        self.button_type = button_type  # "cancel", "restore", "save"
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(44)
        
        # Hover progress property (0.0 to 1.0)
        self._hover_progress = 0.0
        self.hover_anim = QPropertyAnimation(self, b"hover_progress", self)
        self.hover_anim.setDuration(150)
        
        # Pressed state tracking
        self.is_pressed = False
        
        # Active theme reference
        self.current_theme = "light"
        
    @pyqtProperty(float)
    def hover_progress(self):
        return self._hover_progress
        
    @hover_progress.setter
    def hover_progress(self, val):
        self._hover_progress = val
        self.update()
        
    def enterEvent(self, event):
        if self.isEnabled():
            self.hover_anim.stop()
            self.hover_anim.setStartValue(self._hover_progress)
            self.hover_anim.setEndValue(1.0)
            self.hover_anim.start()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        if self.isEnabled():
            self.hover_anim.stop()
            self.hover_anim.setStartValue(self._hover_progress)
            self.hover_anim.setEndValue(0.0)
            self.hover_anim.start()
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        if self.isEnabled() and event.button() == Qt.MouseButton.LeftButton:
            self.is_pressed = True
            self.update()
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_pressed = False
            self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Determine theme and state colors
        is_dark = self.current_theme == "dark"
        is_enabled = self.isEnabled()
        
        rect = QRectF(0, 0, self.width(), self.height())
        draw_rect = rect.adjusted(0.5, 0.5, -0.5, -0.5)
        
        # Scale parameters based on zoom factor
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        zoom_factor = getattr(app, 'zoom_factor', 1.0)
        window_scale = getattr(app, 'window_scale', 1.0)
        effective_zoom = zoom_factor * window_scale
        
        radius = int(10 * effective_zoom)
        font_size = int(10 * effective_zoom)

        # Color helper to interpolate
        def interpolate_color(color1, color2, progress):
            r = int(color1.red() + (color2.red() - color1.red()) * progress)
            g = int(color1.green() + (color2.green() - color1.green()) * progress)
            b = int(color1.blue() + (color2.blue() - color1.blue()) * progress)
            a = int(color1.alpha() + (color2.alpha() - color1.alpha()) * progress)
            return QColor(r, g, b, a)
            
        if self.button_type == "cancel":
            # Outlined secondary button
            if is_dark:
                base_border = QColor("#334155")
                hover_border = QColor("#475569")
                base_bg = QColor(30, 41, 59, 0) # transparent
                hover_bg = QColor(255, 255, 255, 12) # ~0.05 opacity
                text_color = QColor("#E2E8F0")
            else:
                base_border = QColor("#CBD5E1")
                hover_border = QColor("#94A3B8")
                base_bg = QColor(255, 255, 255, 0) # transparent
                hover_bg = QColor(15, 23, 42, 12) # ~0.05 opacity
                text_color = QColor("#4B5563")
                
            if not is_enabled:
                text_color = QColor("#475569") if is_dark else QColor("#9CA3AF")
                border_color = QColor("#1E293B") if is_dark else QColor("#E5E7EB")
                bg_color = QColor(0, 0, 0, 0)
            else:
                bg_color = interpolate_color(base_bg, hover_bg, self._hover_progress)
                border_color = interpolate_color(base_border, hover_border, self._hover_progress)
                
            painter.setPen(QPen(border_color, 1))
            painter.setBrush(QBrush(bg_color))
            painter.drawRoundedRect(draw_rect, radius, radius)
            
        elif self.button_type == "restore":
            # Soft grey filled background
            if is_dark:
                base_bg = QColor("#334155")
                hover_bg = QColor("#475569")
                pressed_bg = QColor("#1E293B")
                text_color = QColor("#F8FAFC")
            else:
                base_bg = QColor("#F3F4F6")
                hover_bg = QColor("#E5E7EB")
                pressed_bg = QColor("#D1D5DB")
                text_color = QColor("#374151")
                
            if not is_enabled:
                bg_color = QColor("#1E293B") if is_dark else QColor("#F9FAFB")
                text_color = QColor("#475569") if is_dark else QColor("#D1D5DB")
            else:
                if self.is_pressed:
                    bg_color = pressed_bg
                else:
                    bg_color = interpolate_color(base_bg, hover_bg, self._hover_progress)
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bg_color))
            painter.drawRoundedRect(draw_rect, radius, radius)
            
        elif self.button_type == "save":
            # Primary blue background
            base_bg = QColor("#0037b0")
            hover_bg = QColor("#1d4ed8")
            pressed_bg = QColor("#002c8c")
            text_color = QColor("#FFFFFF")
            
            if not is_enabled:
                bg_color = QColor("#1E293B") if is_dark else QColor("#F3F4F6")
                text_color = QColor("#475569") if is_dark else QColor("#9CA3AF")
            else:
                if self.is_pressed:
                    bg_color = pressed_bg
                else:
                    bg_color = interpolate_color(base_bg, hover_bg, self._hover_progress)
                    
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bg_color))
            painter.drawRoundedRect(draw_rect, radius, radius)
            
        # Draw Text / Icon
        painter.setPen(text_color)
        font = self.font()
        font.setFamily("Times New Roman")
        font.setPointSize(font_size)
        if self.button_type == "save":
            font.setBold(True)
        else:
            font.setBold(False)
        painter.setFont(font)
        
        # Center the text
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())
        painter.end()


class SettingsWindow(QWidget):
    """
    Main View for the Settings module.
    Presents a two-column layout with a left sidebar nav list and a right settings stacked panel.
    Incorporates inline error labels, active theme updates, and a sticky footer.
    """
    # Signals for Controller interactions
    save_clicked = pyqtSignal()
    apply_clicked = pyqtSignal()
    cancel_clicked = pyqtSignal()
    restore_defaults_clicked = pyqtSignal()
    
    # Test connection clicks
    test_db_clicked = pyqtSignal(str)
    test_gemini_clicked = pyqtSignal(str)
    test_email_clicked = pyqtSignal(str, str, str, str)
    
    # Action clicks
    backup_db_clicked = pyqtSignal(str)
    restore_db_clicked = pyqtSignal(str)
    export_db_clicked = pyqtSignal(str)
    view_db_stats_clicked = pyqtSignal(str)
    clear_session_clicked = pyqtSignal()
    reset_auth_clicked = pyqtSignal()
    check_updates_clicked = pyqtSignal()
    logout_clicked = pyqtSignal()
    
    # Edit profile inline
    edit_profile_clicked = pyqtSignal()
    change_password_clicked = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsScreenRoot")
        self.active_tab_key = "general"
        
        # Base UI layout setup
        self.init_ui()
        
    def init_ui(self):
        # Top-level vertical layout for modern Settings screen
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 24, 32, 24)
        main_layout.setSpacing(20)
        
        # 1. TOP SEGMENTED TAB BAR CONTAINER
        self.tab_bar_frame = QFrame()
        self.tab_bar_frame.setObjectName("SettingsTabBar")
        self.tab_bar_frame.setFixedHeight(48)
        
        tab_bar_layout = QHBoxLayout(self.tab_bar_frame)
        tab_bar_layout.setContentsMargins(6, 6, 6, 6)
        tab_bar_layout.setSpacing(6)
        
        # Segmented buttons specification
        self.sidebar_nav_items = [
            ("General", "general", "dashboard"),
            ("Account", "account", "profile"),
            ("Appearance", "appearance", "reports"),
            ("Notifications", "notifications", "bell"),
            ("About", "about", "info")
        ]
        
        self.nav_buttons = {}
        for label, key, icon in self.sidebar_nav_items:
            btn = SettingsSidebarItem(label, key, icon)
            btn.clicked.connect(lambda checked, k=key: self.switch_tab(k))
            tab_bar_layout.addWidget(btn)
            self.nav_buttons[key] = btn
            
        tab_bar_layout.addStretch()
        main_layout.addWidget(self.tab_bar_frame)
        
        # 2. CONTENT CONTAINER (Scroll area wrapping Stacked Widget)
        self.content_scroll = QScrollArea()
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content_scroll.setStyleSheet("background: transparent; border: none;")
        
        self.right_stack = QStackedWidget()
        self.opacity_effect = QGraphicsOpacityEffect(self.right_stack)
        self.right_stack.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)
        self.content_scroll.setWidget(self.right_stack)
        main_layout.addWidget(self.content_scroll, stretch=1)
        
        # 3. STICKY FOOTER
        self.footer_frame = QFrame()
        self.footer_frame.setObjectName("SettingsStickyFooter")
        self.footer_frame.setFixedHeight(80)
        
        # Soft top shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setXOffset(0)
        shadow.setYOffset(-3)
        shadow.setColor(QColor(0, 0, 0, 13)) # rgba(0,0,0,0.05)
        self.footer_frame.setGraphicsEffect(shadow)
        
        footer_layout = QHBoxLayout(self.footer_frame)
        footer_layout.setContentsMargins(24, 0, 24, 0)
        footer_layout.setSpacing(12)
        
        # Left side status indicator
        self.status_container = QWidget()
        self.status_container.setObjectName("StatusContainer")
        self.status_container.setStyleSheet("background: transparent; border: none;")
        status_layout = QHBoxLayout(self.status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(8)
        
        self.status_icon = QLabel()
        self.status_icon.setFixedSize(8, 8)
        self.status_icon.setStyleSheet("background-color: #10B981; border-radius: 4px; border: none;")
        
        self.status_text = QLabel("All changes saved")
        self.status_text.setFont(QFont("Times New Roman", 10, QFont.Weight.Medium))
        self.status_text.setStyleSheet("color: #6B7280; border: none; background: transparent;")
        
        status_layout.addWidget(self.status_icon, 0, Qt.AlignmentFlag.AlignVCenter)
        status_layout.addWidget(self.status_text, 0, Qt.AlignmentFlag.AlignVCenter)
        
        footer_layout.addWidget(self.status_container, 0, Qt.AlignmentFlag.AlignVCenter)
        
        # Spacer between left status and right buttons
        footer_layout.addStretch(1)
        
        # Footer Action Buttons
        self.btn_cancel = AnimatedButton("Cancel", "cancel")
        self.btn_cancel.clicked.connect(self.cancel_clicked.emit)
        self.btn_cancel.setMinimumWidth(90)
        footer_layout.addWidget(self.btn_cancel, 0, Qt.AlignmentFlag.AlignVCenter)
        
        self.btn_restore = AnimatedButton("↻  Restore Defaults", "restore")
        self.btn_restore.clicked.connect(self.restore_defaults_clicked.emit)
        self.btn_restore.setMinimumWidth(150)
        footer_layout.addWidget(self.btn_restore, 0, Qt.AlignmentFlag.AlignVCenter)
        
        self.btn_save = AnimatedButton("Save Changes", "save")
        self.btn_save.clicked.connect(self.save_clicked.emit)
        self.btn_save.setMinimumWidth(130)
        footer_layout.addWidget(self.btn_save, 0, Qt.AlignmentFlag.AlignVCenter)
        
        main_layout.addWidget(self.footer_frame)
        
        # Initialize stacked pages
        self.create_pages()
        
        # Set default tab
        self.switch_tab("general")
        self.set_buttons_dirty(False)
        
        # Styling integration
        from utils.theme_manager import ThemeManager
        self.update_theme_style(ThemeManager.get_theme())

    def update_theme_style(self, theme):
        """Applies layout panel QSS styles dynamically based on theme."""
        self.current_theme = theme
        
        # Propagate theme down to custom elements
        for btn in self.nav_buttons.values():
            btn.update_theme_style(theme)
            
        self.color_selector.update_theme(theme)
        self.avatar.update_theme(theme)
        
        # Propagate theme update to cards
        for card in self.findChildren(SettingCard):
            card.update_theme_style(theme)
            
        # Synchronize Visual Theme dropdown if exists
        if hasattr(self, "app_theme") and self.app_theme is not None:
            self.app_theme.blockSignals(True)
            self.app_theme.setCurrentText(theme.capitalize())
            self.app_theme.blockSignals(False)
            
        # Synchronize page header labels
        title_style = "font-size: 22px; font-weight: 800; color: #F8FAFC;" if theme == "dark" else "font-size: 22px; font-weight: 800; color: #0F172A;"
        sub_style = "font-size: 13px; color: #94A3B8; font-weight: 500;" if theme == "dark" else "font-size: 13px; color: #64748B; font-weight: 500;"
        for title_lbl in self.findChildren(QLabel, "SettingsPageTitle"):
            title_lbl.setStyleSheet(title_style)
        for sub_lbl in self.findChildren(QLabel, "SettingsPageSubtitle"):
            sub_lbl.setStyleSheet(sub_style)
            
        # Synchronize about page elements
        about_title_style = "font-size: 18px; font-weight: bold; color: #F8FAFC;" if theme == "dark" else "font-size: 18px; font-weight: bold; color: #0F172A;"
        about_version_style = "font-weight: 500; color: #94A3B8;" if theme == "dark" else "font-weight: 500; color: #64748B;"
        for t in self.findChildren(QLabel, "AboutTitle"):
            t.setStyleSheet(about_title_style)
        for v in self.findChildren(QLabel, "AboutVersion"):
            v.setStyleSheet(about_version_style)
            
        if theme == "dark":
            self.setStyleSheet("""
                QWidget#SettingsScreenRoot {
                    background-color: #0F172A;
                    color: #F8FAFC;
                }
                QFrame#SettingsStickyFooter {
                    background-color: #1E293B;
                    border-top: 1px solid #334155;
                    border-top-left-radius: 12px;
                    border-top-right-radius: 12px;
                }
                QLabel {
                    color: #F8FAFC;
                }
            """)
            # Update specific controls
            combo_style = """
                QComboBox {
                    background-color: #0F172A;
                    border: 1px solid #334155;
                    border-radius: 8px;
                    padding: 8px 12px;
                    color: #F8FAFC;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 26px;
                }
                QComboBox QAbstractItemView {
                    background-color: #1E293B;
                    border: 1px solid #334155;
                    selection-background-color: #3B82F6;
                    selection-color: #FFFFFF;
                    color: #F8FAFC;
                }
            """
            for combo in self.findChildren(QComboBox):
                combo.setStyleSheet(combo_style)
                
            input_style = """
                QLineEdit {
                    background-color: #0F172A;
                    border: 1px solid #334155;
                    border-radius: 8px;
                    padding: 8px 12px;
                    color: #F8FAFC;
                }
                QLineEdit:focus {
                    border-color: #3B82F6;
                }
            """
            for line_edit in self.findChildren(QLineEdit):
                if line_edit.parent() and "PasswordInput" in line_edit.parent().metaObject().className():
                    continue # Skip password widgets which manage themselves
                line_edit.setStyleSheet(input_style)
                
            text_style = """
                QTextEdit {
                    background-color: #0F172A;
                    border: 1px solid #334155;
                    border-radius: 8px;
                    padding: 8px 12px;
                    color: #F8FAFC;
                }
                QTextEdit:focus {
                    border-color: #3B82F6;
                }
            """
            for text_edit in self.findChildren(QTextEdit):
                text_edit.setStyleSheet(text_style)
                
            # Sliders
            for slider in self.findChildren(QSlider):
                slider.setStyleSheet("""
                    QSlider::groove:horizontal {
                        border: none;
                        height: 6px;
                        background: #334155;
                        border-radius: 3px;
                    }
                    QSlider::handle:horizontal {
                        background: #3B82F6;
                        border: none;
                        width: 16px;
                        height: 16px;
                        margin: -5px 0;
                        border-radius: 8px;
                    }
                """)
        else:
            self.setStyleSheet("""
                QWidget#SettingsScreenRoot {
                    background-color: #F8FAFC;
                    color: #0F172A;
                }
                QFrame#SettingsStickyFooter {
                    background-color: #FFFFFF;
                    border-top: 1px solid #E5E7EB;
                    border-top-left-radius: 12px;
                    border-top-right-radius: 12px;
                }
                QLabel {
                    color: #0F172A;
                }
            """)
            combo_style = """
                QComboBox {
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    border-radius: 8px;
                    padding: 8px 12px;
                    color: #0F172A;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 26px;
                }
                QComboBox QAbstractItemView {
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    selection-background-color: #0037b0;
                    selection-color: #FFFFFF;
                }
            """
            for combo in self.findChildren(QComboBox):
                combo.setStyleSheet(combo_style)
                
            input_style = """
                QLineEdit {
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    border-radius: 8px;
                    padding: 8px 12px;
                    color: #0F172A;
                }
                QLineEdit:focus {
                    border-color: #0037b0;
                }
            """
            for line_edit in self.findChildren(QLineEdit):
                if line_edit.parent() and "PasswordInput" in line_edit.parent().metaObject().className():
                    continue
                line_edit.setStyleSheet(input_style)
                
            text_style = """
                QTextEdit {
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    border-radius: 8px;
                    padding: 8px 12px;
                    color: #0F172A;
                }
                QTextEdit:focus {
                    border-color: #0037b0;
                }
            """
            for text_edit in self.findChildren(QTextEdit):
                text_edit.setStyleSheet(text_style)
                
            for slider in self.findChildren(QSlider):
                slider.setStyleSheet("""
                    QSlider::groove:horizontal {
                        border: none;
                        height: 6px;
                        background: #E2E8F0;
                        border-radius: 3px;
                    }
                    QSlider::handle:horizontal {
                        background: #0037b0;
                        border: none;
                        width: 16px;
                        height: 16px;
                        margin: -5px 0;
                        border-radius: 8px;
                    }
                """)
        
        # Propagate theme down to animated buttons and left status
        if hasattr(self, "btn_cancel"):
            self.btn_cancel.current_theme = theme
            self.btn_cancel.update()
        if hasattr(self, "btn_restore"):
            self.btn_restore.current_theme = theme
            self.btn_restore.update()
        if hasattr(self, "btn_save"):
            self.btn_save.current_theme = theme
            self.btn_save.update()
            
        if hasattr(self, "btn_save"):
            self.set_buttons_dirty(self.btn_save.isEnabled())

    def switch_tab(self, key):
        """Switches the right stacked widget tab index with a smooth fade animation."""
        mapping = {
            "general": 0, "account": 1, "appearance": 2, "notifications": 3, "about": 4
        }
        if key not in mapping:
            return
            
        self.active_tab_key = key
        
        # Update checked item in sidebar
        for k, btn in self.nav_buttons.items():
            btn.setChecked(k == key)
            
        # Trigger fade transition
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(120)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        
        def on_fade_out():
            self.right_stack.setCurrentIndex(mapping[key])
            
            # Reset scroll position to top when switching tab
            self.content_scroll.verticalScrollBar().setValue(0)
            
            # Fade back in
            self.anim_in = QPropertyAnimation(self.opacity_effect, b"opacity")
            self.anim_in.setDuration(120)
            self.anim_in.setStartValue(0.0)
            self.anim_in.setEndValue(1.0)
            self.anim_in.start()
            
        self.anim.finished.connect(on_fade_out)
        self.anim.start()

    def set_buttons_dirty(self, dirty):
        """Enables/disables footer actions based on dirty flags."""
        self.btn_save.setEnabled(dirty)
        self.btn_cancel.setEnabled(dirty)
        
        is_dark = getattr(self, "current_theme", "light") == "dark"
        text_color = "#94A3B8" if is_dark else "#6B7280"
        self.status_text.setStyleSheet(f"color: {text_color}; border: none; background: transparent;")
        
        if dirty:
            self.status_icon.setStyleSheet("background-color: #F59E0B; border-radius: 4px; border: none;")
            self.status_text.setText("Changes not saved")
        else:
            self.status_icon.setStyleSheet("background-color: #10B981; border-radius: 4px; border: none;")
            self.status_text.setText("All changes saved")

    # ----------------------------------------------------
    # CARD LAYOUT CONSTRUCTORS FOR PAGES
    # ----------------------------------------------------
    
    def create_pages(self):
        """Builds all 5 settings tabs, inserting them into QStackedWidget."""
        self.pages = []
        for _ in range(5):
            pg = QWidget()
            pg.setStyleSheet("background: transparent;")
            lay = QVBoxLayout(pg)
            lay.setContentsMargins(32, 24, 32, 24)
            lay.setSpacing(20)
            lay.setAlignment(Qt.AlignmentFlag.AlignTop)
            self.right_stack.addWidget(pg)
            self.pages.append((pg, lay))
            
        # Add page-specific cards
        self._build_general_page()
        self._build_account_page()
        self._build_appearance_page()
        self._build_notifications_page()
        self._build_about_page()

    def _build_general_page(self):
        _, layout = self.pages[0]
        
        # Header title
        self._add_page_header(layout, "General Settings", "Configure basic application behaviors and file systems.")
        
        # Card 1: App details
        card1 = SettingCard("Application Identity", "Identity attributes and specifications.")
        grid1 = QHBoxLayout()
        grid1.addWidget(QLabel("Application Name:"))
        self.gen_app_name = QLineEdit()
        grid1.addWidget(self.gen_app_name)
        
        self.gen_app_version = QLabel("Current Version: v1.0")
        self.gen_app_version.setStyleSheet("font-weight: bold; color: #64748B;")
        
        card1.add_layout(grid1)
        card1.add_widget(self.gen_app_version)
        layout.addWidget(card1)
        
        # Card 2: Files & Language
        card2 = SettingCard("Storage & Localization", "Preferences for files and interface lang.")
        grid2 = QGridLayout()
        
        # Save Location
        grid2.addWidget(QLabel("Default Save Location:"), 0, 0)
        self.gen_save_location = QLineEdit()
        self.gen_save_location_err = self._create_error_label()
        
        browse_btn = QPushButton("Browse")
        browse_btn.setObjectName("SecondaryButton")
        browse_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        browse_btn.clicked.connect(self._browse_save_location)
        
        row_save = QHBoxLayout()
        row_save.addWidget(self.gen_save_location)
        row_save.addWidget(browse_btn)
        
        grid2.addLayout(row_save, 0, 1)
        grid2.addWidget(self.gen_save_location_err, 1, 1)
        
        # Language
        grid2.addWidget(QLabel("Language:"), 2, 0)
        self.gen_lang = QComboBox()
        self.gen_lang.addItems(["English (US/UK)", "Spanish (Español)", "French (Français)", "German (Deutsch)"])
        grid2.addWidget(self.gen_lang, 2, 1)
        
        card2.add_layout(grid2)
        
        # Auto save toggle
        self.gen_auto_save = QCheckBox("Enable Automatic Settings Syncing")
        self.gen_auto_save.setStyleSheet("font-weight: 500;")
        card2.add_widget(self.gen_auto_save)
        
        layout.addWidget(card2)
        
        # Card 3: Actions
        card3 = SettingCard("Updates & Controls", "Check for software upgrades or trigger resets.")
        btn_update = QPushButton("Check for Updates")
        btn_update.setObjectName("SecondaryButton")
        btn_update.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_update.clicked.connect(self.check_updates_clicked.emit)
        
        card3.add_widget(btn_update)
        layout.addWidget(card3)

    def _build_account_page(self):
        _, layout = self.pages[1]
        self._add_page_header(layout, "My Account", "Manage personal profile information, roles, and password updates.")
        
        card1 = SettingCard("Profile Information", "Details representing the active logged-in user.")
        h_lay = QHBoxLayout()
        
        # Avatar on left
        self.avatar = AvatarWidget(96)
        h_lay.addWidget(self.avatar)
        
        # Form details on right
        form_lay = QGridLayout()
        
        form_lay.addWidget(QLabel("Username:"), 0, 0)
        self.acc_username = QLineEdit()
        self.acc_username_err = self._create_error_label()
        form_lay.addWidget(self.acc_username, 0, 1)
        form_lay.addWidget(self.acc_username_err, 1, 1)

        form_lay.addWidget(QLabel("Full Name:"), 2, 0)
        self.acc_name = QLineEdit()
        self.acc_name_err = self._create_error_label()
        form_lay.addWidget(self.acc_name, 2, 1)
        form_lay.addWidget(self.acc_name_err, 3, 1)
        
        form_lay.addWidget(QLabel("Email:"), 4, 0)
        self.acc_email = QLineEdit()
        self.acc_email.setReadOnly(True)
        form_lay.addWidget(self.acc_email, 4, 1)
        
        form_lay.addWidget(QLabel("Phone Number:"), 5, 0)
        self.acc_phone = QLineEdit()
        self.acc_phone_err = self._create_error_label()
        form_lay.addWidget(self.acc_phone, 5, 1)
        form_lay.addWidget(self.acc_phone_err, 6, 1)
        
        form_lay.addWidget(QLabel("Role:"), 7, 0)
        self.acc_role_lbl = QLabel("User")
        self.acc_role_lbl.setStyleSheet("font-weight: bold; color: #3B82F6;")
        form_lay.addWidget(self.acc_role_lbl, 7, 1)
        
        form_lay.addWidget(QLabel("Member Since:"), 8, 0)
        self.acc_date_lbl = QLabel("N/A")
        self.acc_date_lbl.setStyleSheet("color: #64748B;")
        form_lay.addWidget(self.acc_date_lbl, 8, 1)
        
        h_lay.addLayout(form_lay, stretch=1)
        card1.add_layout(h_lay)
        
        # Action Buttons inside card
        btn_layout = QHBoxLayout()
        self.btn_edit_profile = QPushButton("Update Profile")
        self.btn_edit_profile.setObjectName("PrimaryButton")
        self.btn_edit_profile.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_edit_profile.clicked.connect(self.edit_profile_clicked.emit)
        btn_layout.addWidget(self.btn_edit_profile)
        
        card1.add_layout(btn_layout)
        layout.addWidget(card1)
        
        # Card 2: Password
        card2 = SettingCard("Change Account Password", "Establish a new login password to secure statement access.")
        pwd_grid = QGridLayout()
        pwd_grid.addWidget(QLabel("Old Password:"), 0, 0)
        self.acc_old_pwd = QLineEdit()
        self.acc_old_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        pwd_grid.addWidget(self.acc_old_pwd, 0, 1)
        
        pwd_grid.addWidget(QLabel("New Password:"), 1, 0)
        self.acc_new_pwd = QLineEdit()
        self.acc_new_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        pwd_grid.addWidget(self.acc_new_pwd, 1, 1)
        
        self.acc_pwd_err = self._create_error_label()
        pwd_grid.addWidget(self.acc_pwd_err, 2, 1)
        
        card2.add_layout(pwd_grid)
        
        self.btn_change_pwd = QPushButton("Modify Password")
        self.btn_change_pwd.setObjectName("SecondaryButton")
        self.btn_change_pwd.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_change_pwd.clicked.connect(self._trigger_change_password)
        card2.add_widget(self.btn_change_pwd)
        
        layout.addWidget(card2)

    def _build_ai_page(self):
        _, layout = self.pages[2]
        self._add_page_header(layout, "AI Configuration", "Configure credentials and parameters for AI LLM integration.")
        
        # Card 1: Main Toggle & API Key
        card1 = SettingCard("AI Integration", "Authorize parser to interact with AI API services.")
        
        # Toggle AI
        row_ai = QHBoxLayout()
        row_ai.addWidget(QLabel("Enable AI Parsing:"))
        self.ai_enabled = ToggleSwitch()
        row_ai.addWidget(self.ai_enabled)
        row_ai.addStretch()
        card1.add_layout(row_ai)
        
        # API Key password widget
        card1.add_widget(QLabel("AI API Key:"))
        self.ai_api_key_field = PasswordInput("Enter AI Studio API Key")
        self.ai_api_key_err = self._create_error_label()
        card1.add_widget(self.ai_api_key_field)
        card1.add_widget(self.ai_api_key_err)
        
        # Test Connection & status badge
        row_test = QHBoxLayout()
        self.btn_test_gemini = QPushButton("Test AI Connection")
        self.btn_test_gemini.setObjectName("SecondaryButton")
        self.btn_test_gemini.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_test_gemini.clicked.connect(lambda: self.test_gemini_clicked.emit(self.ai_api_key_field.text()))
        row_test.addWidget(self.btn_test_gemini)
        
        self.gemini_status_badge = QLabel("Disconnected")
        self.gemini_status_badge.setFixedSize(100, 22)
        self.gemini_status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gemini_status_badge.setStyleSheet("background-color: #F1F5F9; color: #64748B; border-radius: 6px; font-weight: bold; font-size: 11px;")
        row_test.addWidget(self.gemini_status_badge)
        row_test.addStretch()
        
        card1.add_layout(row_test)
        layout.addWidget(card1)
        
        # Card 2: Parameters
        card2 = SettingCard("Model & Generation Parameters", "Adjust response predictability and limits.")
        grid = QGridLayout()
        
        # Model
        grid.addWidget(QLabel("Current Model:"), 0, 0)
        self.ai_model = QComboBox()
        self.ai_model.addItems(["Gemini 2.5 Flash", "Gemini 2.5 Pro", "Gemini 1.5 Flash", "Gemini 1.5 Pro"])
        grid.addWidget(self.ai_model, 0, 1)
        
        # Temperature Slider
        grid.addWidget(QLabel("Temperature:"), 1, 0)
        self.ai_temp = QSlider(Qt.Orientation.Horizontal)
        self.ai_temp.setRange(0, 200) # representing 0.0 to 2.0
        self.ai_temp.setValue(70)
        self.ai_temp_val = QLabel("0.7")
        self.ai_temp_val.setFixedWidth(30)
        self.ai_temp.valueChanged.connect(lambda v: self.ai_temp_val.setText(f"{v/100:.2f}"))
        
        row_temp = QHBoxLayout()
        row_temp.addWidget(self.ai_temp)
        row_temp.addWidget(self.ai_temp_val)
        grid.addLayout(row_temp, 1, 1)
        
        # Max Tokens
        grid.addWidget(QLabel("Max Output Tokens:"), 2, 0)
        self.ai_max_tokens = QLineEdit()
        self.ai_max_tokens.setText("2048")
        grid.addWidget(self.ai_max_tokens, 2, 1)
        
        # Top P
        grid.addWidget(QLabel("Top P:"), 3, 0)
        self.ai_top_p = QSlider(Qt.Orientation.Horizontal)
        self.ai_top_p.setRange(0, 100)
        self.ai_top_p.setValue(95)
        self.ai_top_p_val = QLabel("0.95")
        self.ai_top_p_val.setFixedWidth(30)
        self.ai_top_p.valueChanged.connect(lambda v: self.ai_top_p_val.setText(f"{v/100:.2f}"))
        
        row_p = QHBoxLayout()
        row_p.addWidget(self.ai_top_p)
        row_p.addWidget(self.ai_top_p_val)
        grid.addLayout(row_p, 3, 1)
        
        # Top K
        grid.addWidget(QLabel("Top K:"), 4, 0)
        self.ai_top_k = QSlider(Qt.Orientation.Horizontal)
        self.ai_top_k.setRange(1, 100)
        self.ai_top_k.setValue(40)
        self.ai_top_k_val = QLabel("40")
        self.ai_top_k_val.setFixedWidth(30)
        self.ai_top_k.valueChanged.connect(lambda v: self.ai_top_k_val.setText(str(v)))
        
        row_k = QHBoxLayout()
        row_k.addWidget(self.ai_top_k)
        row_k.addWidget(self.ai_top_k_val)
        grid.addLayout(row_k, 4, 1)
        
        card2.add_layout(grid)
        layout.addWidget(card2)
        
        # Card 3: System Prompt
        card3 = SettingCard("System Prompt Rules", "System instructions injected before financial processing.")
        self.ai_system_prompt = QTextEdit()
        self.ai_system_prompt.setFixedHeight(120)
        card3.add_widget(self.ai_system_prompt)
        
        self.btn_reset_prompt = QPushButton("Restore Default Prompt")
        self.btn_reset_prompt.setObjectName("SecondaryButton")
        self.btn_reset_prompt.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        card3.add_widget(self.btn_reset_prompt)
        
        layout.addWidget(card3)

    def _build_processing_page(self):
        _, layout = self.pages[3]
        self._add_page_header(layout, "Statement Processing", "Configure parsing, OCR preprocessing, and cleanup algorithms.")
        
        # Card 1: Engines
        card1 = SettingCard("Text Extraction Settings", "Control how PDF statements convert to plain text.")
        row_ocr = QHBoxLayout()
        row_ocr.addWidget(QLabel("Enable OCR (Image Statement Processing):"))
        self.sp_ocr_enabled = ToggleSwitch()
        row_ocr.addWidget(self.sp_ocr_enabled)
        row_ocr.addStretch()
        card1.add_layout(row_ocr)
        
        grid = QGridLayout()
        grid.addWidget(QLabel("OCR Parsing Engine:"), 0, 0)
        self.sp_ocr_engine = QComboBox()
        self.sp_ocr_engine.addItems(["Tesseract", "OpenCV OCR"])
        grid.addWidget(self.sp_ocr_engine, 0, 1)
        card1.add_layout(grid)
        
        layout.addWidget(card1)
        
        # Card 2: Image Preprocessing
        card2 = SettingCard("Image Preprocessing Options", "Apply mathematical filters before OCR to increase parser confidence.")
        self.sp_deskew = QCheckBox("Deskew / Auto Rotate skewed pages")
        self.sp_noise_removal = QCheckBox("Denoise / Remove speckles and grain")
        self.sp_threshold = QCheckBox("Binarization / Apply local thresholding filters")
        
        card2.add_widget(self.sp_deskew)
        card2.add_widget(self.sp_noise_removal)
        card2.add_widget(self.sp_threshold)
        layout.addWidget(card2)
        
        # Card 3: Post-processing & confidence
        card3 = SettingCard("Verification Rules", "Set threshold parameters and clean-up options.")
        self.sp_auto_detect_bank = QCheckBox("Auto-detect banking institution structures")
        self.sp_merge_narration = QCheckBox("Merge multi-line text narrates into single transaction rows")
        self.sp_remove_spaces = QCheckBox("Remove duplicate spaces from narrations")
        self.sp_detect_period = QCheckBox("Auto-detect statement billing periods")
        self.sp_date_format = QCheckBox("Determine custom date formats automatically")
        self.sp_currency = QCheckBox("Auto-detect currency symbols")
        
        card3.add_widget(self.sp_auto_detect_bank)
        card3.add_widget(self.sp_merge_narration)
        card3.add_widget(self.sp_remove_spaces)
        card3.add_widget(self.sp_detect_period)
        card3.add_widget(self.sp_date_format)
        card3.add_widget(self.sp_currency)
        
        # Confidence score
        grid3 = QHBoxLayout()
        grid3.addWidget(QLabel("Confidence Score threshold:"), stretch=1)
        self.sp_confidence = QSlider(Qt.Orientation.Horizontal)
        self.sp_confidence.setRange(0, 100)
        self.sp_confidence.setValue(85)
        self.sp_confidence_lbl = QLabel("85%")
        self.sp_confidence_lbl.setFixedWidth(40)
        self.sp_confidence.valueChanged.connect(lambda v: self.sp_confidence_lbl.setText(f"{v}%"))
        grid3.addWidget(self.sp_confidence, stretch=2)
        grid3.addWidget(self.sp_confidence_lbl)
        
        card3.add_layout(grid3)
        layout.addWidget(card3)

    def _build_export_page(self):
        _, layout = self.pages[4]
        self._add_page_header(layout, "Export Settings", "Configure default file destinations, file structures, and templates.")
        
        # Card 1: format
        card1 = SettingCard("Output File Formats", "Select default sheet template format.")
        grid = QGridLayout()
        grid.addWidget(QLabel("Primary Export Format:"), 0, 0)
        self.exp_format = QComboBox()
        self.exp_format.addItems(["Excel", "CSV", "JSON", "PDF"])
        grid.addWidget(self.exp_format, 0, 1)
        card1.add_layout(grid)
        layout.addWidget(card1)
        
        # Card 2: excel options
        card2 = SettingCard("Excel Layout Formats", "Structure styles specifically applied to spreadsheet files.")
        self.exp_freeze_header = QCheckBox("Freeze top column titles row")
        self.exp_auto_width = QCheckBox("Adjust column widths automatically to match content size")
        self.exp_bold_header = QCheckBox("Bold font headings styling")
        self.exp_alt_row_color = QCheckBox("Zebra-striping (Alternate row colors)")
        self.exp_currency = QCheckBox("Apply local currency number formats")
        self.exp_summary_sheet = QCheckBox("Include summary calculations sheet")
        
        card2.add_widget(self.exp_freeze_header)
        card2.add_widget(self.exp_auto_width)
        card2.add_widget(self.exp_bold_header)
        card2.add_widget(self.exp_alt_row_color)
        card2.add_widget(self.exp_currency)
        card2.add_widget(self.exp_summary_sheet)
        layout.addWidget(card2)
        
        # Card 3: file options
        card3 = SettingCard("Destinations & Patterns", "Naming patterns and target destination folders.")
        grid3 = QGridLayout()
        
        grid3.addWidget(QLabel("Default Filename Pattern:"), 0, 0)
        self.exp_filename = QLineEdit()
        self.exp_filename.setText("{Bank}{Month}{Year}")
        self.exp_filename_err = self._create_error_label()
        grid3.addWidget(self.exp_filename, 0, 1)
        grid3.addWidget(self.exp_filename_err, 1, 1)
        
        # Help label
        help_pattern = QLabel("Available tokens: {Bank}, {Month}, {Year}, {User}, {Day}")
        help_pattern.setStyleSheet("color: #64748B; font-size: 11px;")
        grid3.addWidget(help_pattern, 2, 1)
        
        # Save Folder
        grid3.addWidget(QLabel("Target Folder:"), 3, 0)
        self.exp_save_folder = QLineEdit()
        self.exp_save_folder_err = self._create_error_label()
        
        btn_browse = QPushButton("Browse Folder")
        btn_browse.setObjectName("SecondaryButton")
        btn_browse.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_browse.clicked.connect(self._browse_export_folder)
        
        row_folder = QHBoxLayout()
        row_folder.addWidget(self.exp_save_folder)
        row_folder.addWidget(btn_browse)
        grid3.addLayout(row_folder, 3, 1)
        grid3.addWidget(self.exp_save_folder_err, 4, 1)
        
        card3.add_layout(grid3)
        
        self.btn_open_folder = QPushButton("Open Exports Directory")
        self.btn_open_folder.setObjectName("SecondaryButton")
        self.btn_open_folder.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_open_folder.clicked.connect(self._open_export_dir)
        card3.add_widget(self.btn_open_folder)
        
        layout.addWidget(card3)

    def _build_database_page(self):
        _, layout = self.pages[5]
        self._add_page_header(layout, "Database & Cloud Synced Storage", "Configure and test MongoDB Atlas connection string.")
        
        card1 = SettingCard("MongoDB Atlas Connection", "Establish database credentials to synchronize users and statements.")
        card1.add_widget(QLabel("Connection URI:"))
        self.db_uri = QLineEdit()
        self.db_uri_err = self._create_error_label()
        card1.add_widget(self.db_uri)
        card1.add_widget(self.db_uri_err)
        
        grid = QGridLayout()
        grid.addWidget(QLabel("Target Database:"), 0, 0)
        self.db_name = QLineEdit()
        self.db_name.setText("statementforge")
        grid.addWidget(self.db_name, 0, 1)
        card1.add_layout(grid)
        
        # Status
        row_status = QHBoxLayout()
        self.btn_test_db = QPushButton("Test DB Connection")
        self.btn_test_db.setObjectName("SecondaryButton")
        self.btn_test_db.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_test_db.clicked.connect(lambda: self.test_db_clicked.emit(self.db_uri.text()))
        row_status.addWidget(self.btn_test_db)
        
        self.db_status_badge = QLabel("Disconnected")
        self.db_status_badge.setFixedSize(100, 22)
        self.db_status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.db_status_badge.setStyleSheet("background-color: #F1F5F9; color: #64748B; border-radius: 6px; font-weight: bold; font-size: 11px;")
        row_status.addWidget(self.db_status_badge)
        
        self.btn_reconnect_db = QPushButton("Reconnect DB")
        self.btn_reconnect_db.setObjectName("SecondaryButton")
        self.btn_reconnect_db.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_reconnect_db.clicked.connect(lambda: self.test_db_clicked.emit(self.db_uri.text()))
        row_status.addWidget(self.btn_reconnect_db)
        row_status.addStretch()
        
        card1.add_layout(row_status)
        layout.addWidget(card1)
        
        # Card 2: Operations
        card2 = SettingCard("Database Maintenance", "Run diagnostic actions, statistics, or trigger file-based backups.")
        
        btn_grid = QGridLayout()
        
        btn_backup = QPushButton("Backup Database")
        btn_backup.setObjectName("SecondaryButton")
        btn_backup.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_backup.clicked.connect(lambda: self.backup_db_clicked.emit(self.db_uri.text()))
        btn_grid.addWidget(btn_backup, 0, 0)
        
        btn_restore = QPushButton("Restore Database")
        btn_restore.setObjectName("SecondaryButton")
        btn_restore.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_restore.clicked.connect(lambda: self.restore_db_clicked.emit(self.db_uri.text()))
        btn_grid.addWidget(btn_restore, 0, 1)
        
        btn_export = QPushButton("Export Database Schema")
        btn_export.setObjectName("SecondaryButton")
        btn_export.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_export.clicked.connect(lambda: self.export_db_clicked.emit(self.db_uri.text()))
        btn_grid.addWidget(btn_export, 1, 0)
        
        btn_stats = QPushButton("View Statistics")
        btn_stats.setObjectName("SecondaryButton")
        btn_stats.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_stats.clicked.connect(lambda: self.view_db_stats_clicked.emit(self.db_uri.text()))
        btn_grid.addWidget(btn_stats, 1, 1)
        
        card2.add_layout(btn_grid)
        
        # Labels for counts
        self.db_stats_label = QLabel("Database stats: Not loaded.")
        self.db_stats_label.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 500;")
        card2.add_widget(self.db_stats_label)
        
        layout.addWidget(card2)

    def _build_appearance_page(self):
        _, layout = self.pages[2]
        self._add_page_header(layout, "Appearance Settings", "Select visual styles, colors, and layout densities.")
        
        # Card 1: Theme selection
        card1 = SettingCard("Visual Styles & Accent Themes", "Theme configurations applied instantly.")
        grid = QGridLayout()
        
        grid.addWidget(QLabel("Visual Theme:"), 0, 0)
        self.app_theme = QComboBox()
        self.app_theme.addItems(["Light", "Dark", "System"])
        grid.addWidget(self.app_theme, 0, 1)
        
        grid.addWidget(QLabel("Accent Branding Color:"), 1, 0)
        self.color_selector = ColorSelector()
        grid.addWidget(self.color_selector, 1, 1)
        
        grid.addWidget(QLabel("Base Font Sizing:"), 2, 0)
        self.app_font_size = QComboBox()
        self.app_font_size.addItems(["Small", "Medium", "Large"])
        grid.addWidget(self.app_font_size, 2, 1)
        
        card1.add_layout(grid)
        layout.addWidget(card1)
        
        # Card 2: Layout config
        card2 = SettingCard("Sidebar & Density Options", "Toggles for spacing, density, and animation speeds.")
        grid2 = QGridLayout()
        
        grid2.addWidget(QLabel("Left Navigation Panel:"), 0, 0)
        self.app_sidebar = QComboBox()
        self.app_sidebar.addItems(["Expanded", "Compact"])
        grid2.addWidget(self.app_sidebar, 0, 1)
        
        grid2.addWidget(QLabel("Visual Layout Spacing:"), 1, 0)
        self.app_density = QComboBox()
        self.app_density.addItems(["Comfortable", "Compact"])
        grid2.addWidget(self.app_density, 1, 1)
        
        card2.add_layout(grid2)
        
        # Animations switch
        row_anim = QHBoxLayout()
        row_anim.addWidget(QLabel("Enable Micro-Animations and Fade transitions:"))
        self.app_animations = ToggleSwitch()
        row_anim.addWidget(self.app_animations)
        row_anim.addStretch()
        card2.add_layout(row_anim)
        
        layout.addWidget(card2)

    def _build_notifications_page(self):
        _, layout = self.pages[3]
        self._add_page_header(layout, "Notification Configurations", "Subscribe to operating system visual notification alerts.")
        
        card1 = SettingCard("Desktop Event Alerts", "Check configurations to trigger desktop notifications.")
        self.nt_completed = QCheckBox("Statement parsing completed successfully")
        self.nt_export = QCheckBox("Export file spreadsheet saved successfully")
        self.nt_errors = QCheckBox("Statement parsing or connection errors encountered")
        self.nt_email = QCheckBox("Automated email dispatch reports sent successfully")
        self.nt_ai = QCheckBox("AI summaries and audit insights finished successfully")
        self.nt_updates = QCheckBox("Software updates are available for download")
        
        card1.add_widget(self.nt_completed)
        card1.add_widget(self.nt_export)
        card1.add_widget(self.nt_errors)
        card1.add_widget(self.nt_email)
        card1.add_widget(self.nt_ai)
        card1.add_widget(self.nt_updates)
        
        layout.addWidget(card1)

    def _build_security_page(self):
        _, layout = self.pages[9]
        self._add_page_header(layout, "Security Settings", "Configure encryption methods and login timeout policies.")
        
        card1 = SettingCard("Login & Auto Logouts", "Configure local caching configurations.")
        self.sec_remember = QCheckBox("Remember active login credentials on restart")
        card1.add_widget(self.sec_remember)
        
        grid = QGridLayout()
        grid.addWidget(QLabel("Auto Logout Timing:"), 0, 0)
        self.sec_logout_time = QComboBox()
        self.sec_logout_time.addItems(["15 minutes", "30 minutes", "1 hour", "Never"])
        grid.addWidget(self.sec_logout_time, 0, 1)
        card1.add_layout(grid)
        layout.addWidget(card1)
        
        # Actions
        card2 = SettingCard("Encryption & Authentication sessions", "Security configurations and clearing cached tokens.")
        
        grid2 = QGridLayout()
        grid2.addWidget(QLabel("Password Encryption Standard:"), 0, 0)
        lbl_enc = QLabel("bcrypt (12 rounds salting)")
        lbl_enc.setStyleSheet("font-weight: bold; color: #64748B;")
        grid2.addWidget(lbl_enc, 0, 1)
        
        grid2.addWidget(QLabel("Active Security Session:"), 1, 0)
        self.lbl_sec_session = QLabel("Active user token verified")
        self.lbl_sec_session.setStyleSheet("color: #16A34A; font-weight: bold;")
        grid2.addWidget(self.lbl_sec_session, 1, 1)
        card2.add_layout(grid2)
        
        btn_lay = QHBoxLayout()
        btn_clear = QPushButton("Clear Saved Session Cache")
        btn_clear.setObjectName("SecondaryButton")
        btn_clear.setStyleSheet("color: #EF4444; border-color: #FCA5A5;")
        btn_clear.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_clear.clicked.connect(self.clear_session_clicked.emit)
        btn_lay.addWidget(btn_clear)
        
        btn_reset = QPushButton("Reset Authentication settings")
        btn_reset.setObjectName("SecondaryButton")
        btn_reset.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_reset.clicked.connect(self.reset_auth_clicked.emit)
        btn_lay.addWidget(btn_reset)
        
        card2.add_layout(btn_lay)
        layout.addWidget(card2)

    def _build_logs_page(self):
        _, layout = self.pages[10]
        self._add_page_header(layout, "Logs & Parser History", "Browse activity logs and system processes debug outputs.")
        
        card1 = SettingCard("System Activity Logs", "Debug operations and file parsing logs.")
        
        # Search and filters
        row_filter = QHBoxLayout()
        row_filter.addWidget(QLabel("Search Logs:"))
        self.logs_search = QLineEdit()
        self.logs_search.setPlaceholderText("Filter lines by keyword...")
        row_filter.addWidget(self.logs_search)
        
        row_filter.addWidget(QLabel("Level:"))
        self.logs_filter = QComboBox()
        self.logs_filter.addItems(["All Logs", "Informational", "Errors Only", "Parsings Only"])
        row_filter.addWidget(self.logs_filter)
        card1.add_layout(row_filter)
        
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setFixedHeight(220)
        self.logs_text.setFont(QFont("Consolas", 10) if hasattr(self, "setFont") else None)
        self.logs_text.setText(
            "[INFO] 2026-07-11 10:30:15 - StatementForge Engine initialized.\n"
            "[INFO] 2026-07-11 10:30:16 - Successfully loaded local configuration schemas.\n"
            "[INFO] 2026-07-11 10:31:05 - Connection to MongoDB Atlas established.\n"
            "[INFO] 2026-07-11 10:31:06 - Collection users successfully indexed.\n"
            "[INFO] 2026-07-11 10:32:44 - User session loaded: xyz@gmail.com.\n"
            "[INFO] 2026-07-11 10:33:02 - Initializing PDF OCR parser backend...\n"
            "[WARN] 2026-07-11 10:33:03 - Tesseract executable path not found in registry. Using fallback OCR.\n"
        )
        card1.add_widget(self.logs_text)
        
        row_btns = QHBoxLayout()
        btn_export = QPushButton("Export Logs to File")
        btn_export.setObjectName("SecondaryButton")
        btn_export.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        row_btns.addWidget(btn_export)
        
        btn_clear = QPushButton("Clear logs history")
        btn_clear.setObjectName("SecondaryButton")
        btn_clear.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_clear.clicked.connect(lambda: self.logs_text.setText(""))
        row_btns.addWidget(btn_clear)
        row_btns.addStretch()
        
        card1.add_layout(row_btns)
        layout.addWidget(card1)

    def _build_about_page(self):
        _, layout = self.pages[4]
        self._add_page_header(layout, "About StatementForge", "About the licensing and technologies of StatementForge.")
        
        card1 = SettingCard("Application Profile", "Application specifications.")
        
        # Logo + text horizontal
        row_logo = QHBoxLayout()
        logo_lbl = QLabel()
        logo_lbl.setFixedSize(64, 64)
        pix = QPixmap("assets/logo.png")
        if not pix.isNull():
            logo_lbl.setPixmap(pix.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        row_logo.addWidget(logo_lbl)
        
        text_lay = QVBoxLayout()
        title = QLabel("StatementForge Desktop Hub")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        title.setObjectName("AboutTitle")
        version = QLabel("Version 1.0 (Enterprise Build)")
        version.setStyleSheet("font-weight: 500;")
        version.setObjectName("AboutVersion")
        text_lay.addWidget(title)
        text_lay.addWidget(version)
        row_logo.addLayout(text_lay, stretch=1)
        card1.add_layout(row_logo)
        
        # Stack info
        grid = QGridLayout()
        grid.addWidget(QLabel("Technology Stack:"), 0, 0)
        grid.addWidget(QLabel("Python 3.12, PyQt6, MongoDB Atlas, Google Gemini, OpenCV, Tesseract OCR"), 0, 1)
        
        grid.addWidget(QLabel("License Standard:"), 1, 0)
        grid.addWidget(QLabel("Educational Use License (Premium Sandbox)"), 1, 1)
        
        card1.add_layout(grid)
        layout.addWidget(card1)

    # --- Sizing / Page Header Helper ---
    
    def _add_page_header(self, layout, title, subtitle):
        """Adds a unified header label with subtitle matching standard dashboard greets."""
        header_lay = QVBoxLayout()
        header_lay.setSpacing(4)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 22px; font-weight: 800;")
        lbl_title.setObjectName("SettingsPageTitle")
        
        lbl_sub = QLabel(subtitle)
        lbl_sub.setStyleSheet("font-size: 13px; font-weight: 500;")
        lbl_sub.setObjectName("SettingsPageSubtitle")
        
        header_lay.addWidget(lbl_title)
        header_lay.addWidget(lbl_sub)
        
        # Add spacing below header
        header_lay.addItem(QSpacerItem(20, 16, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        layout.addLayout(header_lay)

    def _create_error_label(self):
        """Helper to create error messages with fixed height to prevent layout shifts."""
        err = QLabel(" ")
        err.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 500;")
        err.setFixedHeight(16)
        return err

    # ----------------------------------------------------
    # BROWSE ACTIONS
    # ----------------------------------------------------
    
    def _browse_save_location(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.gen_save_location.text())
        if dir_path:
            self.gen_save_location.setText(dir_path)

    def _browse_export_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Export Directory", self.exp_save_folder.text())
        if dir_path:
            self.exp_save_folder.setText(dir_path)

    def _open_export_dir(self):
        folder = self.exp_save_folder.text().strip()
        if os.path.exists(folder):
            os.startfile(folder) if os.name == 'nt' else os.system(f"open {folder}")

    # ----------------------------------------------------
    # BUTTON TRIGGER HELPERS
    # ----------------------------------------------------
    
    def _trigger_change_password(self):
        old_pwd = self.acc_old_pwd.text()
        new_pwd = self.acc_new_pwd.text()
        self.change_password_clicked.emit(old_pwd, new_pwd)

    def _trigger_email_test(self):
        self.test_email_clicked.emit(
            self.email_smtp.text(),
            self.email_port.text(),
            self.email_sender.text(),
            self.email_password_field.text()
        )

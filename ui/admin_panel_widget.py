from ui.html_screen_wrapper import HtmlScreenWrapper

class AdminPanelWidget(HtmlScreenWrapper):
    """
    PyQt6 container widget hosting the Admin Panel HTML interface ('web/admin_panel.html').
    Interacts with Python via QWebChannel WebBridge.
    """
    def __init__(self, parent=None):
        super().__init__("web/admin_panel.html", parent=parent)

    def reload_data(self):
        """Triggers a data refresh inside the webview."""
        self.eval_js("if (typeof initAdminPanel === 'function') initAdminPanel();")

    def switch_tab(self, tab_name):
        """Switches active sub-tab inside Admin Panel ('users', 'statements', 'logs')."""
        self.eval_js(f"if (typeof switchTab === 'function') switchTab('{tab_name}');")

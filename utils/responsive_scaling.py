import re
import PyQt6.QtWidgets as QtWidgets
from PyQt6.QtCore import QObject, QEvent, Qt, QSize, QMargins
from PyQt6.QtGui import QFont, QPixmap

# --- Original Qt Methods ---
_original_set_stylesheet = QtWidgets.QWidget.setStyleSheet
_original_app_set_stylesheet = QtWidgets.QApplication.setStyleSheet
_original_set_font = QtWidgets.QWidget.setFont
_original_app_set_font = QtWidgets.QApplication.setFont

_original_set_fixed_size = QtWidgets.QWidget.setFixedSize
_original_set_fixed_width = QtWidgets.QWidget.setFixedWidth
_original_set_fixed_height = QtWidgets.QWidget.setFixedHeight

_original_set_minimum_size = QtWidgets.QWidget.setMinimumSize
_original_set_minimum_width = QtWidgets.QWidget.setMinimumWidth
_original_set_minimum_height = QtWidgets.QWidget.setMinimumHeight

_original_set_maximum_size = QtWidgets.QWidget.setMaximumSize
_original_set_maximum_width = QtWidgets.QWidget.setMaximumWidth
_original_set_maximum_height = QtWidgets.QWidget.setMaximumHeight

_original_layout_set_spacing = QtWidgets.QLayout.setSpacing
_original_layout_set_contents_margins = QtWidgets.QLayout.setContentsMargins

_original_set_icon_size = QtWidgets.QAbstractButton.setIconSize
_original_tab_set_icon_size = QtWidgets.QTabWidget.setIconSize

_original_set_column_width = QtWidgets.QTableView.setColumnWidth
_original_set_default_section_size = QtWidgets.QHeaderView.setDefaultSectionSize

_original_set_pixmap = QtWidgets.QLabel.setPixmap

# Flag to prevent infinite recursion during batch updates
_in_zoom_update = False

# --- Helpers ---

def scale_qss(qss_content, factor):
    if not qss_content:
        return qss_content
        
    def replace_px(match):
        value = float(match.group(1))
        # Do not scale 0px or 1px (often used for border widths to prevent disappearing lines)
        if abs(value) <= 1.0:
            return match.group(0)
        scaled_value = round(value * factor)
        return f"{scaled_value}px"
        
    # Match integer or decimal values immediately followed by "px"
    pattern = r'\b(-?\d+(?:\.\d+)?)px\b'
    return re.sub(pattern, replace_px, qss_content)

def scale_dim(val, factor):
    if val is None:
        return None
    # Do not scale default extreme/max/min sizes in Qt (typically >= 100000 or <= -100000)
    if val >= 100000 or val <= -100000:
        return val
    scaled = int(val * factor)
    # Clamp to signed 32-bit integer range
    return max(-2147483648, min(2147483647, scaled))

def scale_qsize(qsize, factor):
    if qsize is None:
        return None
    w = scale_dim(qsize.width(), factor)
    h = scale_dim(qsize.height(), factor)
    return QSize(max(1, w) if w is not None else 1, max(1, h) if h is not None else 1)

# --- Monkey-Patched QWidget/QApplication Setters ---

def new_set_stylesheet(self, sheet):
    self._original_style_sheet = sheet
    if _in_zoom_update:
        _original_set_stylesheet(self, sheet)
        return
    app = QtWidgets.QApplication.instance()
    zoom_factor = getattr(app, 'zoom_factor', 1.0)
    window_scale = getattr(app, 'window_scale', 1.0)
    effective_zoom = zoom_factor * window_scale
    scaled_sheet = scale_qss(sheet, effective_zoom)
    _original_set_stylesheet(self, scaled_sheet)

def new_app_set_stylesheet(self, sheet):
    self._original_style_sheet = sheet
    if _in_zoom_update:
        _original_app_set_stylesheet(self, sheet)
        return
    zoom_factor = getattr(self, 'zoom_factor', 1.0)
    window_scale = getattr(self, 'window_scale', 1.0)
    effective_zoom = zoom_factor * window_scale
    scaled_sheet = scale_qss(sheet, effective_zoom)
    _original_app_set_stylesheet(self, scaled_sheet)

def new_set_font(self, font):
    self._original_font = QFont(font)
    if not hasattr(self, '_original_font_point_size'):
        self._original_font_point_size = font.pointSize()
        if self._original_font_point_size <= 0:
            self._original_font_point_size = font.pixelSize()
            self._is_pixel_font = True
        else:
            self._is_pixel_font = False
            
    if _in_zoom_update:
        _original_set_font(self, font)
        return
        
    app = QtWidgets.QApplication.instance()
    zoom_factor = getattr(app, 'zoom_factor', 1.0)
    window_scale = getattr(app, 'window_scale', 1.0)
    effective_zoom = zoom_factor * window_scale
    scaled_font = QFont(font)
    if getattr(self, '_is_pixel_font', False):
        scaled_font.setPixelSize(max(1, int(self._original_font_point_size * effective_zoom)))
    else:
        scaled_font.setPointSize(max(1, int(self._original_font_point_size * effective_zoom)))
    _original_set_font(self, scaled_font)

def new_app_set_font(self, font):
    self._original_font = QFont(font)
    if _in_zoom_update:
        _original_app_set_font(font)
        return
    zoom_factor = getattr(self, 'zoom_factor', 1.0)
    window_scale = getattr(self, 'window_scale', 1.0)
    effective_zoom = zoom_factor * window_scale
    scaled_font = QFont(font)
    scaled_font.setPointSize(max(1, int(font.pointSize() * effective_zoom)))
    _original_app_set_font(scaled_font)

# --- Monkey-Patched Size Constraint Setters ---

def new_set_fixed_size(self, *args):
    if len(args) == 1:
        size = args[0]
        if isinstance(size, QSize):
            self._original_fixed_size = QSize(size)
        else:
            self._original_fixed_size = None
    elif len(args) == 2:
        self._original_fixed_size = QSize(args[0], args[1])
    else:
        self._original_fixed_size = None
        
    if _in_zoom_update:
        _original_set_fixed_size(self, *args)
        return
        
    app = QtWidgets.QApplication.instance()
    zoom_factor = getattr(app, 'zoom_factor', 1.0)
    window_scale = getattr(app, 'window_scale', 1.0)
    effective_zoom = zoom_factor * window_scale
    if self._original_fixed_size:
        scaled = scale_qsize(self._original_fixed_size, effective_zoom)
        _original_set_fixed_size(self, scaled)
    else:
        _original_set_fixed_size(self, *args)

def new_set_fixed_width(self, width):
    self._original_fixed_width = width
    if _in_zoom_update:
        _original_set_fixed_width(self, width)
        return
    app = QtWidgets.QApplication.instance()
    zoom_factor = getattr(app, 'zoom_factor', 1.0)
    window_scale = getattr(app, 'window_scale', 1.0)
    effective_zoom = zoom_factor * window_scale
    _original_set_fixed_width(self, int(width * effective_zoom))

def new_set_fixed_height(self, height):
    self._original_fixed_height = height
    if _in_zoom_update:
        _original_set_fixed_height(self, height)
        return
    app = QtWidgets.QApplication.instance()
    zoom_factor = getattr(app, 'zoom_factor', 1.0)
    window_scale = getattr(app, 'window_scale', 1.0)
    effective_zoom = zoom_factor * window_scale
    _original_set_fixed_height(self, int(height * effective_zoom))

def new_set_minimum_size(self, *args):
    if len(args) == 1:
        size = args[0]
        if isinstance(size, QSize):
            self._original_minimum_size = QSize(size)
        else:
            self._original_minimum_size = None
    elif len(args) == 2:
        self._original_minimum_size = QSize(args[0], args[1])
    else:
        self._original_minimum_size = None
        
    if _in_zoom_update:
        _original_set_minimum_size(self, *args)
        return
        
    app = QtWidgets.QApplication.instance()
    zoom_factor = getattr(app, 'zoom_factor', 1.0)
    window_scale = getattr(app, 'window_scale', 1.0)
    effective_zoom = zoom_factor * window_scale
    if self._original_minimum_size:
        scaled = scale_qsize(self._original_minimum_size, effective_zoom)
        _original_set_minimum_size(self, scaled)
    else:
        _original_set_minimum_size(self, *args)

def new_set_minimum_width(self, width):
    self._original_minimum_width = width
    if _in_zoom_update:
        _original_set_minimum_width(self, width)
        return
    app = QtWidgets.QApplication.instance()
    zoom_factor = getattr(app, 'zoom_factor', 1.0)
    window_scale = getattr(app, 'window_scale', 1.0)
    effective_zoom = zoom_factor * window_scale
    _original_set_minimum_width(self, int(width * effective_zoom))

def new_set_minimum_height(self, height):
    self._original_minimum_height = height
    if _in_zoom_update:
        _original_set_minimum_height(self, height)
        return
    app = QtWidgets.QApplication.instance()
    zoom_factor = getattr(app, 'zoom_factor', 1.0)
    window_scale = getattr(app, 'window_scale', 1.0)
    effective_zoom = zoom_factor * window_scale
    _original_set_minimum_height(self, int(height * effective_zoom))

def new_set_maximum_size(self, *args):
    is_default = False
    if len(args) == 1:
        size = args[0]
        if isinstance(size, QSize):
            if size.width() >= 16777215 and size.height() >= 16777215:
                is_default = True
            self._original_maximum_size = QSize(size)
        else:
            self._original_maximum_size = None
    elif len(args) == 2:
        if args[0] >= 16777215 and args[1] >= 16777215:
            is_default = True
        self._original_maximum_size = QSize(args[0], args[1])
    else:
        self._original_maximum_size = None
        
    if is_default:
        self._original_maximum_size = None
        
    if _in_zoom_update:
        _original_set_maximum_size(self, *args)
        return
        
    app = QtWidgets.QApplication.instance()
    zoom_factor = getattr(app, 'zoom_factor', 1.0)
    window_scale = getattr(app, 'window_scale', 1.0)
    effective_zoom = zoom_factor * window_scale
    if self._original_maximum_size:
        scaled = scale_qsize(self._original_maximum_size, effective_zoom)
        _original_set_maximum_size(self, scaled)
    else:
        _original_set_maximum_size(self, *args)

def new_set_maximum_width(self, width):
    if width >= 16777215:
        self._original_maximum_width = None
    else:
        self._original_maximum_width = width
        
    if _in_zoom_update:
        _original_set_maximum_width(self, width)
        return
    app = QtWidgets.QApplication.instance()
    zoom_factor = getattr(app, 'zoom_factor', 1.0)
    window_scale = getattr(app, 'window_scale', 1.0)
    effective_zoom = zoom_factor * window_scale
    if self._original_maximum_width is not None:
        _original_set_maximum_width(self, int(width * effective_zoom))
    else:
        _original_set_maximum_width(self, width)

def new_set_maximum_height(self, height):
    if height >= 16777215:
        self._original_maximum_height = None
    else:
        self._original_maximum_height = height
        
    if _in_zoom_update:
        _original_set_maximum_height(self, height)
        return
    app = QtWidgets.QApplication.instance()
    zoom_factor = getattr(app, 'zoom_factor', 1.0)
    window_scale = getattr(app, 'window_scale', 1.0)
    effective_zoom = zoom_factor * window_scale
    if self._original_maximum_height is not None:
        _original_set_maximum_height(self, int(height * effective_zoom))
    else:
        _original_set_maximum_height(self, height)

# --- Monkey-Patched QLayout Setters ---

def new_layout_set_spacing(self, spacing):
    self._original_spacing = spacing
    if _in_zoom_update:
        _original_layout_set_spacing(self, spacing)
        return
    app = QtWidgets.QApplication.instance()
    zoom_factor = getattr(app, 'zoom_factor', 1.0)
    window_scale = getattr(app, 'window_scale', 1.0)
    effective_zoom = zoom_factor * window_scale
    _original_layout_set_spacing(self, int(spacing * effective_zoom))

def new_layout_set_contents_margins(self, *args):
    if len(args) == 1:
        margins = args[0]
        if isinstance(margins, QMargins):
            self._original_margins = (margins.left(), margins.top(), margins.right(), margins.bottom())
        else:
            self._original_margins = None
    elif len(args) == 4:
        self._original_margins = args
    else:
        self._original_margins = None
        
    if _in_zoom_update:
        _original_layout_set_contents_margins(self, *args)
        return
        
    app = QtWidgets.QApplication.instance()
    zoom_factor = getattr(app, 'zoom_factor', 1.0)
    window_scale = getattr(app, 'window_scale', 1.0)
    effective_zoom = zoom_factor * window_scale
    if self._original_margins:
        l, t, r, b = self._original_margins
        _original_layout_set_contents_margins(self, int(l * effective_zoom), int(t * effective_zoom), int(r * effective_zoom), int(b * effective_zoom))
    else:
        _original_layout_set_contents_margins(self, *args)

# --- Monkey-Patched Button Icon / Table Setters ---

def new_set_icon_size(self, size):
    self._original_icon_size = QSize(size)
    if _in_zoom_update:
        _original_set_icon_size(self, size)
        return
    app = QtWidgets.QApplication.instance()
    zoom_factor = getattr(app, 'zoom_factor', 1.0)
    window_scale = getattr(app, 'window_scale', 1.0)
    effective_zoom = zoom_factor * window_scale
    _original_set_icon_size(self, scale_qsize(self._original_icon_size, effective_zoom))

def new_tab_set_icon_size(self, size):
    self._original_icon_size = QSize(size)
    if _in_zoom_update:
        _original_tab_set_icon_size(self, size)
        return
    app = QtWidgets.QApplication.instance()
    zoom_factor = getattr(app, 'zoom_factor', 1.0)
    window_scale = getattr(app, 'window_scale', 1.0)
    effective_zoom = zoom_factor * window_scale
    _original_tab_set_icon_size(self, scale_qsize(self._original_icon_size, effective_zoom))

def new_set_column_width(self, column, width):
    if not hasattr(self, '_original_column_widths'):
        self._original_column_widths = {}
    self._original_column_widths[column] = width
    if _in_zoom_update:
        _original_set_column_width(self, column, width)
        return
    app = QtWidgets.QApplication.instance()
    zoom_factor = getattr(app, 'zoom_factor', 1.0)
    window_scale = getattr(app, 'window_scale', 1.0)
    effective_zoom = zoom_factor * window_scale
    _original_set_column_width(self, column, int(width * effective_zoom))

def new_set_default_section_size(self, size):
    self._original_default_section_size = size
    if _in_zoom_update:
        _original_set_default_section_size(self, size)
        return
    app = QtWidgets.QApplication.instance()
    zoom_factor = getattr(app, 'zoom_factor', 1.0)
    window_scale = getattr(app, 'window_scale', 1.0)
    effective_zoom = zoom_factor * window_scale
    _original_set_default_section_size(self, int(size * effective_zoom))

# --- Monkey-Patched QLabel Pixmap Scaling ---

def new_set_pixmap(self, pixmap):
    self._original_pixmap = pixmap
    if _in_zoom_update:
        _original_set_pixmap(self, pixmap)
        return
        
    app = QtWidgets.QApplication.instance()
    zoom_factor = getattr(app, 'zoom_factor', 1.0)
    window_scale = getattr(app, 'window_scale', 1.0)
    effective_zoom = zoom_factor * window_scale
    
    if pixmap and not pixmap.isNull():
        orig_size = pixmap.size()
        scaled_w = max(1, int(orig_size.width() * effective_zoom))
        scaled_h = max(1, int(orig_size.height() * effective_zoom))
        scaled_pixmap = pixmap.scaled(scaled_w, scaled_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        _original_set_pixmap(self, scaled_pixmap)
    else:
        _original_set_pixmap(self, pixmap)

# --- Batch Layout & Widget Traverser ---

def update_layout_zoom(layout, zoom_factor):
    if not layout:
        return
    if hasattr(layout, '_original_spacing') and layout._original_spacing is not None:
        _original_layout_set_spacing(layout, int(layout._original_spacing * zoom_factor))
    if hasattr(layout, '_original_margins') and layout._original_margins is not None:
        l, t, r, b = layout._original_margins
        _original_layout_set_contents_margins(layout, int(l * zoom_factor), int(t * zoom_factor), int(r * zoom_factor), int(b * zoom_factor))
        
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if not item:
            continue
            
        # Scale Spacers
        spacer = item.spacerItem()
        if spacer:
            if not hasattr(spacer, '_original_size'):
                spacer._original_size = QSize(spacer.sizeHint())
                spacer._original_policies = (spacer.sizePolicy().horizontalPolicy(), spacer.sizePolicy().verticalPolicy())
            orig_size = spacer._original_size
            hp, vp = spacer._original_policies
            scaled_w = scale_dim(orig_size.width(), zoom_factor)
            scaled_h = scale_dim(orig_size.height(), zoom_factor)
            
            # Make sure we don't pass None or negative values for spacer sizes
            scaled_w = max(0, scaled_w) if scaled_w is not None else 0
            scaled_h = max(0, scaled_h) if scaled_h is not None else 0
            
            spacer.changeSize(scaled_w, scaled_h, hp, vp)
            
        sub_layout = item.layout()
        if sub_layout:
            update_layout_zoom(sub_layout, zoom_factor)
            
    layout.invalidate()

def update_all_widgets_zoom(effective_zoom=None):
    if effective_zoom is None:
        app = QtWidgets.QApplication.instance()
        zoom_factor = getattr(app, 'zoom_factor', 1.0)
        window_scale = getattr(app, 'window_scale', 1.0)
        effective_zoom = zoom_factor * window_scale
        
    global _in_zoom_update
    _in_zoom_update = True
    try:
        app = QtWidgets.QApplication.instance()
        
        # 1. Update Application Global Stylesheet
        if hasattr(app, '_original_style_sheet') and app._original_style_sheet:
            _original_app_set_stylesheet(app, scale_qss(app._original_style_sheet, effective_zoom))
            
        # 2. Update Application Default Font
        if hasattr(app, '_original_font'):
            scaled_font = QFont(app._original_font)
            scaled_font.setPointSize(max(1, int(app._original_font.pointSize() * effective_zoom)))
            _original_app_set_font(scaled_font)
            
        # 3. Update all instanced widgets
        for widget in app.allWidgets():
            # Stylesheet
            if hasattr(widget, '_original_style_sheet') and widget._original_style_sheet:
                scaled_sheet = scale_qss(widget._original_style_sheet, effective_zoom)
                _original_set_stylesheet(widget, scaled_sheet)
                
            # Font
            if hasattr(widget, '_original_font'):
                scaled_font = QFont(widget._original_font)
                if getattr(widget, '_is_pixel_font', False):
                    scaled_font.setPixelSize(max(1, int(widget._original_font_point_size * effective_zoom)))
                else:
                    scaled_font.setPointSize(max(1, int(widget._original_font_point_size * effective_zoom)))
                _original_set_font(widget, scaled_font)
                
            # Fixed size constraints
            if hasattr(widget, '_original_fixed_size') and widget._original_fixed_size:
                _original_set_fixed_size(widget, scale_qsize(widget._original_fixed_size, effective_zoom))
            if hasattr(widget, '_original_fixed_width') and widget._original_fixed_width is not None:
                _original_set_fixed_width(widget, int(widget._original_fixed_width * effective_zoom))
            if hasattr(widget, '_original_fixed_height') and widget._original_fixed_height is not None:
                _original_set_fixed_height(widget, int(widget._original_fixed_height * effective_zoom))
                
            # Minimum size constraints
            if hasattr(widget, '_original_minimum_size') and widget._original_minimum_size:
                _original_set_minimum_size(widget, scale_qsize(widget._original_minimum_size, effective_zoom))
            if hasattr(widget, '_original_minimum_width') and widget._original_minimum_width is not None:
                _original_set_minimum_width(widget, int(widget._original_minimum_width * effective_zoom))
            if hasattr(widget, '_original_minimum_height') and widget._original_minimum_height is not None:
                _original_set_minimum_height(widget, int(widget._original_minimum_height * effective_zoom))
                
            # Maximum size constraints
            if hasattr(widget, '_original_maximum_size') and widget._original_maximum_size:
                _original_set_maximum_size(widget, scale_qsize(widget._original_maximum_size, effective_zoom))
            if hasattr(widget, '_original_maximum_width') and widget._original_maximum_width is not None:
                _original_set_maximum_width(widget, int(widget._original_maximum_width * effective_zoom))
            if hasattr(widget, '_original_maximum_height') and widget._original_maximum_height is not None:
                _original_set_maximum_height(widget, int(widget._original_maximum_height * effective_zoom))
                
            # Layout margins and spaces
            layout = QtWidgets.QWidget.layout(widget)
            if layout:
                update_layout_zoom(layout, effective_zoom)
                
            # Button Icon sizes
            if isinstance(widget, QtWidgets.QAbstractButton) and hasattr(widget, '_original_icon_size') and widget._original_icon_size:
                _original_set_icon_size(widget, scale_qsize(widget._original_icon_size, effective_zoom))
                
            # Tab widget Icon sizes
            if isinstance(widget, QtWidgets.QTabWidget) and hasattr(widget, '_original_icon_size') and widget._original_icon_size:
                _original_tab_set_icon_size(widget, scale_qsize(widget._original_icon_size, effective_zoom))
                
            # Table column widths
            if isinstance(widget, QtWidgets.QTableView):
                if hasattr(widget, '_original_column_widths'):
                    for col, w in widget._original_column_widths.items():
                        _original_set_column_width(widget, col, int(w * effective_zoom))
            if isinstance(widget, QtWidgets.QHeaderView):
                if hasattr(widget, '_original_default_section_size'):
                    _original_set_default_section_size(widget, int(widget._original_default_section_size * effective_zoom))
                    
            # QLabel Pixmaps
            if isinstance(widget, QtWidgets.QLabel):
                if hasattr(widget, '_original_pixmap') and widget._original_pixmap and not widget._original_pixmap.isNull():
                    orig_pixmap = widget._original_pixmap
                    scaled_w = max(1, int(orig_pixmap.width() * effective_zoom))
                    scaled_h = max(1, int(orig_pixmap.height() * effective_zoom))
                    scaled_pixmap = orig_pixmap.scaled(scaled_w, scaled_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    _original_set_pixmap(widget, scaled_pixmap)
                    
            # Force trigger update/repaint of current custom painted switches and buttons
            widget.update()
    finally:
        _in_zoom_update = False

# --- Global Zoom & Resize Event Filter ---

class GlobalZoomFilter(QObject):
    def eventFilter(self, obj, event):
        # 1. Capture Ctrl+, Ctrl-, Ctrl+0 Key combinations
        if event.type() == QEvent.Type.KeyPress:
            key_event = event
            if key_event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                if key_event.key() in (Qt.Key.Key_Equal, Qt.Key.Key_Plus):
                    self.change_zoom(0.1)
                    return True
                elif key_event.key() == Qt.Key.Key_Minus:
                    self.change_zoom(-0.1)
                    return True
                elif key_event.key() == Qt.Key.Key_0:
                    self.reset_zoom()
                    return True
                    
        # 2. Capture Ctrl + Mouse Wheel zoom
        elif event.type() == QEvent.Type.Wheel:
            wheel_event = event
            if wheel_event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                delta = wheel_event.angleDelta().y()
                if delta > 0:
                    self.change_zoom(0.05)
                elif delta < 0:
                    self.change_zoom(-0.05)
                return True
                
        # 3. Capture Main Window resize to implement Fluid Font and Layout Scaling
        elif event.type() == QEvent.Type.Resize and isinstance(obj, QtWidgets.QMainWindow):
            w = obj.width()
            h = obj.height()
            
            # Base reference design size (1440x900)
            ref_w, ref_h = 1440, 900
            
            # Smooth scale factor (average of width and height scale ratios)
            scale = (w / ref_w + h / ref_h) / 2.0
            # Keep scale bounds comfortable (e.g. 0.85x min to 1.8x max) to prevent tiny fonts
            scale = max(0.85, min(1.8, scale))
            
            app = QtWidgets.QApplication.instance()
            app.window_scale = scale
            self.apply_combined_zoom()
            
        return super().eventFilter(obj, event)

    def change_zoom(self, delta):
        app = QtWidgets.QApplication.instance()
        current_zoom = getattr(app, 'zoom_factor', 1.0)
        new_zoom = max(0.5, min(3.0, current_zoom + delta))
        if new_zoom != current_zoom:
            app.zoom_factor = new_zoom
            self.apply_combined_zoom()

    def reset_zoom(self):
        app = QtWidgets.QApplication.instance()
        if getattr(app, 'zoom_factor', 1.0) != 1.0:
            app.zoom_factor = 1.0
            self.apply_combined_zoom()

    def apply_combined_zoom(self):
        app = QtWidgets.QApplication.instance()
        zoom_factor = getattr(app, 'zoom_factor', 1.0)
        window_scale = getattr(app, 'window_scale', 1.0)
        
        effective_zoom = zoom_factor * window_scale
        
        # Debounce/prevent unnecessary updates if scale difference is extremely small
        last_applied = getattr(app, 'last_applied_effective_zoom', 1.0)
        if abs(effective_zoom - last_applied) > 0.02:
            app.last_applied_effective_zoom = effective_zoom
            update_all_widgets_zoom(effective_zoom)

# --- Initialization Entry Point ---

def apply_responsive_patches(app):
    """Hooks QWidget, QLayout, and widget subclasses to allow responsive layout & dynamic scale scaling."""
    # Apply monkey patches to Qt prototype classes
    QtWidgets.QWidget.setStyleSheet = new_set_stylesheet
    QtWidgets.QApplication.setStyleSheet = new_app_set_stylesheet
    
    QtWidgets.QWidget.setFont = new_set_font
    QtWidgets.QApplication.setFont = new_app_set_font
    
    QtWidgets.QWidget.setFixedSize = new_set_fixed_size
    QtWidgets.QWidget.setFixedWidth = new_set_fixed_width
    QtWidgets.QWidget.setFixedHeight = new_set_fixed_height
    
    QtWidgets.QWidget.setMinimumSize = new_set_minimum_size
    QtWidgets.QWidget.setMinimumWidth = new_set_minimum_width
    QtWidgets.QWidget.setMinimumHeight = new_set_minimum_height
    
    QtWidgets.QWidget.setMaximumSize = new_set_maximum_size
    QtWidgets.QWidget.setMaximumWidth = new_set_maximum_width
    QtWidgets.QWidget.setMaximumHeight = new_set_maximum_height
    
    QtWidgets.QLayout.setSpacing = new_layout_set_spacing
    QtWidgets.QLayout.setContentsMargins = new_layout_set_contents_margins
    
    QtWidgets.QAbstractButton.setIconSize = new_set_icon_size
    QtWidgets.QTabWidget.setIconSize = new_tab_set_icon_size
    
    QtWidgets.QTableView.setColumnWidth = new_set_column_width
    QtWidgets.QHeaderView.setDefaultSectionSize = new_set_default_section_size
    
    QtWidgets.QLabel.setPixmap = new_set_pixmap

    # Initialize scale parameters on application instance
    app.zoom_factor = 1.0
    app.window_scale = 1.0
    app.last_applied_effective_zoom = 1.0

    # Install the global keyboard, mouse, and resize filter
    zoom_filter = GlobalZoomFilter(app)
    app.installEventFilter(zoom_filter)
    app.zoom_filter_ref = zoom_filter # Keep strong reference to prevent garbage collection

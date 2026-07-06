import os
from PyQt6.QtGui import QImage, QPainter, QColor, QPen, QBrush, QFont, QLinearGradient
from PyQt6.QtCore import Qt, QPointF, QRectF

def ensure_directories():
    """Ensure assets directory structure exists."""
    for path in ["assets", "assets/icons", "assets/images"]:
        os.makedirs(path, exist_ok=True)

def generate_assets():
    """Generates all necessary icons and logo assets if they do not exist."""
    ensure_directories()
    
    # Generate Logo
    logo_path = "assets/logo.png"
    if not os.path.exists(logo_path):
        create_logo(logo_path)
        
    # List of icons to generate: (name, draw_func)
    icons = {
        "dashboard": draw_dashboard_icon,
        "upload": draw_upload_icon,
        "history": draw_history_icon,
        "reports": draw_reports_icon,
        "settings": draw_settings_icon,
        "logout": draw_logout_icon,
        "excel": draw_excel_icon,
        "ai": draw_ai_icon,
        "gst": draw_gst_icon,
        "tally": draw_tally_icon,
        "search": draw_search_icon,
        "bell": draw_bell_icon,
        "profile": draw_profile_icon,
        "duplicate": draw_duplicate_icon,
        "email": draw_email_icon
    }
    
    for name, func in icons.items():
        icon_path = f"assets/icons/{name}.png"
        if not os.path.exists(icon_path):
            create_icon(icon_path, func)

def create_logo(path):
    """Draws a premium high-res logo with gradient background and abstract geometric 'SF' structure."""
    img = QImage(512, 512, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Draw rounded gradient container
    gradient = QLinearGradient(0, 0, 512, 512)
    gradient.setColorAt(0.0, QColor("#2563EB"))  # Primary Blue
    gradient.setColorAt(1.0, QColor("#1D4ED8"))  # Darker Blue
    
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(gradient))
    painter.drawRoundedRect(QRectF(16, 16, 480, 480), 96, 96)
    
    # Draw Shield/Vault outline
    painter.setPen(QPen(QColor("#FFFFFF"), 16, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    
    # Stylized S & F interlocking curves
    # S curve
    painter.drawArc(QRectF(140, 120, 232, 120), 0 * 16, 180 * 16)
    painter.drawArc(QRectF(140, 220, 232, 120), 180 * 16, 180 * 16)
    # F horizontal bar
    painter.drawLine(140, 180, 372, 180)
    painter.drawLine(140, 280, 320, 280)
    
    # Add a glowing trend line going up-right representing finance/growth
    painter.setPen(QPen(QColor("#38BDF8"), 20, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    points = [
        QPointF(100, 380),
        QPointF(200, 360),
        QPointF(300, 260),
        QPointF(420, 180)
    ]
    for i in range(len(points) - 1):
        painter.drawLine(points[i], points[i+1])
        
    # Draw arrow head for the growth line
    painter.setBrush(QBrush(QColor("#38BDF8")))
    painter.setPen(Qt.PenStyle.NoPen)
    arrow = [
        QPointF(420, 180),
        QPointF(390, 210),
        QPointF(430, 220)
    ]
    painter.drawPolygon(arrow)
    
    painter.end()
    img.save(path)

def create_icon(path, draw_func):
    """Draws a 64x64 icon on transparent canvas using the specified draw function."""
    img = QImage(64, 64, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Establish a default theme color palette for icons
    primary_color = QColor("#2563EB")
    accent_color = QColor("#3B82F6")
    gray_color = QColor("#64748B")
    
    draw_func(painter, primary_color, accent_color, gray_color)
    
    painter.end()
    img.save(path)

# Custom Icon Drawing Functions (64x64 canvas)

def draw_dashboard_icon(painter, primary, accent, gray):
    # Modern grid of 4 squares, offset/sleek
    painter.setPen(Qt.PenStyle.NoPen)
    
    # Top-Left (primary)
    painter.setBrush(QBrush(primary))
    painter.drawRoundedRect(QRectF(8, 8, 20, 20), 4, 4)
    
    # Top-Right (accent)
    painter.setBrush(QBrush(accent))
    painter.drawRoundedRect(QRectF(36, 8, 20, 20), 4, 4)
    
    # Bottom-Left (gray)
    painter.setBrush(QBrush(gray))
    painter.drawRoundedRect(QRectF(8, 36, 20, 20), 4, 4)
    
    # Bottom-Right (primary)
    painter.setBrush(QBrush(primary))
    painter.drawRoundedRect(QRectF(36, 36, 20, 20), 4, 4)

def draw_upload_icon(painter, primary, accent, gray):
    # Upload arrow pointing up from container
    painter.setPen(QPen(primary, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    
    # Draw container / bottom bracket
    painter.drawLine(8, 48, 56, 48)
    painter.drawLine(8, 40, 8, 48)
    painter.drawLine(56, 40, 56, 48)
    
    # Draw Up Arrow
    painter.drawLine(32, 12, 32, 40)
    painter.drawLine(20, 24, 32, 12)
    painter.drawLine(44, 24, 32, 12)

def draw_history_icon(painter, primary, accent, gray):
    # Clockwise circular arrow
    painter.setPen(QPen(primary, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    
    # Clock circle (open arc for arrow head)
    painter.drawArc(QRectF(10, 10, 44, 44), 60 * 16, 270 * 16)
    
    # Arrow head
    painter.setBrush(QBrush(primary))
    painter.setPen(Qt.PenStyle.NoPen)
    arrow = [
        QPointF(42, 28),
        QPointF(54, 22),
        QPointF(46, 12)
    ]
    painter.drawPolygon(arrow)
    
    # Clock hands
    painter.setPen(QPen(gray, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(32, 32, 32, 20)
    painter.drawLine(32, 32, 44, 32)

def draw_reports_icon(painter, primary, accent, gray):
    # Document with charts or lines
    painter.setPen(QPen(primary, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    
    # Document border
    painter.drawRoundedRect(QRectF(12, 6, 40, 52), 6, 6)
    
    # Lines
    painter.setPen(QPen(gray, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(20, 20, 44, 20)
    painter.drawLine(20, 30, 44, 30)
    painter.drawLine(20, 40, 36, 40)

def draw_settings_icon(painter, primary, accent, gray):
    # Settings Gear
    painter.setPen(QPen(primary, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    
    # Inner circle
    painter.drawEllipse(QRectF(22, 22, 20, 20))
    
    # Gear teeth
    # Draw a outer circular boundary and draw teeth radiating outward
    center_x, center_y = 32, 32
    import math
    for i in range(8):
        angle = i * (2 * math.pi / 8)
        x1 = center_x + 13 * math.cos(angle)
        y1 = center_y + 13 * math.sin(angle)
        x2 = center_x + 19 * math.cos(angle)
        y2 = center_y + 19 * math.sin(angle)
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

def draw_logout_icon(painter, primary, accent, gray):
    # Door and arrow pointing out
    painter.setPen(QPen(gray, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    
    # Door bracket
    painter.drawLine(24, 10, 8, 10)
    painter.drawLine(8, 10, 8, 54)
    painter.drawLine(8, 54, 24, 54)
    
    # Logout arrow pointing right
    painter.setPen(QPen(primary, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(20, 32, 54, 32)
    painter.drawLine(44, 22, 54, 32)
    painter.drawLine(44, 42, 54, 32)

def draw_excel_icon(painter, primary, accent, gray):
    # Excel green color theme
    green_color = QColor("#16A34A")
    painter.setPen(QPen(green_color, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    
    # Excel sheet border
    painter.drawRoundedRect(QRectF(12, 6, 40, 52), 6, 6)
    
    # An X inside the document
    painter.drawLine(22, 20, 42, 40)
    painter.drawLine(42, 20, 22, 40)

def draw_ai_icon(painter, primary, accent, gray):
    # Sparkle / AI brain connection points
    painter.setPen(QPen(accent, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    
    # 4 points star (sparkle) in center
    # Top sparkle
    painter.drawLine(32, 10, 32, 54)
    painter.drawLine(10, 32, 54, 32)
    
    # Diagonal small lines
    painter.drawLine(22, 22, 42, 42)
    painter.drawLine(42, 22, 22, 42)
    
    # Draw central glow
    painter.setBrush(QBrush(primary))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(QRectF(26, 26, 12, 12))

def draw_gst_icon(painter, primary, accent, gray):
    # Tax/finance report with percent symbol
    painter.setPen(QPen(primary, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    
    painter.drawRoundedRect(QRectF(12, 6, 40, 52), 6, 6)
    
    # Draw a simple percentage symbol inside
    painter.setPen(QPen(accent, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    # Diagonal line
    painter.drawLine(22, 38, 42, 20)
    # Circles
    painter.setBrush(QBrush(accent))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(QRectF(22, 20, 6, 6))
    painter.drawEllipse(QRectF(36, 36, 6, 6))

def draw_tally_icon(painter, primary, accent, gray):
    # Arrow and document matching tally/accounting
    orange_color = QColor("#EA580C")
    painter.setPen(QPen(orange_color, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    
    painter.drawRoundedRect(QRectF(12, 6, 40, 52), 6, 6)
    
    # Draw two vertical bars and one diagonal bar (Tally counts)
    painter.setPen(QPen(orange_color, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(22, 20, 22, 40)
    painter.drawLine(28, 20, 28, 40)
    painter.drawLine(34, 20, 34, 40)
    painter.drawLine(18, 35, 38, 25)

def draw_search_icon(painter, primary, accent, gray):
    # Magnifying glass
    painter.setPen(QPen(gray, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    
    # Glass head
    painter.drawEllipse(QRectF(10, 10, 28, 28))
    
    # Glass handle
    painter.drawLine(32, 32, 54, 54)

def draw_bell_icon(painter, primary, accent, gray):
    # Notification Bell
    painter.setPen(QPen(primary, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    
    # Bell curve
    # Semi-circle top with flared bottom
    painter.drawArc(QRectF(16, 16, 32, 32), 0 * 16, 180 * 16)
    painter.drawLine(16, 32, 16, 44)
    painter.drawLine(48, 32, 48, 44)
    painter.drawLine(10, 44, 54, 44)
    
    # Bell clapper (bottom circle segment)
    painter.setBrush(QBrush(gray))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(QRectF(28, 48, 8, 8))

def draw_profile_icon(painter, primary, accent, gray):
    # User Profile Avatar Outline
    painter.setPen(QPen(primary, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    
    # Head
    painter.drawEllipse(QRectF(22, 10, 20, 20))
    
    # Shoulders
    painter.drawArc(QRectF(10, 38, 44, 44), 0 * 16, 180 * 16)
    painter.drawLine(10, 60, 54, 60)

def draw_duplicate_icon(painter, primary, accent, gray):
    # Overlapping double sheets
    painter.setPen(QPen(primary, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    
    # Back sheet
    painter.drawRoundedRect(QRectF(6, 6, 36, 44), 6, 6)
    
    # Front sheet (offset to bottom right)
    painter.setPen(QPen(accent, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(QBrush(QColor("#FFFFFF")))
    painter.drawRoundedRect(QRectF(20, 14, 38, 44), 6, 6)

def draw_email_icon(painter, primary, accent, gray):
    # Mail envelope
    painter.setPen(QPen(primary, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    
    # Envelope rectangle
    painter.drawRoundedRect(QRectF(8, 12, 48, 40), 6, 6)
    
    # Fold lines
    painter.drawLine(8, 16, 32, 34)
    painter.drawLine(56, 16, 32, 34)

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    # For independent testing of asset generator
    app = QApplication(sys.argv)
    generate_assets()
    print("Assets generated successfully.")

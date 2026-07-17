import math
import random
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QRectF
from PyQt6.QtGui import QPixmap, QColor, QPainter, QLinearGradient, QRadialGradient, QPainterPath, QPen, QImage, QBrush

class PremiumLogoCard(QWidget):
    """
    A premium glassmorphism card that renders the logo.
    Filters out the blue background programmatically and adds fade-in,
    overshoot scaling, breathing glow, and subtle floating animations.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 140)
        
        # Load and process the logo to remove blue background
        self.logo_pixmap = QPixmap("assets/logo.png")
        if not self.logo_pixmap.isNull():
            self.logo_pixmap = self.remove_blue_background(self.logo_pixmap)
            
        # Animation parameters
        self.anim_time = 0
        self.scale_factor = 0.0
        self.opacity = 0.0
        self.float_offset = 0.0
        self.glow_alpha = 100
        
        # 60 FPS animation timer
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation)
        self.anim_timer.start(16)

    def remove_blue_background(self, pixmap):
        """
        Removes the dark blue background square programmatically from the logo,
        retaining the white temple icon and its smooth antialiased gray edges.
        """
        image = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        for y in range(image.height()):
            for x in range(image.width()):
                color = image.pixelColor(x, y)
                # If the blue channel is significantly higher than red, make it transparent
                if color.blue() - color.red() > 45:
                    image.setPixelColor(x, y, QColor(0, 0, 0, 0))
        return QPixmap.fromImage(image)

    def update_animation(self):
        self.anim_time += 16
        
        # 1. Fade-in and overshoot scale-up (0% -> 115% -> 100% over first 800ms)
        t = self.anim_time / 800.0
        if t < 1.0:
            self.opacity = t
            # Easing: rapid scale up to 1.15, then settle back to 1.0
            if t < 0.7:
                self.scale_factor = (t / 0.7) * 1.15
            else:
                self.scale_factor = 1.15 - ((t - 0.7) / 0.3) * 0.15
        else:
            self.opacity = 1.0
            self.scale_factor = 1.0
            
        # 2. Subtle floating motion (2-3px) using a slow sine wave
        self.float_offset = math.sin(self.anim_time * 0.002) * 2.5
        
        # 3. Breathing glow opacity (every 3 seconds)
        self.glow_alpha = int(120 + math.sin(self.anim_time * 0.0015) * 60)
        
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        card_rect = QRectF(10, 10 + self.float_offset, 120, 120)
        
        # Draw breathing glow behind the glass card
        glow_grad = QRadialGradient(card_rect.center(), 70)
        glow_grad.setColorAt(0, QColor(79, 140, 255, int(self.glow_alpha * 0.35)))
        glow_grad.setColorAt(0.6, QColor(79, 140, 255, int(self.glow_alpha * 0.15)))
        glow_grad.setColorAt(1, QColor(0, 0, 0, 0))
        
        painter.save()
        painter.fillPath(self.get_rounded_rect_path(QRectF(0, 0, 140, 140), 24), glow_grad)
        painter.restore()
        
        # Set animation opacity
        painter.setOpacity(self.opacity)
        
        # Draw glassmorphism card base (rgba(255, 255, 255, 0.12))
        glass_path = self.get_rounded_rect_path(card_rect, 24)
        painter.fillPath(glass_path, QColor(255, 255, 255, 30))
        
        # Draw soft white border with low opacity
        border_pen = QPen(QColor(255, 255, 255, 60), 1.2)
        painter.setPen(border_pen)
        painter.drawPath(glass_path)
        
        # Draw logo with scale factor applied
        if not self.logo_pixmap.isNull():
            target_w = 64 * self.scale_factor
            target_h = 64 * self.scale_factor
            logo_rect = QRectF(
                card_rect.center().x() - target_w / 2,
                card_rect.center().y() - target_h / 2,
                target_w,
                target_h
            )
            painter.drawPixmap(logo_rect, self.logo_pixmap, QRectF(self.logo_pixmap.rect()))
        painter.end()

    def get_rounded_rect_path(self, rect, radius):
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        return path


class GlowingProgressBar(QWidget):
    """
    A custom vector-painted progress bar with a glowing gradient fill,
    rounded end caps, and an animated shimmer overlay moving across it.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0
        self.shimmer_offset = 0
        self.setFixedHeight(12)
        
        # Shimmer speed timer
        self.shimmer_timer = QTimer(self)
        self.shimmer_timer.timeout.connect(self.update_shimmer)
        self.shimmer_timer.start(25)

    def setValue(self, val):
        self.value = max(0, min(100, val))
        self.update()

    def update_shimmer(self):
        self.shimmer_offset = (self.shimmer_offset + 4) % 400
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background track
        track_rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        track_path = QPainterPath()
        track_path.addRoundedRect(track_rect, 4, 4)
        painter.fillPath(track_path, QColor(255, 255, 255, 20))
        
        # Draw progress fill
        progress_width = (self.width() - 4) * (self.value / 100.0)
        if progress_width > 0:
            fill_rect = QRectF(2, 2, progress_width, self.height() - 4)
            fill_path = QPainterPath()
            fill_path.addRoundedRect(fill_rect, 4, 4)
            
            # Gradient fill (Navy -> Blue -> Light Glow Blue)
            grad = QLinearGradient(0, 0, progress_width, 0)
            grad.setColorAt(0, QColor("#123DAF"))
            grad.setColorAt(0.6, QColor("#4F8CFF"))
            grad.setColorAt(1, QColor("#8AB8FF"))
            painter.fillPath(fill_path, grad)
            
            # Draw shimmer overlay (moving highlighted gradient)
            shimmer_grad = QLinearGradient(self.shimmer_offset - 100, 0, self.shimmer_offset + 100, 0)
            shimmer_grad.setColorAt(0, QColor(255, 255, 255, 0))
            shimmer_grad.setColorAt(0.5, QColor(255, 255, 255, 130))
            shimmer_grad.setColorAt(1, QColor(255, 255, 255, 0))
            
            painter.save()
            painter.setClipPath(fill_path)
            painter.fillRect(fill_rect, shimmer_grad)
            painter.restore()
            
            # Soft outline highlight glow
            pen = QPen(QColor(138, 184, 255, 120), 1.2)
            painter.setPen(pen)
            painter.drawPath(fill_path)
        painter.end()


class SplashScreen(QWidget):
    """
    A premium splash screen containing the customized PremiumLogoCard,
    Typography styled with a serif title, tagline controls,
    and a custom glowing progress indicator. Draws a multi-layer
    animated gradient and AI neural grid directly on the translucent window canvas.
    """
    loadingFinished = pyqtSignal()

    def __init__(self):
        super().__init__()
        
        # Frameless, translucent window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setFixedSize(650, 420)
        self.center_on_screen()
        
        # Master window fade out
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)
        
        # Floating background particles
        self.particles = []
        for _ in range(16):
            self.particles.append({
                "x": random.uniform(0, 650),
                "y": random.uniform(0, 420),
                "size": random.uniform(1.8, 5.0),
                "vx": random.uniform(-0.15, 0.15),
                "vy": random.uniform(-0.15, 0.15)
            })
            
        self.anim_tick = 0
        
        # Initialize UI elements
        self.init_ui()
        
        # Loading Simulation
        self.progress_value = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(30) # ~3 seconds total

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(12)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 1. Premium Logo Card
        self.logo_card = PremiumLogoCard()
        main_layout.addWidget(self.logo_card, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # 2. Elegantly styled Title
        self.title_label = QLabel("StatementForge")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("""
            font-size: 34px; 
            font-weight: bold; 
            color: #FFFFFF; 
            font-family: "Playfair Display", "Georgia", "Times New Roman", serif; 
            letter-spacing: 0.5px;
            background: transparent;
            border: none;
        """)
        main_layout.addWidget(self.title_label)
        
        # 3. Subtitle (AI Hub Branding)
        self.subtitle_label = QLabel("AI Powered Accounting Hub")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setStyleSheet("""
            font-size: 11px; 
            font-weight: 700; 
            color: #8AB8FF; 
            font-family: "Inter", "Segoe UI", "SF Pro Display", sans-serif;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            background: transparent;
            border: none;
        """)
        main_layout.addWidget(self.subtitle_label)
        
        # 4. Subtle Tagline
        self.tagline_label = QLabel("Parse • Verify • Analyze • Export")
        self.tagline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tagline_label.setStyleSheet("""
            font-size: 9px; 
            font-weight: 500; 
            color: #BAC9E2; 
            font-family: "Inter", "Segoe UI", sans-serif;
            letter-spacing: 2px;
            background: transparent;
            border: none;
        """)
        main_layout.addWidget(self.tagline_label)
        
        main_layout.addSpacing(18)
        
        # 5. Shimmer Progress Bar
        self.progress_bar = GlowingProgressBar()
        main_layout.addWidget(self.progress_bar)
        
        main_layout.addSpacing(4)
        
        # 6. Smooth Rotational Loading Status Info
        self.loading_label = QLabel("Initializing AI Engine...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("""
            font-size: 11px; 
            color: #8AB8FF; 
            font-weight: 600; 
            font-family: "Inter", "Segoe UI", sans-serif;
            background: transparent;
            border: none;
        """)
        
        # Opacity effect specifically for text fading on message change
        self.loading_opacity_effect = QGraphicsOpacityEffect(self.loading_label)
        self.loading_label.setGraphicsEffect(self.loading_opacity_effect)
        self.loading_opacity_effect.setOpacity(1.0)
        
        main_layout.addWidget(self.loading_label)

    def center_on_screen(self):
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geo = screen.geometry()
            x = (screen_geo.width() - self.width()) // 2
            y = (screen_geo.height() - self.height()) // 2
            self.move(x, y)

    def update_progress(self):
        self.progress_value += 1
        self.progress_bar.setValue(self.progress_value)
        
        # Particle positions and background ticker updates
        self.anim_tick += 1
        for part in self.particles:
            part["x"] += part["vx"]
            part["y"] += part["vy"]
            if part["x"] < 0: part["x"] = 650
            if part["x"] > 650: part["x"] = 0
            if part["y"] < 0: part["y"] = 420
            if part["y"] > 420: part["y"] = 0
            
        # Rotate loading texts dynamically based on progress milestones
        if self.progress_value == 1:
            self.set_loading_text("Initializing AI Engine...")
        elif self.progress_value == 18:
            self.set_loading_text("Loading OCR Models...")
        elif self.progress_value == 38:
            self.set_loading_text("Detecting Bank Format...")
        elif self.progress_value == 58:
            self.set_loading_text("Preparing Financial Intelligence...")
        elif self.progress_value == 78:
            self.set_loading_text("Optimizing Performance...")
        elif self.progress_value == 92:
            self.set_loading_text("Launching Dashboard...")
        elif self.progress_value == 100:
            self.set_loading_text("Ready")
            
        self.update() # Force repaint of background linear/radial grids
        
        if self.progress_value >= 100:
            self.timer.stop()
            self.fade_out_and_finish()

    def set_loading_text(self, text):
        """Fades the loading label out, updates the text string, and fades back in."""
        if self.loading_label.text() == text:
            return
            
        self.text_fade = QPropertyAnimation(self.loading_opacity_effect, b"opacity")
        self.text_fade.setDuration(120)
        self.text_fade.setStartValue(1.0)
        self.text_fade.setEndValue(0.0)
        
        def on_fade_out():
            self.loading_label.setText(text)
            self.text_fade_in = QPropertyAnimation(self.loading_opacity_effect, b"opacity")
            self.text_fade_in.setDuration(120)
            self.text_fade_in.setStartValue(0.0)
            self.text_fade_in.setEndValue(1.0)
            self.text_fade_in.start()
            
        self.text_fade.finished.connect(on_fade_out)
        self.text_fade.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Base Gradient Canvas (Deep Royal Blue, Navy, and Premium Blue)
        # Slow animated coordinate shift for background gradient breathing
        angle = self.anim_tick * 0.015
        x1 = 0.5 + math.sin(angle) * 0.4
        y1 = 0.5 + math.cos(angle) * 0.4
        x2 = 0.5 - math.sin(angle) * 0.4
        y2 = 0.5 - math.cos(angle) * 0.4
        
        base_grad = QLinearGradient(x1 * self.width(), y1 * self.height(), x2 * self.width(), y2 * self.height())
        base_grad.setColorAt(0, QColor("#071646")) # Navy
        base_grad.setColorAt(0.5, QColor("#0B1F6A")) # Deep Royal Blue
        base_grad.setColorAt(1, QColor("#1A56DB")) # Premium Blue
        
        rect_path = QPainterPath()
        rect_path.addRoundedRect(QRectF(self.rect()), 18, 18)
        painter.fillPath(rect_path, base_grad)
        
        # 2. Visual Accent Blobs (radial overlays in corners)
        tr_blob = QRadialGradient(self.width(), 0, 240)
        tr_blob.setColorAt(0, QColor(79, 140, 255, 55)) # Accent #4F8CFF
        tr_blob.setColorAt(1, QColor(0, 0, 0, 0))
        painter.fillPath(rect_path, tr_blob)
        
        bl_blob = QRadialGradient(0, self.height(), 260)
        bl_blob.setColorAt(0, QColor(18, 61, 175, 75)) # Secondary #123DAF
        bl_blob.setColorAt(1, QColor(0, 0, 0, 0))
        painter.fillPath(rect_path, bl_blob)
        
        # 3. Radial lighting behind the logo card
        logo_glow = QRadialGradient(self.width() / 2, 110, 180)
        logo_glow.setColorAt(0, QColor(79, 140, 255, 65))
        logo_glow.setColorAt(0.6, QColor(18, 61, 175, 15))
        logo_glow.setColorAt(1, QColor(0, 0, 0, 0))
        painter.fillPath(rect_path, logo_glow)
        
        # 4. Minimal Glowing Financial Grid Lines
        grid_pen = QPen(QColor(79, 140, 255, 10), 1.0)
        painter.setPen(grid_pen)
        # horizontal lines
        for y in range(40, self.height(), 60):
            painter.drawLine(0, y, self.width(), y)
        # vertical lines
        for x in range(40, self.width(), 65):
            painter.drawLine(x, 0, x, self.height())
            
        # 5. Faint AI Neural Connection Lines (polygon constellation links)
        connection_pen = QPen(QColor(138, 184, 255, 14), 1.0)
        painter.setPen(connection_pen)
        pts = [
            (50, 70), (110, 250), (180, 310), (510, 80), 
            (570, 190), (450, 340), (270, 45), (370, 370)
        ]
        painter.drawLine(pts[0][0], pts[0][1], pts[1][0], pts[1][1])
        painter.drawLine(pts[1][0], pts[1][1], pts[2][0], pts[2][1])
        painter.drawLine(pts[3][0], pts[3][1], pts[4][0], pts[4][1])
        painter.drawLine(pts[4][0], pts[4][1], pts[5][0], pts[5][1])
        painter.drawLine(pts[2][0], pts[2][1], pts[7][0], pts[7][1])
        painter.drawLine(pts[6][0], pts[6][1], pts[3][0], pts[3][1])
        
        # Draw node circles
        painter.setBrush(QColor(79, 140, 255, 30))
        painter.setPen(QColor(138, 184, 255, 50))
        for pt in pts:
            painter.drawEllipse(pt[0] - 2, pt[1] - 2, 4, 4)
            
        # 6. Soft Floating Particles
        painter.setBrush(QColor(255, 255, 255, 25))
        painter.setPen(Qt.PenStyle.NoPen)
        for part in self.particles:
            painter.drawEllipse(QRectF(part["x"], part["y"], part["size"], part["size"]))
            
        # 7. Vignette shading at edges
        vignette = QRadialGradient(self.width() / 2, self.height() / 2, self.width() * 0.75)
        vignette.setColorAt(0, QColor(0, 0, 0, 0))
        vignette.setColorAt(0.8, QColor(0, 0, 0, 50))
        vignette.setColorAt(1, QColor(0, 0, 0, 170))
        painter.setBrush(vignette)
        painter.drawPath(rect_path)
        
        # 8. Thin white highlight border around the window
        border_pen = QPen(QColor(255, 255, 255, 30), 1.2)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(rect_path)
        
        painter.end()

    def fade_out_and_finish(self):
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(500)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.finished.connect(self.on_animation_finished)
        self.anim.start()

    def on_animation_finished(self):
        self.close()
        self.loadingFinished.emit()

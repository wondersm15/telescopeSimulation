"""
Pop-out window for simulated images at perceived angular scale.
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
import io


class ImagePopoutWindow(QDialog):
    """Pop-out window showing image at perceived angular scale."""

    def __init__(self, figure, title="Simulated View", angular_size_arcmin=None, parent=None):
        super().__init__(parent)

        self.setWindowTitle(title)

        # Convert figure to pixmap
        buf = io.BytesIO()
        figure.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)

        # Load as QPixmap
        original_pixmap = QPixmap()
        original_pixmap.loadFromData(buf.getvalue())
        buf.close()

        if original_pixmap.isNull():
            print("Warning: Failed to load pixmap in pop-out window")
            self.close()
            return

        # Calculate display size based on angular size
        # Goal: show the image at a size that matches the perceived angular size
        # when viewing the screen at ~50cm distance

        # At 50cm viewing distance:
        # 1 degree subtends ~8.7mm on screen
        # Typical screen: 100-150 DPI
        # This gives ~34-52 pixels per degree - too small!

        # Solution: Use a comfortable scale factor (pixels per degree)
        # that makes the image visible while preserving FOV relationships
        if angular_size_arcmin is not None:
            angular_size_deg = angular_size_arcmin / 60.0

            # Scale factor: pixels per degree
            # Higher value = larger image (more comfortable to view)
            # Lower value = more "realistic" angular size
            # 200-300 pixels/degree is a good compromise
            pixels_per_degree = 250

            display_size = int(angular_size_deg * pixels_per_degree)

            # Clamp to reasonable range
            display_size = max(200, min(display_size, 1200))

            scale_info = f"True FOV: {angular_size_arcmin:.1f} arcmin ({angular_size_deg:.2f}°) | Scale: {pixels_per_degree} pixels/degree"
        else:
            # No angular size info - use a default
            display_size = 600
            scale_info = "Angular scale not available"

        # Scale the pixmap
        scaled_pixmap = original_pixmap.scaled(
            display_size, display_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # Layout
        layout = QVBoxLayout()

        # Info header
        info_label = QLabel(scale_info)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("padding: 10px; background-color: #f0f0f0; font-weight: bold;")
        layout.addWidget(info_label)

        # Image
        image_label = QLabel()
        image_label.setPixmap(scaled_pixmap)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(image_label)

        # Instructions
        instructions = QLabel(
            "This window shows the approximate perceived angular size.\n"
            "Higher magnification → smaller field of view → smaller window.\n"
            f"View from ~50cm for most realistic angular perception."
        )
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setStyleSheet("padding: 10px; font-size: 10pt; color: #666;")
        layout.addWidget(instructions)

        self.setLayout(layout)

        # Window size
        window_width = display_size + 100
        window_height = display_size + 200  # Extra space for labels

        self.resize(window_width, window_height)

        # Center on screen
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().geometry()
        self.move(
            screen.center().x() - window_width // 2,
            screen.center().y() - window_height // 2
        )

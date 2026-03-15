"""
Pop-out window for simulated images at correct angular scale.
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
import matplotlib.pyplot as plt
import io
from PIL import Image


class ImagePopoutWindow(QDialog):
    """Pop-out window showing image at correct angular scale."""

    def __init__(self, figure, title="Simulated View", angular_size_arcmin=None, parent=None):
        super().__init__(parent)

        self.setWindowTitle(title)

        # Calculate window size
        # Assume viewing distance of 50cm and convert angular size to linear size
        # At 50cm, 1 degree = ~8.7mm, so 1 arcmin = ~0.145mm
        # Screen pixels: assume ~100 DPI (typical), so 1mm = ~4 pixels
        # Therefore: 1 arcmin ≈ 0.58 pixels... but we want it visible!

        # Use a scale factor: 1 arcmin = 10 pixels (reasonable for viewing)
        if angular_size_arcmin is not None:
            pixels_per_arcmin = 10  # Tunable
            window_size = int(angular_size_arcmin * pixels_per_arcmin)
            window_size = max(400, min(window_size, 1200))  # Clamp to reasonable range
        else:
            window_size = 600  # Default

        # Convert figure to pixmap
        buf = io.BytesIO()
        figure.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        img = Image.open(buf)

        # Convert to QPixmap
        img_data = img.tobytes("raw", "RGBA")
        qimage = QPixmap()
        qimage.loadFromData(img_data)

        # Layout
        layout = QVBoxLayout()

        # Image label
        image_label = QLabel()
        pixmap = QPixmap(buf.getvalue())
        pixmap = pixmap.scaled(window_size, window_size,
                              Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
        image_label.setPixmap(pixmap)
        layout.addWidget(image_label)

        # Info label
        if angular_size_arcmin is not None:
            info = QLabel(f"Approximate angular size: {angular_size_arcmin:.1f} arcmin\n"
                         f"(Scale: {pixels_per_arcmin} pixels/arcmin for visibility)")
            info.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(info)

        self.setLayout(layout)

        buf.close()

        # Set window size
        self.resize(window_size + 50, window_size + 100)

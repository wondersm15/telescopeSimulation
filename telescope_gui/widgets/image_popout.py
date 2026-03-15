"""
Pop-out window for simulated images at full resolution.
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QScrollArea
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
import matplotlib.pyplot as plt
import io


class ImagePopoutWindow(QDialog):
    """Pop-out window showing image at full resolution."""

    def __init__(self, figure, title="Simulated View", angular_size_arcmin=None, parent=None):
        super().__init__(parent)

        self.setWindowTitle(title)

        # Convert figure to pixmap at high DPI
        buf = io.BytesIO()
        # Use higher DPI for better quality
        figure.savefig(buf, format='png', dpi=200, bbox_inches='tight')
        buf.seek(0)

        # Load as QPixmap
        pixmap = QPixmap()
        pixmap.loadFromData(buf.getvalue())
        buf.close()

        if pixmap.isNull():
            print("Warning: Failed to load pixmap in pop-out window")
            self.close()
            return

        # Get image dimensions
        img_width = pixmap.width()
        img_height = pixmap.height()

        # Layout with scroll area for large images
        layout = QVBoxLayout()

        # Info label at top
        info_text = f"Full resolution view"
        if angular_size_arcmin is not None:
            info_text += f" | True FOV: {angular_size_arcmin:.2f} arcmin ({angular_size_arcmin/60:.3f}°)"
        info_text += f"\nImage size: {img_width} × {img_height} pixels"

        info_label = QLabel(info_text)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("padding: 10px; background-color: #f0f0f0;")
        layout.addWidget(info_label)

        # Scroll area for image (allows scrolling if image is larger than screen)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(False)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Image label
        image_label = QLabel()
        image_label.setPixmap(pixmap)
        scroll_area.setWidget(image_label)

        layout.addWidget(scroll_area)

        # Instructions
        instructions = QLabel("Scroll to view full image if it's larger than the window")
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setStyleSheet("padding: 5px; font-size: 10pt; color: #666;")
        layout.addWidget(instructions)

        self.setLayout(layout)

        # Set window size - allow up to 90% of screen, minimum 600x600
        # This shows the image at its actual rendered size (or scrollable if larger)
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().geometry()
        max_width = int(screen.width() * 0.9)
        max_height = int(screen.height() * 0.9)

        # Add padding for info labels and scrollbars
        window_width = min(img_width + 50, max_width)
        window_height = min(img_height + 150, max_height)

        # Minimum size
        window_width = max(600, window_width)
        window_height = max(600, window_height)

        self.resize(window_width, window_height)

        # Center on screen
        self.move(
            screen.center().x() - window_width // 2,
            screen.center().y() - window_height // 2
        )

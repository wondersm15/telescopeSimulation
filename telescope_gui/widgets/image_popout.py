"""
Pop-out window for simulated images at perceived angular scale.
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
import io


class ImagePopoutWindow(QDialog):
    """Pop-out window showing image at perceived angular scale.

    The figure passed to this window should already be sized correctly
    (e.g., using the true angular size logic from plot_source_image).
    This window simply displays it without additional scaling.
    """

    def __init__(self, figure, title="Simulated View", display_mode="scaled", parent=None):
        super().__init__(parent)

        self.setWindowTitle(title)

        # Convert figure to pixmap at full resolution
        buf = io.BytesIO()
        figure.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)

        # Load as QPixmap
        pixmap = QPixmap()
        pixmap.loadFromData(buf.getvalue())
        buf.close()

        if pixmap.isNull():
            print("Warning: Failed to load pixmap in pop-out window")
            self.close()
            return

        # Layout
        layout = QVBoxLayout()

        # Info header (varies by display mode)
        header_text = {
            "scaled": "Standardized View — Enhanced detail, not at true angular scale",
            "true_size": "Perceived Angular Size View — Figure sized for ~50cm viewing distance",
            "eyepiece_view": "Eyepiece View — Fixed-size circular field with correct proportions",
        }.get(display_mode, "Simulated View")
        info_label = QLabel(header_text)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("padding: 10px; background-color: #f0f0f0; font-weight: bold;")
        layout.addWidget(info_label)

        # Image (display at natural size from figure)
        image_label = QLabel()
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(image_label)

        # Instructions
        instructions = QLabel(
            "This window shows the perceived angular size as calculated by the simulation.\n"
            "Higher magnification → smaller field of view → smaller window.\n"
            "View from ~50cm for most realistic angular perception."
        )
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setStyleSheet("padding: 10px; font-size: 10pt; color: #666;")
        layout.addWidget(instructions)

        self.setLayout(layout)

        # Size window to fit content
        self.adjustSize()

        # Center on screen safely
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().availableGeometry()  # Excludes taskbars/menus

        # Calculate centered position
        x = screen.x() + (screen.width() - self.width()) // 2
        y = screen.y() + (screen.height() - self.height()) // 2

        # Ensure window stays on screen
        x = max(screen.x(), min(x, screen.x() + screen.width() - self.width()))
        y = max(screen.y(), min(y, screen.y() + screen.height() - self.height()))

        self.move(x, y)

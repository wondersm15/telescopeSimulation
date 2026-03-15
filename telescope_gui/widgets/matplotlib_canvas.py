"""
Matplotlib canvas widget for embedding plots in Qt.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
import io
from PIL import Image
import numpy as np


class MatplotlibCanvas(QWidget):
    """Widget containing a matplotlib figure with navigation toolbar."""

    def __init__(self, parent=None, figsize=(8, 6), dpi=100):
        super().__init__(parent)

        # Create matplotlib figure
        self.figure = Figure(figsize=figsize, dpi=dpi)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def set_figure(self, fig):
        """Replace the current figure with a new one.

        Converts the provided figure to an image and displays it.
        This approach is simple and reliable.
        """
        # Save the figure to a buffer
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        buf.seek(0)

        # Read as image
        img = Image.open(buf)
        img_array = np.array(img)

        # Clear our figure and display the image
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.imshow(img_array)
        ax.axis('off')

        self.figure.tight_layout(pad=0)
        self.canvas.draw()

        buf.close()

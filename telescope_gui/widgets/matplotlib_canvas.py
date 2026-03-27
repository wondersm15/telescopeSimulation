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

        # Stored data-space limits for preserve_limits (not pixel-space)
        self._preserved_xlim = None
        self._preserved_ylim = None

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def set_figure(self, fig, preserve_limits=False):
        """Replace the current figure with a new one.

        Converts the provided figure to an image and displays it.
        When preserve_limits is True, applies stored data-space axes limits
        to the source figure before rendering (not pixel-space limits from
        the rasterized image).
        """
        # Apply preserved data-space limits to the source figure before rendering
        if preserve_limits and self._preserved_xlim is not None and fig.axes:
            fig.axes[0].set_xlim(self._preserved_xlim)
            fig.axes[0].set_ylim(self._preserved_ylim)

        # Save data-space limits BEFORE rasterizing
        if fig.axes:
            self._preserved_xlim = fig.axes[0].get_xlim()
            self._preserved_ylim = fig.axes[0].get_ylim()

        # Save the figure to a buffer
        # When preserving limits, skip bbox_inches='tight' so the figure layout
        # stays fixed — tight crop changes when data limits change, causing shifts.
        buf = io.BytesIO()
        if preserve_limits:
            fig.savefig(buf, format='png', dpi=100)
        else:
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

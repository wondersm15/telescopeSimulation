"""Stand-in for matplotlib.backends.backend_qtagg.

`FigureCanvasQTAgg.draw()` renders its figure to PNG and shows it in an
<img>. The desktop MatplotlibCanvas always displays a pre-rendered image
(set_figure rasterises the plot at 100 dpi, then imshows the pixels on an
axis-off axes), so the fast path encodes those pixels directly — the
browser shows exactly the bitmap the desktop shows, without a second
resampling pass. Any other figure is rendered with Agg as usual.

The interactive navigation toolbar (zoom/pan) is not available in the
browser; NavigationToolbar2QT is an invisible placeholder.
"""

from __future__ import annotations

import io

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from PyQt6.QtWidgets import QWidget
from qtshim.nodes import make_node


def _single_image(figure):
    """The image array if `figure` is one axis-off axes holding one image."""
    if len(figure.axes) != 1:
        return None
    ax = figure.axes[0]
    images = ax.get_images()
    if ax.axison or len(images) != 1 or ax.lines or ax.collections or ax.patches[1:]:
        return None
    array = np.asarray(images[0].get_array())
    if array.dtype != np.uint8 or array.ndim != 3 or array.shape[2] not in (3, 4):
        return None
    return array


def figure_png(figure) -> bytes | None:
    """PNG bytes for what `figure` shows, or None if it is empty."""
    if not figure.axes:
        return None
    array = _single_image(figure)
    buf = io.BytesIO()
    if array is not None:
        from PIL import Image
        Image.fromarray(array).save(buf, format="png")
    else:
        figure.savefig(buf, format="png", dpi=figure.dpi)
    return buf.getvalue()


class FigureCanvasQTAgg(FigureCanvasAgg, QWidget):
    """Agg canvas (as on the desktop) that is also a shim widget."""

    _default_grows = (True, True)

    def __init__(self, figure=None):
        QWidget.__init__(self)
        FigureCanvasAgg.__init__(self, figure)
        self._node = make_node("img", "qw FigureCanvas")
        # Qt's size hint for the canvas is the figure size in pixels; it
        # is the height the plot gets in a scroll area (elsewhere the
        # layout shrinks it to fit).
        _width, height = self.figure.get_size_inches() * self.figure.dpi
        self._node.set_style(height=f"{int(height)}px")

    def draw(self) -> None:
        # Headless nodes discard images; skip the encoding cost there.
        if getattr(self._node, "renders", False):
            self._node.set_image_png(figure_png(self.figure))

    def draw_idle(self) -> None:
        self.draw()


class NavigationToolbar2QT(QWidget):
    def __init__(self, canvas=None, parent=None, *args):
        super().__init__()
        self.setVisible(False)


FigureCanvas = FigureCanvasQTAgg

"""
Shared image-display controls: View, Exposure, Filter, Exit pupil.

These four controls decide how `plot_source_image` turns simulated light into
a picture, so every tab that renders a source must offer the same ones with
the same meanings — otherwise the Tutorial tab, whose job is to give
confidence in the main program, would be validating settings the main program
never uses. That is exactly how the Design tab ended up showing a 200 mm
Jupiter 67 % clipped to white: it called the renderer with library defaults
(Detector view, exposure 1.0) that no tutorial scenario exercised, and had no
control to change them.

So the widgets are built here, once:

- the factory functions (`make_view_combo`, `make_exposure_slider`, ...) are
  used by the Tutorial tab, which lays them out in its own horizontal row;
- `ImageDisplayControls` composes the same factories into one vertical panel
  for the Design and Comparison tabs.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget,
)

from telescope_sim.physics.filters import FILTER_LIBRARY


# ── View ─────────────────────────────────────────────────────────────
# The data values ("linear"/"log"/"log_integrated") are historical API
# strings for `plot_source_image(display_stretch=...)`; they no longer name a
# display curve (R5.8) — the three views differ in the instrument modelled.
VIEW_OPTIONS = (
    ("Detector (CCD)", "linear"),
    ("Eye (visual)", "log"),
    ("Eye + integration (1″ blur)", "log_integrated"),
)
EYE_VIEWS = ("log", "log_integrated")

VIEW_TOOLTIP = (
    "Both views are rendered so that screen brightness is\n"
    "proportional to simulated light; what differs is the\n"
    "instrument, not the display curve.\n\n"
    "Detector: you choose the exposure, and silicon records the\n"
    "  same colour at any light level.\n"
    "Eye: no exposure control (~0.1s fixed); extended objects are\n"
    "  shown at naked-eye brightness (the eye adapts), and colour\n"
    "  fades where the real luminance (set by the exit pupil)\n"
    "  falls below the cone threshold.\n"
    "Eye + integration: Eye plus 1″ spatial integration (eye's\n"
    "  ~1″ resolution at moderate eyepiece magnification —\n"
    "  chromatic-disk light mixes into the perceived core)."
)

# ── Exposure ─────────────────────────────────────────────────────────
# Log-scaled slider: internal range 0..200 maps to 10^((pos-100)/50), i.e.
# 0.01× → 1× → 100×, so one decade of slider travel = 10× collected flux.
EXPOSURE_SLIDER_MIN = 0
EXPOSURE_SLIDER_MAX = 200
EXPOSURE_SLIDER_CENTER = 100

EXPOSURE_TOOLTIP = (
    "Collected flux ∝ exposure. Higher = brighter image.\n"
    "1.0× is the photometric anchor (mag-0 star, 100 mm,\n"
    "no seeing → just-below-saturation). Bright sources or\n"
    "large apertures will saturate at lower exposure; faint\n"
    "sources need higher exposure to lift above the noise.\n"
    "Range: 0.01× to 100×, log-scaled. Detector view only."
)

# ── Filter ───────────────────────────────────────────────────────────
FILTER_TOOLTIP = (
    "Optical filter applied before the detector. ND = neutral\n"
    "density (uniform dimming). W = Wratten colour filters that\n"
    "shift the RGB balance — useful for revealing low-contrast\n"
    "planetary features (a light-blue W80A darkens Jupiter's\n"
    "blue-absorbing belts and Red Spot against the bright zones;\n"
    "a red W25 mostly cuts haze and gives a uniform red disk)."
)

# ── Exit pupil ───────────────────────────────────────────────────────
# Each maps to a representative observing-magnification regime. Only used
# when there is no eyepiece: with one, the exit pupil is derived
# (`resolve_exit_pupil_mm`) and this control is disabled.
EXIT_PUPIL_OPTIONS = (
    (7.0, "7.0 mm — max (naked-eye SB)"),
    (4.0, "4.0 mm — low power"),
    (2.0, "2.0 mm — planetary"),
    (1.0, "1.0 mm — high power"),
    (0.5, "0.5 mm — very high power"),
)
DEFAULT_EXIT_PUPIL_MM = 2.0

EXIT_PUPIL_TOOLTIP = (
    "Eye-view surface-brightness model (extended objects):\n"
    "a telescope can't exceed naked-eye surface brightness, and\n"
    "at higher magnification (smaller exit pupil) it falls as\n"
    "(exit pupil / 7 mm)². Exit pupil = aperture / magnification.\n"
    "This sets the real luminance (cd/m², shown on the image) and\n"
    "so the colour gate. The picture stays at naked-eye brightness\n"
    "because the eye adapts. Large exit pupils also wash out contrast.\n"
    "No effect in Detector view (exposure drives brightness there)\n"
    "or on point-like stars (aperture-driven).\n"
    "With an eyepiece the exit pupil is set by the eyepiece."
)

_CAPTION_STYLE = "font-size: 8pt; font-weight: normal; color: #555;"
_VALUE_STYLE = "font-size: 8pt; font-weight: bold; color: #333;"
_VALUE_STYLE_NA = "font-size: 8pt; font-weight: bold; color: #999;"


def slider_to_exposure(pos: int) -> float:
    """Exposure level for a slider position (log scale)."""
    return 10.0 ** ((pos - EXPOSURE_SLIDER_CENTER) / 50.0)


def exposure_to_slider(exposure: float) -> int:
    """Slider position for an exposure level (inverse of the above)."""
    return int(round(EXPOSURE_SLIDER_CENTER
                     + 50.0 * math.log10(max(exposure, 1e-9))))


def is_eye_view(display_stretch: str) -> bool:
    """True for the views where exposure does not apply."""
    return display_stretch in EYE_VIEWS


def caption_label(text: str) -> QLabel:
    """The small grey caption shown above each display control."""
    lbl = QLabel(text)
    lbl.setStyleSheet(_CAPTION_STYLE)
    return lbl


def make_view_combo(default_stretch: str = "log") -> QComboBox:
    """View dropdown: Detector / Eye / Eye + integration."""
    combo = QComboBox()
    for text, data in VIEW_OPTIONS:
        combo.addItem(text, data)
    idx = combo.findData(default_stretch)
    combo.setCurrentIndex(idx if idx >= 0 else combo.findData("log"))
    combo.setToolTip(VIEW_TOOLTIP)
    return combo


def make_exposure_slider(default_exposure: float = 1.0
                         ) -> tuple[QSlider, QLabel]:
    """Log-scaled exposure slider plus the label showing its value.

    The label tracks the slider while dragging; callers decide when to
    re-render (typically on release — a render per tick is too slow).
    """
    value_lbl = QLabel(f"{default_exposure:.2f}×")
    value_lbl.setStyleSheet(_VALUE_STYLE)
    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setMinimum(EXPOSURE_SLIDER_MIN)
    slider.setMaximum(EXPOSURE_SLIDER_MAX)
    slider.setValue(exposure_to_slider(default_exposure))
    slider.setToolTip(EXPOSURE_TOOLTIP)
    slider.valueChanged.connect(
        lambda v: value_lbl.setText(f"{slider_to_exposure(v):.2f}×"))
    return slider, value_lbl


def exposure_column(slider: QSlider, value_lbl: QLabel) -> QVBoxLayout:
    """'Exposure  1.00×' header above the slider."""
    col = QVBoxLayout()
    header = QHBoxLayout()
    header.addWidget(caption_label("Exposure"))
    header.addStretch()
    header.addWidget(value_lbl)
    col.addLayout(header)
    col.addWidget(slider)
    return col


def sync_exposure_enabled(slider: QSlider, value_lbl: QLabel | None,
                          eye_view: bool) -> None:
    """Grey out the exposure slider in Eye view (exposure is detector-only).

    Disabling it makes the physics explicit rather than leaving a live-looking
    control that does nothing.
    """
    slider.setEnabled(not eye_view)
    if value_lbl is None:
        return
    if eye_view:
        value_lbl.setText("N/A (Eye)")
        value_lbl.setStyleSheet(_VALUE_STYLE_NA)
    else:
        value_lbl.setText(f"{slider_to_exposure(slider.value()):.2f}×")
        value_lbl.setStyleSheet(_VALUE_STYLE)


def make_filter_combo(default_filter: str = "None") -> QComboBox:
    """ND / Wratten filter dropdown from `telescope_sim.physics.filters`."""
    combo = QComboBox()
    for flt in FILTER_LIBRARY:
        combo.addItem(flt.name, flt.name)
        combo.setItemData(combo.count() - 1, flt.description,
                          Qt.ItemDataRole.ToolTipRole)
    idx = combo.findData(default_filter)
    if idx >= 0:
        combo.setCurrentIndex(idx)
    combo.setToolTip(FILTER_TOOLTIP)
    return combo


def make_exit_pupil_combo(default_mm: float = DEFAULT_EXIT_PUPIL_MM
                          ) -> QComboBox:
    """Exit-pupil dropdown for the Eye-view surface-brightness model."""
    combo = QComboBox()
    for p_mm, text in EXIT_PUPIL_OPTIONS:
        combo.addItem(text, p_mm)
    idx = combo.findData(default_mm)
    combo.setCurrentIndex(idx if idx >= 0
                          else combo.findData(DEFAULT_EXIT_PUPIL_MM))
    combo.setToolTip(EXIT_PUPIL_TOOLTIP)
    return combo


class ImageDisplayControls(QWidget):
    """View / Exposure / Filter / Exit-pupil panel for source images.

    Built from the same factories as the Tutorial tab's controls. Emits
    `changed` when a setting that affects the render changes; hosts that
    render on a button press can ignore it.

    Defaults to the Eye view: it answers "what will I see through this
    telescope" without an exposure number someone has to tune, and an
    extended object is shown at its naked-eye surface brightness, so it does
    not saturate merely because the aperture grew.
    """

    changed = pyqtSignal()

    def __init__(self, default_stretch: str = "log",
                 default_exposure: float = 1.0,
                 default_filter: str = "None",
                 default_exit_pupil_mm: float = DEFAULT_EXIT_PUPIL_MM,
                 parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.view_combo = make_view_combo(default_stretch)
        layout.addWidget(caption_label("View"))
        layout.addWidget(self.view_combo)

        self.exposure_slider, self.exposure_value_label = (
            make_exposure_slider(default_exposure))
        layout.addLayout(exposure_column(self.exposure_slider,
                                         self.exposure_value_label))

        self.filter_combo = make_filter_combo(default_filter)
        layout.addWidget(caption_label("Filter"))
        layout.addWidget(self.filter_combo)

        self.exit_pupil_combo = make_exit_pupil_combo(default_exit_pupil_mm)
        layout.addWidget(caption_label("Exit pupil (Eye view)"))
        layout.addWidget(self.exit_pupil_combo)
        # Shown instead of the combo's own choice when something else (an
        # eyepiece, or a star source) decides the exit pupil's role.
        self.exit_pupil_note = QLabel("")
        self.exit_pupil_note.setWordWrap(True)
        self.exit_pupil_note.setStyleSheet("font-size: 8pt; color: #666;")
        self.exit_pupil_note.hide()
        layout.addWidget(self.exit_pupil_note)

        self.view_combo.currentIndexChanged.connect(self._sync_enabled)
        self.view_combo.currentIndexChanged.connect(self.changed)
        self.exposure_slider.sliderReleased.connect(self.changed)
        self.filter_combo.currentIndexChanged.connect(self.changed)
        self.exit_pupil_combo.currentIndexChanged.connect(self.changed)

        self._eyepiece_exit_pupil_mm: float | None = None
        self._is_extended_source = True
        self._sync_enabled()

    # ── state ────────────────────────────────────────────────────────
    def display_stretch(self) -> str:
        return self.view_combo.currentData()

    def exposure_level(self) -> float:
        return slider_to_exposure(self.exposure_slider.value())

    def filter_name(self) -> str:
        return self.filter_combo.currentData() or "None"

    def exit_pupil_mm(self) -> float:
        """The exit-pupil CHOICE; `resolve_exit_pupil_mm` lets an eyepiece
        override it, so this is safe to pass alongside one."""
        return float(self.exit_pupil_combo.currentData())

    def plot_kwargs(self) -> dict:
        """Keyword arguments for `plot_source_image`."""
        return dict(
            display_stretch=self.display_stretch(),
            exposure_level=self.exposure_level(),
            filter_name=self.filter_name(),
            exit_pupil_mm=self.exit_pupil_mm(),
        )

    def set_context(self, *, is_extended_source: bool,
                    eyepiece_exit_pupil_mm: float | None) -> None:
        """Tell the panel what the exit-pupil choice will actually do.

        The combo only matters for an extended source with no eyepiece; in
        the other cases it is disabled and a note says why, so the panel
        never offers a control whose value is silently ignored.
        """
        self._is_extended_source = is_extended_source
        self._eyepiece_exit_pupil_mm = eyepiece_exit_pupil_mm
        self._sync_enabled()

    def _sync_enabled(self) -> None:
        eye = is_eye_view(self.display_stretch())
        sync_exposure_enabled(self.exposure_slider,
                              self.exposure_value_label, eye)

        note = ""
        if not self._is_extended_source:
            note = "Stars: brightness ∝ aperture², exit pupil not used."
        elif self._eyepiece_exit_pupil_mm is not None:
            note = (f"Set by eyepiece: "
                    f"{self._eyepiece_exit_pupil_mm:.1f} mm")
        elif not eye:
            note = "Detector view: exposure sets brightness."
        self.exit_pupil_combo.setEnabled(not note)
        self.exit_pupil_note.setText(note)
        self.exit_pupil_note.setVisible(bool(note))

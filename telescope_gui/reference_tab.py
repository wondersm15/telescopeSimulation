"""
Parameters & Physics reference tab.

A read-only, scrollable guide covering telescope types, GUI parameters,
plot descriptions, and implemented physics.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QGroupBox, QLabel
)
from PyQt6.QtCore import Qt


# ---------------------------------------------------------------------------
# HTML content for each section
# ---------------------------------------------------------------------------

TELESCOPE_TYPES_HTML = """
<h3>Newtonian</h3>
<p>A <b>concave primary mirror</b> (parabolic or spherical) reflects light to a
<b>flat diagonal secondary</b> that redirects the beam out the side of the tube
to the eyepiece.</p>
<ul>
  <li><b>Pros:</b> Simple, inexpensive per inch of aperture, no chromatic
      aberration.</li>
  <li><b>Cons:</b> Coma at low f-ratios, spider-vane diffraction spikes,
      collimation-sensitive, open tube (dust/currents).</li>
</ul>

<h3>Cassegrain</h3>
<p>A concave <b>parabolic primary</b> focuses light onto a convex <b>hyperbolic
secondary</b>, which reflects the beam back through a hole in the primary to the
eyepiece at the rear.</p>
<ul>
  <li><b>Pros:</b> Long effective focal length in a compact tube, rear-mounted
      eyepiece is convenient.</li>
  <li><b>Cons:</b> Central obstruction reduces contrast, alignment is critical,
      more expensive than Newtonian.</li>
</ul>

<h3>Refractor</h3>
<p>Uses a <b>glass objective lens</b> (singlet, achromat, or apochromatic
doublet/triplet) at the front of the tube to bring light to focus at the rear.</p>
<ul>
  <li><b>Pros:</b> No obstruction, sharp high-contrast images, low maintenance,
      sealed tube.</li>
  <li><b>Cons:</b> Chromatic aberration (especially singlets), heavy and
      expensive at large apertures.</li>
</ul>

<h3>Maksutov-Cassegrain</h3>
<p>A thick, steeply curved <b>meniscus corrector</b> at the front corrects
spherical aberration from a spherical primary. A small aluminized spot on the
corrector acts as the secondary mirror.</p>
<ul>
  <li><b>Pros:</b> Excellent correction, rugged sealed tube, compact.</li>
  <li><b>Cons:</b> Slow to reach thermal equilibrium (thick corrector), limited
      to moderate apertures, larger central obstruction.</li>
</ul>

<h3>Schmidt-Cassegrain</h3>
<p>A thin <b>aspheric Schmidt corrector plate</b> at the front corrects
spherical aberration from a spherical primary, with a convex secondary mounted
on the corrector.</p>
<ul>
  <li><b>Pros:</b> Versatile, compact, widely available, good all-around
      performance.</li>
  <li><b>Cons:</b> Moderate central obstruction, mirror shift during focusing,
      potential for dew on corrector.</li>
</ul>
"""

PARAMETERS_HTML = """
<table cellpadding="4" cellspacing="0" style="border-collapse:collapse;">
<tr style="background:#e0e0e0;">
  <th align="left" style="padding:4px 8px;">Parameter</th>
  <th align="left" style="padding:4px 8px;">Description &amp; Physical Impact</th>
</tr>

<tr><td style="padding:4px 8px;"><b>Aperture (mm)</b></td>
<td style="padding:4px 8px;">Diameter of the primary mirror or objective lens.
Determines light-gathering power (proportional to D&sup2;) and diffraction-limited
resolution (Rayleigh limit &prop; &lambda;/D).</td></tr>

<tr style="background:#f5f5f5;"><td style="padding:4px 8px;"><b>f-ratio</b></td>
<td style="padding:4px 8px;">Focal length divided by aperture. Lower f-ratios
give wider true fields and faster photographic speed but amplify off-axis
aberrations (especially coma).</td></tr>

<tr><td style="padding:4px 8px;"><b>Focal Length (mm)</b></td>
<td style="padding:4px 8px;">Distance from the objective to the focal plane.
Longer focal lengths give higher image scale (arcsec/mm) and narrower true
fields.</td></tr>

<tr style="background:#f5f5f5;"><td style="padding:4px 8px;"><b>Primary Type</b></td>
<td style="padding:4px 8px;"><i>Parabolic</i> &mdash; zero on-axis spherical
aberration; <i>Spherical</i> &mdash; easier to manufacture but introduces
spherical aberration that grows as D&sup3;/f&sup3;.</td></tr>

<tr><td style="padding:4px 8px;"><b>Objective Type</b></td>
<td style="padding:4px 8px;">Refractor lens design. <i>Singlet</i> has severe
chromatic aberration; <i>Achromat</i> corrects at two wavelengths;
<i>APO</i> corrects at three or more &mdash; nearly diffraction-limited across
the visible band.</td></tr>

<tr style="background:#f5f5f5;"><td style="padding:4px 8px;"><b>Secondary Magnification</b></td>
<td style="padding:4px 8px;">Cassegrain-type amplification factor. Effective
focal length = primary FL &times; magnification. Higher values give a longer
effective FL in a shorter tube.</td></tr>

<tr><td style="padding:4px 8px;"><b>Meniscus Thickness (mm)</b></td>
<td style="padding:4px 8px;">Thickness of the Maksutov corrector lens. Thicker
correctors provide stronger correction but take longer to reach thermal
equilibrium, which can degrade images.</td></tr>

<tr style="background:#f5f5f5;"><td style="padding:4px 8px;"><b>Obstruction Ratio</b></td>
<td style="padding:4px 8px;">Secondary mirror diameter as a fraction of the
primary. Larger obstructions transfer energy from the Airy disk into the first
diffraction ring, reducing contrast on planetary detail.</td></tr>

<tr><td style="padding:4px 8px;"><b>Spider Vanes</b></td>
<td style="padding:4px 8px;">Struts supporting the secondary mirror. Each vane
produces two opposing diffraction spikes; 4 vanes give 4 spikes (pairs overlap).
More or wider vanes scatter more light.</td></tr>

<tr style="background:#f5f5f5;"><td style="padding:4px 8px;"><b>Source</b></td>
<td style="padding:4px 8px;">The astronomical object being observed (Jupiter,
Moon, Saturn, star field, or point source). Determines the angular size and
surface brightness distribution used in simulated images.</td></tr>

<tr><td style="padding:4px 8px;"><b>Seeing (arcsec FWHM)</b></td>
<td style="padding:4px 8px;">Atmospheric turbulence blurs all ground-based
images. Typical good-site seeing is 1&ndash;2&Prime;; excellent is
&lt;0.5&Prime;. Sets a floor on achievable resolution regardless of
aperture.</td></tr>

<tr style="background:#f5f5f5;"><td style="padding:4px 8px;"><b>Eyepiece FL / AFOV</b></td>
<td style="padding:4px 8px;">Eyepiece focal length sets magnification
(= telescope FL / eyepiece FL). Apparent field of view (AFOV) determines the
angular diameter of the visible circle; true field = AFOV / magnification.</td></tr>

<tr><td style="padding:4px 8px;"><b>Polychromatic</b></td>
<td style="padding:4px 8px;">When enabled, traces rays at multiple wavelengths
(R, G, B) simultaneously, revealing chromatic aberration in refractors and
color-dependent focus shifts.</td></tr>

<tr style="background:#f5f5f5;"><td style="padding:4px 8px;"><b>Wavelength (nm)</b></td>
<td style="padding:4px 8px;">Observation wavelength for monochromatic mode.
Shorter wavelengths (blue, ~450 nm) give finer diffraction limits but stronger
chromatic aberration in refractors. Default 550 nm (green, peak eye
sensitivity).</td></tr>
</table>
"""

PLOTS_HTML = """
<h3>Ray Trace Diagram</h3>
<p>Shows geometric light paths through the optical system. Rays are traced from
the entrance aperture to the focal plane, reflecting off mirrors or refracting
through lenses. Useful for understanding the optical layout and spotting gross
alignment or aberration issues.</p>

<h3>Simulated Image</h3>
<p>Renders the selected astronomical source as it would appear through the
telescope. The ideal source image is convolved with the telescope's PSF
(including diffraction, aberrations, and obstruction effects) to produce a
realistic view.</p>

<h3>PSF &mdash; 1D Profile</h3>
<p>Radial cross-section of the Point Spread Function. Shows the Airy pattern:
central peak, first minimum (Rayleigh limit), and diffraction rings. Central
obstruction transfers energy from the core into the rings, visible as a
reduced peak and brighter rings.</p>

<h3>PSF &mdash; 2D Map</h3>
<p>Two-dimensional intensity map of the PSF, usually displayed on a logarithmic
scale. Reveals diffraction spikes from spider vanes and asymmetries from
coma or other off-axis aberrations.</p>

<h3>Spot Diagram</h3>
<p>Plots the intersection points of many traced rays with the focal plane.
Points are color-coded by their radial distance from the optical axis to
highlight spherical aberration. RMS and maximum spot sizes are reported.</p>

<h3>Coma Field Analysis</h3>
<p>Maps coma magnitude across the field of view. Shows how comatic aberration
grows with field angle, helping users understand the usable field for sharp
imaging (especially important for fast Newtonians).</p>

<h3>Vignetting Curve</h3>
<p>Plots the fraction of light reaching the focal plane as a function of field
angle. Vignetting causes field-edge darkening and is influenced by baffles,
tube length, and secondary mirror size.</p>

<h3>Polychromatic Ray Trace</h3>
<p>Overlays ray traces at multiple wavelengths (typically red, green, blue) on
the same diagram. In reflectors the rays coincide; in refractors the wavelength-
dependent focus shifts reveal chromatic aberration.</p>
"""

PHYSICS_HTML = """
<h3>1. Diffraction (Wave Optics)</h3>
<p>Light diffracts at the circular aperture, producing the <b>Airy pattern</b>
&mdash; a central disk surrounded by concentric rings. This is the fundamental
resolution limit of any telescope.</p>
<p style="font-family:monospace; margin-left:20px;">
Rayleigh limit &theta; = 1.22 &lambda; / D &nbsp;(radians)<br>
Airy disk radius = 1.22 &lambda; f / D &nbsp;(at focal plane)<br>
Dawes limit &theta; = 116 / D<sub>mm</sub> &nbsp;(arcsec, empirical)
</p>
<p><i>Accuracy: Exact &mdash; uses Bessel-function Airy formula and FFT-based
computation.</i></p>

<h3>2. Central Obstruction</h3>
<p>The secondary mirror blocks the center of the aperture, redistributing
energy from the Airy disk into the diffraction rings. This lowers contrast on
fine planetary detail.</p>
<p style="font-family:monospace; margin-left:20px;">
PSF modified by (1 &minus; &epsilon;&sup2;) factor, &epsilon; = obstruction ratio
</p>
<p>Typical obstruction ratios: Newtonian 15&ndash;25%, Cassegrain 25&ndash;35%,
Maksutov 30&ndash;40%.</p>
<p><i>Accuracy: Exact obstruction model.</i></p>

<h3>3. Spider Vane Diffraction</h3>
<p>Support vanes for the secondary mirror act as thin diffracting obstructions,
producing spikes perpendicular to each vane. 4 straight vanes &rarr; 4 spikes
(pairs overlap), 3 vanes &rarr; 6 spikes.</p>
<p><i>Accuracy: Accurate &mdash; full 2D FFT of the aperture function including
vanes.</i></p>

<h3>4. Chromatic Aberration</h3>
<p>Glass dispersion causes different wavelengths to focus at different distances.
Severity depends on the objective design:</p>
<ul>
  <li><b>Singlet:</b> severe (&asymp;30/f-ratio arcsec blur)</li>
  <li><b>Achromat:</b> corrected at two wavelengths, residual secondary
      spectrum</li>
  <li><b>APO:</b> corrected at three+ wavelengths, near diffraction-limited</li>
</ul>
<p>Uses <b>Sellmeier equation</b> with real glass data (N-BK7, N-SF11, etc.).</p>
<p><i>Accuracy: Accurate for implemented lens types.</i></p>

<h3>5. Coma (Off-Axis Aberration)</h3>
<p>Off-axis point sources appear comet-shaped. Worst for fast parabolic mirrors;
negligible on-axis.</p>
<p style="font-family:monospace; margin-left:20px;">
Coma blur &asymp; (field_angle)&sup2; / (16 &middot; f-ratio&sup3;)
</p>
<p><i>Accuracy: Geometric approximation, valid for small field angles.</i></p>

<h3>6. Spherical Aberration</h3>
<p>Spherical mirrors focus marginal rays closer than paraxial rays, creating a
blur circle. Parabolic mirrors have zero on-axis spherical aberration by
design.</p>
<p style="font-family:monospace; margin-left:20px;">
LSA &asymp; D&sup3; / (128 f&sup3;) &nbsp;(Gauss formula)<br>
Angular blur &asymp; 1000 / (f-ratio)&sup3; arcsec
</p>
<p><i>Accuracy: Accurate &mdash; exact ray tracing for spherical surfaces.</i></p>
"""

NOT_IMPLEMENTED_HTML = """
<p>The following effects are <b>not yet modeled</b>. Simulation results will not
reflect these phenomena:</p>
<ul>
  <li><b>Astigmatism</b> &mdash; off-axis aberration causing elliptical star
      images. Requires full 3D ray tracing.</li>
  <li><b>Field Curvature</b> &mdash; best-focus surface is curved, causing edge
      blur on a flat detector/eyepiece field stop.</li>
  <li><b>Distortion (barrel/pincushion)</b> &mdash; magnification varies across
      the field, warping geometry but not resolution.</li>
  <li><b>Thermal Effects</b> &mdash; tube currents from temperature gradients
      degrade seeing inside the telescope.</li>
  <li><b>Optical Surface Errors</b> &mdash; manufacturing deviations from ideal
      shape reduce Strehl ratio.</li>
  <li><b>Atmospheric Seeing</b> &mdash; partially implemented internally but
      not yet fully exposed in the GUI.</li>
</ul>
<p><i>These limitations mean the simulation is most accurate for on-axis,
diffraction-limited performance of well-collimated telescopes at a single
temperature.</i></p>
"""


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------

def _make_section(title: str, html: str) -> QGroupBox:
    """Create a styled QGroupBox with rich-text content."""
    box = QGroupBox(title)
    box.setStyleSheet(
        "QGroupBox { font-weight: bold; font-size: 13px; "
        "margin-top: 18px; padding: 24px 8px 8px 8px; "
        "border: 1px solid palette(mid); border-radius: 4px; }"
        "QGroupBox::title { subcontrol-origin: margin; "
        "subcontrol-position: top left; padding: 4px 8px; "
        "background: palette(window); }"
    )
    layout = QVBoxLayout()
    label = QLabel(html)
    label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.RichText)
    label.setStyleSheet("QLabel { font-weight: normal; }")
    label.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse
    )
    layout.addWidget(label)
    box.setLayout(layout)
    return box


class ParametersPhysicsTab(QWidget):
    """Read-only reference tab documenting telescope parameters and physics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        layout = QVBoxLayout()

        # Header
        header = QLabel(
            "<h2>Telescope Parameters &amp; Physics Reference</h2>"
            "<p>A quick-reference guide to every parameter, plot, and physics "
            "model used in this simulation.</p>"
        )
        header.setWordWrap(True)
        header.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(header)

        # Sections
        layout.addWidget(_make_section("Telescope Types", TELESCOPE_TYPES_HTML))
        layout.addWidget(_make_section("Telescope Parameters", PARAMETERS_HTML))
        layout.addWidget(_make_section("Understanding the Plots", PLOTS_HTML))
        layout.addWidget(_make_section(
            "Implemented Physics", PHYSICS_HTML
        ))
        layout.addWidget(_make_section(
            "Not Yet Implemented", NOT_IMPLEMENTED_HTML
        ))

        layout.addStretch()
        container.setLayout(layout)
        scroll.setWidget(container)

        outer.addWidget(scroll)
        self.setLayout(outer)

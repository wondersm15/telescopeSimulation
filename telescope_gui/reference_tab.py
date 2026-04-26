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
<h3>Units Used in This Simulation</h3>
<table cellpadding="4" cellspacing="0" style="border-collapse:collapse;">
<tr style="background:#e0e0e0;">
  <th align="left" style="padding:4px 8px;">Quantity</th>
  <th align="left" style="padding:4px 8px;">Unit</th>
  <th align="left" style="padding:4px 8px;">Notes</th>
</tr>
<tr><td style="padding:4px 8px;">Angles (sky)</td><td>arcseconds (&#8243;)</td>
    <td>1&#176; = 3600&#8243;; Moon &#8776;1800&#8243;</td></tr>
<tr style="background:#f5f5f5;"><td style="padding:4px 8px;">Image-plane distances</td><td>mm</td>
    <td>Physical size at the focal plane</td></tr>
<tr><td style="padding:4px 8px;">Aperture &amp; focal length</td><td>mm</td>
    <td>Sometimes shown in inches for familiarity: 1&#8243; = 25.4 mm</td></tr>
<tr style="background:#f5f5f5;"><td style="padding:4px 8px;">Wavelengths</td><td>nm</td>
    <td>Visible: 380&ndash;700 nm; default 550 nm (green peak)</td></tr>
<tr><td style="padding:4px 8px;">Plate scale</td><td>arcsec/mm</td>
    <td>= 206265 / focal_length_mm</td></tr>
</table>

<h3>f-ratio</h3>
<p>The <b>f-ratio</b> (focal ratio) is defined as:</p>
<p style="font-family:monospace; margin-left:20px;">f = focal_length / aperture</p>
<p>Its role in telescope optics:</p>
<ul>
  <li><b>Image-plane scale:</b> physical distance on the focal plane for an
      angle &theta; is d = f_length &times; tan(&theta;) &asymp; f_length &times; &theta;
      (for small &theta;).</li>
  <li><b>Photographic speed:</b> lower f-ratio &rarr; brighter image &rarr; shorter
      exposure for extended objects.</li>
  <li><b>Coma-free field:</b> CFF &prop; f-ratio&sup2; — halving the f-ratio
      reduces the usable unvignetted field by 4&times;.</li>
  <li><b>Airy disk size:</b> r<sub>Airy</sub> = 1.22&lambda;f at the focal
      plane &mdash; larger at high f-ratios, smaller at low.</li>
  <li><b>Diffraction limit:</b> angular resolution 1.22&lambda;/D depends
      <i>only</i> on aperture, not f-ratio.</li>
</ul>

<h3>1. Diffraction (Wave Optics)</h3>
<p>Light diffracts at the circular aperture, producing the <b>Airy pattern</b>
&mdash; a central disk surrounded by concentric rings. This is the fundamental
angular resolution limit of any telescope.</p>
<p style="font-family:monospace; margin-left:20px;">
Airy disk radius &theta;<sub>R</sub> = 1.22 &lambda; / D &nbsp;[radians]<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
= 1.22 &lambda; [nm] &times; 206265 / D [mm] &nbsp;[arcsec]<br>
Airy radius at focal plane: r = 1.22 &lambda; &times; f-ratio &nbsp;[mm]
</p>
<p><b>Rayleigh criterion</b> (&theta; = 1.22&lambda;/D): two equal point sources
are &ldquo;just resolved&rdquo; when the central peak of one falls on the first
minimum of the other. Theoretical; requires high contrast.</p>
<p><b>Dawes limit</b> (&theta; &asymp; 116/D<sub>mm</sub> arcsec): empirical
limit for equal-magnitude double stars as observed visually. Slightly tighter
than Rayleigh because the eye detects the small bright spot at the saddle point.
Use Rayleigh for theoretical work; Dawes for practical double-star observing.</p>
<p><i>Accuracy: Exact &mdash; uses Bessel-function Airy/annular formula and
FFT-based pupil diffraction.</i></p>

<h3>2. Central Obstruction</h3>
<p>The secondary mirror blocks the centre of the aperture, redistributing
energy from the Airy disk into the diffraction rings. This reduces peak
intensity (<b>Strehl ratio</b>) and lowers contrast on fine planetary detail.</p>
<p><b>Strehl ratio</b> = peak intensity of aberrated PSF / peak of
unaberrated PSF. For a perfect annular aperture (only obstruction, no other
errors) the Mar&eacute;chal formula gives:</p>
<p style="font-family:monospace; margin-left:20px;">
S = (1 &minus; &epsilon;&sup2;)&sup2; &nbsp;&nbsp; (&epsilon; = obstruction ratio)
</p>
<p>This is not arbitrary scaling: total energy is conserved, but the Airy disk
widens and energy moves into the ring system, so the <i>on-axis peak</i> falls.
A 30% obstruction gives S &asymp; 0.73 (73% of unobstructed peak).</p>
<p><b>Modified Airy radius (annular Rayleigh limit):</b></p>
<p style="font-family:monospace; margin-left:20px;">
&theta;<sub>R,annular</sub> &asymp; 1.22&lambda;/D &times; 1/(1+&epsilon;&sup2;)
</p>
<p>This is a useful approximation, not the exact first zero of the annular
diffraction pattern. The exact zero requires solving<br>
&nbsp;&nbsp;&nbsp;&nbsp;<code>2J<sub>1</sub>(x)/x &minus; &epsilon;&sup2; &middot; 2J<sub>1</sub>(&epsilon;x)/(&epsilon;x) = 0</code><br>
numerically; for &epsilon; &le; 0.4 the 1/(1+&epsilon;&sup2;) form is accurate
to within a few percent. Used in <code>rayleigh_criterion_arcsec()</code> in
the codebase.</p>
<p><b>Resolution vs contrast:</b> obstruction <i>narrows</i> the Airy disk
slightly &mdash; superficially improving angular resolution on bright double
stars. However the contrast of extended planetary detail degrades because
more energy sits in the rings. These are different properties; the disk
narrowing (resolution) and the Strehl drop (contrast) are independent
consequences of the same obstruction.</p>
<p>Typical obstruction ratios: Newtonian 15&ndash;25%, Cassegrain 25&ndash;35%,
Maksutov 30&ndash;40%.</p>
<p><i>Accuracy: Exact annular-aperture PSF model.</i></p>

<h3>3. Spider Vane Diffraction</h3>
<p>Support vanes for the secondary mirror act as thin diffracting obstructions,
producing spikes <i>perpendicular</i> to each vane. Each arm creates a pair
of opposing spikes, so:</p>
<ul>
  <li>4 vanes (as 2 crossing arms) &rarr; 4 spikes</li>
  <li>3 vanes (independent arms) &rarr; 6 spikes</li>
  <li>6 vanes (as 3 crossing arm pairs) &rarr; 6 spikes, each 2&times; brighter
      than the 3-vane case</li>
</ul>
<p>Wider vanes scatter more light into spikes; curved vanes spread the spikes
into a fan (not modelled here).</p>
<p><i>Accuracy: Accurate &mdash; full 2D FFT of the aperture function including
vanes as half-strip obstructions.</i></p>

<h3>4. Chromatic Aberration</h3>
<p>Glass dispersion (wavelength-dependent refractive index) causes different
wavelengths to focus at different distances. Severity depends on the objective
design:</p>
<ul>
  <li><b>Singlet:</b> severe; focal shift &prop; &lambda;<sup>&minus;2</sup></li>
  <li><b>Achromat:</b> two wavelengths brought to the same focus (typically
      red &amp; blue); residual &ldquo;secondary spectrum&rdquo; remains</li>
  <li><b>APO:</b> three or more wavelengths corrected; near
      diffraction-limited across the visible band</li>
</ul>
<p><b>Sellmeier equation</b> (full form used in real glass design):</p>
<p style="font-family:monospace; margin-left:20px;">
n&sup2;(&lambda;) = 1 + &sum;<sub>i</sub> B<sub>i</sub>&lambda;&sup2; /
(&lambda;&sup2; &minus; C<sub>i</sub>)
</p>
<p>where B<sub>i</sub> and C<sub>i</sub> are glass-specific coefficients
(e.g., for N-BK7: B<sub>1</sub>=1.0396, C<sub>1</sub>=0.00600, etc.).<br>
<b>Note:</b> this simulation uses the simpler <b>Cauchy equation</b>
n(&lambda;) = A + B/&lambda;&sup2; for tractability &mdash; a good
approximation over the visible band but not as accurate as Sellmeier.</p>
<p><i>Accuracy: Accurate for implemented lens types using Cauchy
dispersion.</i></p>

<h3>5. Coma &amp; Seidel Aberrations</h3>
<p>Classical aberration theory (Seidel, 1856) expands the wavefront error
as a polynomial in field angle (&theta;) and normalised pupil radius (&rho;).
The five third-order (<i>primary</i>) terms are:</p>
<ol>
  <li><b>Spherical aberration</b> &mdash; on-axis blur, &rho;&sup4; term</li>
  <li><b>Coma</b> &mdash; comet-shaped off-axis blur, &theta;&rho;&sup3;</li>
  <li><b>Astigmatism</b> &mdash; line focus at two orientations,
      &theta;&sup2;&rho;&sup2;</li>
  <li><b>Field curvature</b> &mdash; best focus on a curved surface,
      &theta;&sup2;&rho;&sup2;</li>
  <li><b>Distortion</b> &mdash; magnification shift, &theta;&sup3;&rho;</li>
</ol>
<p>For fast Newtonians, <b>coma</b> is usually dominant off-axis:</p>
<p style="font-family:monospace; margin-left:20px;">
Coma-free field radius &prop; f-ratio&sup2;<br>
Coma blur &asymp; 3 &theta; D / (16 f&sup2;) &nbsp;[mm at focal plane]
</p>
<p><i>Accuracy: Geometric approximation for coma; astigmatism and field
curvature not yet modelled.</i></p>

<h3>6. Spherical Aberration</h3>
<p>Spherical mirrors focus marginal rays closer than paraxial rays, creating a
blur circle. Parabolic mirrors have zero on-axis spherical aberration by
design.</p>
<p style="font-family:monospace; margin-left:20px;">
Transverse SA blur radius r = D&sup3; / (128 f&sup2;) &nbsp;[mm]<br>
Angular blur &theta; = r &times; 206265 / f = D&sup3; &times; 206265 / (128 f&sup3;)
&nbsp;[arcsec]
</p>
<p>Blur scales as (1/f-ratio)&sup3; &mdash; halving f-ratio increases blur 8&times;.
A 200mm f/4 spherical mirror has &sim;25&Prime; blur; at f/8 this falls to
&sim;3&Prime;.</p>
<p><i>Accuracy: Accurate &mdash; exact ray tracing for spherical surfaces.</i></p>

<h3>7. Vignetting</h3>
<p>At off-axis field angles, the cone of light from the primary is partially
clipped by the secondary mirror (or tube walls), reducing illumination toward
the field edge.</p>
<p style="font-family:monospace; margin-left:20px;">
Fully-illuminated field radius &theta;<sub>fif</sub> = (r<sub>sec</sub>
&minus; r<sub>beam</sub>) / d<sub>sec</sub> &times; 206265
</p>
<p>where r<sub>sec</sub> is the secondary mirror radius, r<sub>beam</sub>
is the marginal beam radius at the secondary, and d<sub>sec</sub> is the
distance from primary to secondary (mirror separation). Beyond
&theta;<sub>fif</sub> illumination decreases toward zero at the
&ldquo;50% illumination edge.&rdquo;</p>
<p>Vignetting depends on f-ratio and secondary mirror size. Larger secondaries
reduce vignetting at the cost of more obstruction (contrast loss).</p>
<p><i>Accuracy: Geometric circle-circle overlap model, accurate for a
Newtonian with flat secondary.</i></p>

<h3>8. Atmospheric Seeing</h3>
<p>Refractive index fluctuations in the atmosphere (turbulence) blur all
ground-based images. The <b>Fried parameter r<sub>0</sub></b> characterises
turbulence strength; the long-exposure FWHM of the seeing disk is:</p>
<p style="font-family:monospace; margin-left:20px;">
FWHM<sub>seeing</sub> &asymp; 0.98 &lambda; / r<sub>0</sub>
</p>
<p>Key properties:</p>
<ul>
  <li>FWHM is <b>independent of aperture</b> once D &gt; r<sub>0</sub>
      (typically 10&ndash;20 cm at a good site). Bigger apertures collect
      more light but <i>not more detail</i> in this regime.</li>
  <li><b>Critical aperture</b> D<sub>crit</sub> = 1.22&lambda;/&theta;<sub>seeing</sub>:
      below this, diffraction dominates; above it, seeing dominates.</li>
  <li>FWHM scales weakly with wavelength: &prop; &lambda;<sup>&minus;1/5</sup>
      &mdash; blue light sees slightly worse than red.</li>
</ul>
<p>This simulation models seeing as a Gaussian blur with the specified FWHM.
Real seeing has a von K&aacute;rm&aacute;n spectrum and is not perfectly
Gaussian &mdash; bright stars show non-Gaussian wings and temporal variation.</p>
<p><i>Accuracy: Gaussian approximation &mdash; adequate for average long-exposure
seeing effects.</i></p>
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

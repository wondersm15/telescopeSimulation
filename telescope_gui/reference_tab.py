"""
Parameters & Physics reference tab.

A read-only, scrollable guide covering telescope types, GUI parameters,
plot descriptions, and implemented physics.
"""

import io

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QGroupBox, QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap


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
<p>Uses a <b>glass objective lens</b> at the front of the tube to bring light
to focus at the rear. Four objective designs are modelled, each attacking
chromatic aberration with progressively more glass elements and more exotic
materials:</p>

<table cellpadding="4" cellspacing="0" style="border-collapse:collapse; margin-top:6px;">
<tr style="background:#e0e0e0;">
  <th align="left" style="padding:4px 8px;">Design</th>
  <th align="left" style="padding:4px 8px;">Construction</th>
  <th align="left" style="padding:4px 8px;">How it reduces chromatic</th>
  <th align="left" style="padding:4px 8px;">Residual focal-shift</th>
</tr>
<tr>
  <td style="padding:4px 8px;"><i>Singlet</i></td>
  <td style="padding:4px 8px;">Single lens, typically BK7 crown glass.</td>
  <td style="padding:4px 8px;">No correction. The Cauchy dispersion of BK7 sends
    red light to a longer focus than blue.</td>
  <td style="padding:4px 8px;">~f / 100 between F (486 nm) and C (656 nm).</td>
</tr>
<tr style="background:#f5f5f5;">
  <td style="padding:4px 8px;"><i>Achromat</i></td>
  <td style="padding:4px 8px;">Cemented doublet: BK7 crown + F2 flint. The two
    glasses have opposite dispersion slopes.</td>
  <td style="padding:4px 8px;">Surface curvatures are chosen so the F-line and
    C-line meet at a common focus. The middle (d-line, 587 nm) sits at a slightly
    different focus &mdash; the <i>secondary spectrum</i>.</td>
  <td style="padding:4px 8px;">~f / 2500 residual secondary spectrum.</td>
</tr>
<tr>
  <td style="padding:4px 8px;"><i>APO doublet</i></td>
  <td style="padding:4px 8px;">FPL51 ED (extra-low-dispersion) glass + matching
    crown, cemented.</td>
  <td style="padding:4px 8px;">The ED glass has anomalous partial dispersion that
    flattens the focal curve. F, d, and C meet within a much tighter envelope.</td>
  <td style="padding:4px 8px;">~f / 8000 residual.</td>
</tr>
<tr style="background:#f5f5f5;">
  <td style="padding:4px 8px;"><i>APO triplet</i></td>
  <td style="padding:4px 8px;">Three elements (ED + flint + ED) in an air-spaced
    cell, with synthetic-fluorite or higher-grade ED glass.</td>
  <td style="padding:4px 8px;">Three free design degrees of freedom let the
    designer flatten the focal curve across the entire visible band. Approaches
    a diffraction-limited image at all wavelengths.</td>
  <td style="padding:4px 8px;">~f / 20000 residual.</td>
</tr>
</table>

<p style="margin-top:8px;">The chromatic-aberration tutorial scenario uses these
same residual focal-shift coefficients (see <i>Implemented Physics</i>
&rarr; Chromatic aberration) so the rendered halo sizes match the textbook
performance of each design class.</p>

<ul>
  <li><b>Pros:</b> No central obstruction or diffraction spikes from a spider, sharp
      high-contrast images, low maintenance, sealed tube.</li>
  <li><b>Cons:</b> Chromatic aberration (severe in singlets, residual in
      achromats, near-zero in apos). Glass elements get heavy and expensive at
      large apertures &mdash; 150 mm is a common practical limit.</li>
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
<p><b>Pixel meaning &amp; detector binning.</b> Each displayed pixel
represents the integrated flux a detector pixel of that angular size would
record &mdash; the total photons falling within the pixel's angular area,
not a sample of the underlying continuous image. Two paths support this:</p>
<ul>
<li><i>Star sources</i> (PointSource, StarField, DoubleStar): rendered
directly at the display resolution. A sub-pixel Airy disk records as one
bright pixel (all photons in one detector cell) instead of being spread
thinly across many pixels.</li>
<li><i>Extended sources</i> (Jupiter, Saturn, Moon): rendered internally at
higher resolution for accurate PSF convolution against their fine surface
texture, then <i>sum-binned</i> to the display resolution before
normalisation. Sum-binning conserves total flux per output pixel &mdash;
the physically-correct downsample. Averaging (matplotlib's default
bilinear interpolation) would dilute sub-pixel features and break flux
conservation.</li>
</ul>
<p>Display modes (linear/asinh/asinh+eye-blur) operate on this same binned
array; they alter only how pixel values are mapped to screen brightness,
not the simulated photon counts.</p>

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
design &mdash; see <i>Telescope Types &rarr; Refractor</i> for the construction
of each design class. The simulation models each with a different magnitude of
residual focal shift:</p>
<ul>
  <li><b>Singlet:</b> severe; focal shift follows the Cauchy index curve of BK7
      directly (no correction). F&ndash;C span ≈ f / 100.</li>
  <li><b>Achromat (BK7+F2 doublet):</b> the doublet brings F (486 nm) and C
      (656 nm) to a common focus, leaving a parabolic residual &ldquo;secondary
      spectrum&rdquo; with peak amplitude ≈ f / 2500 at the F&ndash;C midpoint.</li>
  <li><b>APO doublet (ED + crown):</b> the anomalous partial dispersion of the
      ED glass collapses the residual to ≈ f / 8000.</li>
  <li><b>APO triplet (ED + flint + ED, air-spaced):</b> three free degrees of
      freedom drive the residual to ≈ f / 20000 &mdash; below the diffraction
      limit at typical apertures.</li>
</ul>
<p>The defocus shift is converted to a per-wavelength PSF kernel by
convolving the wavelength-scaled Airy disk with the geometric defocus disk
(radius = |&Delta;f| / 2F). For severe defocus this gives a flat-topped uniform
disc (the geometric-optics limit); for mild defocus it approaches an Airy
pattern with reduced peak.</p>
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

<h3>9. Photometry, Saturation &amp; Filters</h3>
<p>Source brightness is anchored to a fixed reference rather than
re-normalised per frame, so absolute magnitude, aperture, exposure,
and filter transmission all interact realistically.</p>
<p><b>Brightness pipeline (linear domain):</b></p>
<p style="font-family:monospace; margin-left:20px;">
flux = 10<sup>&minus;0.4 m</sup> &times; (D / D<sub>ref</sub>)<sup>2</sup>
&times; T(&lambda;) &times; exposure
</p>
<p>where D<sub>ref</sub> = 100&nbsp;mm is the calibration aperture and
T(&lambda;) is the filter transmission. A mag-0 star through a 100&nbsp;mm
scope at unit exposure with no filter peaks just below the saturation
level (= 1.0); brighter sources, larger apertures, or longer exposures
saturate; dimmer sources sit at their true relative brightness.</p>
<p><b>Display modes</b> (apply to the same simulated data):</p>
<ul>
  <li><b>Detector (linear)</b>: raw per-pixel intensity. A real CCD's
  response to photon counts. Bright objects clip to white; dim ones
  sit at a few percent. This is what a calibrated detector records
  before any post-processing.</li>
  <li><b>Eye (asinh)</b>: an inverse-hyperbolic stretch that
  approximates the eye's logarithmic intensity response (Pogson scale).
  Reveals dim features alongside bright ones &mdash; matches the visual
  impression at the eyepiece.</li>
  <li><b>Eye + integration</b>: as Eye, plus a 1&Prime; spatial blur
  approximating the eye's spatial resolution at moderate magnification.</li>
</ul>
<p>In the Eye modes, an additional <b>cone-desaturation</b> step blends
high-flux pixels toward grey luminance by
<i>w</i> = <i>I</i>/(<i>I</i> + 0.5). This reproduces the &ldquo;Jupiter
looks washed out&rdquo; effect &mdash; the eye's colour-sensitive cones lose
discrimination at high brightness, so saturated pixels read as nearly
white rather than retaining their original hue.</p>
<p><b>Filters</b> are applied in the linear-flux domain before
saturation clipping, so they really do reduce the photons delivered to
the detector:</p>
<ul>
  <li><b>Neutral density (ND)</b>: wavelength-flat transmission of
  10<sup>&minus;OD</sup>. ND-1.0 passes 10&nbsp;%, ND-2.0 1&nbsp;%.
  Useful for bringing bright targets (Moon, Jupiter at 250&times;) into
  a comfortable visual range without changing magnification or PSF.</li>
  <li><b>Wratten colour filters</b> (W25 red, W47 blue, W58 green):
  Gaussian-approximated passbands. They shift the RGB balance and
  reduce overall brightness because most of the spectrum is blocked &mdash;
  use for boosting low-contrast planetary detail (W25 lifts the Great
  Red Spot, W47 emphasises Jovian zones, W58 increases belt
  contrast).</li>
</ul>
<p><i>Accuracy: filter spectra are Gaussian approximations of the
published Wratten/Schott curves; the qualitative behaviour matches but
the absolute transmission can differ a few percent from
manufacturer specifications. No out-of-band leakage modelled.</i></p>

<h3>10. Live Ephemeris (Real-Time Targets)</h3>
<p>Real Objects scenarios (Jupiter, Saturn, Moon) expose a
<b>Use live ephemeris</b> checkbox. When enabled, the source is
constructed with <code>use_realtime=True</code> and queries the JPL
DE421 ephemeris (via the <code>skyfield</code> package) to compute:</p>
<ul>
  <li>Current Earth&ndash;target distance &rarr; apparent angular diameter.
  Jupiter spans ~30&Prime; (apoapsis) to ~50&Prime; (closest approach);
  Saturn ~15&Prime; to 20&Prime;; Moon ~1800&Prime; (varies ~14&nbsp;% over a
  month with the Earth&ndash;Moon distance).</li>
  <li>Saturn ring tilt (B angle). Saturn's rotation axis is fixed in
  space at 26.7&deg; from the orbital plane; from Earth's perspective
  the tilt cycles between &plusmn;26.7&deg; over Saturn's 29.5-year
  orbit. The next ring-plane crossing is in 2025 &mdash; near that
  date the rings nearly disappear at low magnification.</li>
  <li>Moon illuminated fraction and approximate sub-observer
  longitude (phase). New / first-quarter / full / last-quarter
  appearances follow the actual lunation.</li>
</ul>
<p>Default (checkbox off) uses representative fixed values: Jupiter
40&Prime;, Saturn 18&Prime; with 20&deg; ring tilt, Moon 1870&Prime; at
full phase. The fixed mode is appropriate for "what does Jupiter look
like through a 200&nbsp;mm scope" pedagogical comparisons; the live mode
is appropriate for "if I go out tonight, will my scope match the
simulation?" validation.</p>
<p><i>Accuracy: DE421 is JPL's standard low-precision planetary
ephemeris (~1&Prime; over 1900&ndash;2050). Saturn ring-tilt formula
here uses ecliptic-latitude proxy &mdash; accurate to ~1&deg; near
maximum-tilt epochs (2002, 2017, 2032), less so near the crossing
itself. First-use downloads the 16&nbsp;MB ephemeris into
<code>~/.skyfield</code>; subsequent loads are local.</i></p>
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

VIGNETTING_DIAGRAM_CAPTION_HTML = (
    "<p>A star on the optical axis sends a light cone that lands squarely on "
    "the secondary mirror &mdash; every ray is caught and the image is "
    "<b>fully illuminated</b>. A star <i>off</i> the axis sends its cone in "
    "at an angle, so by the time the cone reaches the secondary it has "
    "shifted sideways (left panel). Once the shift is large enough, the far "
    "edge of the cone <b>misses the secondary</b> and that light is lost "
    "(red) &mdash; the star is dimmed. The right panel is the same effect "
    "seen face-on: the circular beam footprint slides off the circular "
    "secondary aperture, and the non-overlapping sliver is the vignetted "
    "light (the <i>circle&ndash;circle overlap</i> model the simulation "
    "uses).</p>"
    "<p style='font-family:monospace; margin-left:20px;'>"
    "Fully-illuminated field &theta;<sub>fif</sub> = (r<sub>sec</sub> "
    "&minus; r<sub>beam</sub>) / d<sub>sec</sub> &times; 206265&Prime;</p>"
    "<p>Inside &theta;<sub>fif</sub> illumination is 100%; beyond it the "
    "overlap fraction &mdash; and the illumination &mdash; falls smoothly "
    "toward the 50% edge. A larger secondary pushes &theta;<sub>fif</sub> "
    "outward (less vignetting) at the cost of a larger central obstruction.</p>"
    "<p><b>Why you don't see vignetting on the Star Field Showcase:</b> for a "
    "normally-sized secondary, &theta;<sub>fif</sub> is huge &mdash; a 200&nbsp;mm "
    "f/4 Newtonian is fully illuminated out to roughly 75&prime; (arcminutes), "
    "far beyond the few-arcminute star field, so no star there is measurably "
    "dimmed. Vignetting matters for wide-field astrophotography and undersized "
    "secondaries, not a high-power visual field. (Tube/focuser vignetting is "
    "not modelled.)</p>"
    "<p><i>Accuracy: schematic geometry (an unfolded Newtonian) for the "
    "picture; the illumination fraction itself uses the exact circle&ndash;"
    "circle overlap in the physics engine.</i></p>"
)


def _build_vignetting_diagram():
    """Build a static illustrative diagram of vignetting geometry.

    Two panels:
      (A) Side view — the converging light cone from an off-axis star is
          laterally shifted at the secondary and its far edge misses the
          secondary's clear aperture (the lost light is shaded red).
      (B) Secondary-face view — the "circle overlap" model the simulation
          uses: the beam footprint (blue) slides off the secondary aperture
          (grey) as the field angle grows; the non-overlapping fraction is
          the vignetted (lost) light.

    Schematic (an unfolded Newtonian, drawn to scale in relative units) — it
    illustrates the geometry, it is not a ray trace. Returns a matplotlib
    Figure.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    import numpy as np

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(10.0, 4.6))

    # ── Panel A: side view ────────────────────────────────────────────────
    D = 2.0                 # primary aperture (relative units)
    F = 4.2                 # primary → focus distance
    y_sec = 0.70 * F        # secondary height along the axis
    sec_half = 0.32         # secondary clear half-width
    # Beam half-width at the secondary (cone narrows from D/2 at primary to 0
    # at focus): r_beam(y) = (D/2) * (1 - y/F)
    r_beam_sec = (D / 2.0) * (1.0 - y_sec / F)

    axA.set_title("Side view (schematic): off-axis cone clipped\n"
                  "by the secondary", fontsize=9)
    # Primary mirror
    axA.plot([-D / 2, D / 2], [0, 0], color="black", lw=3, solid_capstyle="butt")
    axA.text(0, -0.22, "Primary mirror (aperture D)", ha="center",
             va="top", fontsize=7.5)

    # On-axis cone (blue): edges from primary rim converge to focus at (0, F)
    axA.fill([-D / 2, D / 2, 0], [0, 0, F], color="#3b7fd0", alpha=0.14,
             zorder=0)
    for x0 in (-D / 2, D / 2):
        axA.plot([x0, 0], [0, F], color="#3b7fd0", lw=1.0)
    axA.plot(0, F, marker="*", color="#3b7fd0", ms=11)
    axA.text(-0.1, F + 0.05, "on-axis focus\n(fully illuminated)", ha="right",
             va="center", fontsize=7, color="#245a9e")

    # Off-axis cone (orange): star at field angle θ → focus shifts to (+dx, F).
    # dx chosen so the beam is PARTIALLY clipped at the secondary (clearest
    # illustration): part of the cone lands on the secondary, part misses.
    dx = 0.5
    axA.fill([-D / 2, D / 2, dx], [0, 0, F], color="#e08a2b", alpha=0.12,
             zorder=0)
    for x0 in (-D / 2, D / 2):
        axA.plot([x0, dx], [0, F], color="#e08a2b", lw=1.0)
    axA.plot(dx, F, marker="*", color="#e08a2b", ms=11)
    axA.text(dx + 0.12, F + 0.05, "off-axis focus", ha="left", va="center",
             fontsize=7, color="#a9631a")

    # Secondary clear aperture (grey bar) at y_sec.
    axA.plot([-sec_half, sec_half], [y_sec, y_sec], color="0.3", lw=7,
             solid_capstyle="butt", zorder=4)
    axA.text(-sec_half - 0.08, y_sec, "secondary\nclear\naperture",
             ha="right", va="center", fontsize=7, color="0.3")

    # Off-axis beam footprint at the secondary height: centre is shifted; the
    # part beyond the secondary's clear aperture is lost.
    cx_off = dx * (y_sec / F)  # cone centre at the secondary height
    right_edge = cx_off + r_beam_sec
    # Shade the clipped (lost) portion: the beam beyond +sec_half.
    if right_edge > sec_half:
        axA.fill_between([sec_half, right_edge],
                         [y_sec - 0.16, y_sec - 0.16],
                         [y_sec + 0.16, y_sec + 0.16],
                         color="#d0342b", alpha=0.55, zorder=5)
        axA.annotate("clipped rays\n(lost light → dimmer)",
                     xy=((sec_half + right_edge) / 2, y_sec + 0.16),
                     xytext=(sec_half + 0.35, y_sec - 1.05),
                     fontsize=7, color="#a11", ha="left",
                     arrowprops=dict(arrowstyle="->", color="#a11", lw=0.9))
    axA.set_xlim(-D / 2 - 0.75, D / 2 + 0.75)
    axA.set_ylim(-0.6, F + 0.6)
    axA.set_aspect("equal")
    axA.axis("off")

    # ── Panel B: secondary-face circle-overlap model ──────────────────────
    axB.set_title("Secondary face: beam footprint vs clear aperture",
                  fontsize=9)
    r_sec = 1.0             # secondary clear radius (drawn)
    r_bm = 0.9              # beam footprint radius
    # Three field angles → three offsets of the beam footprint centre.
    cases = [
        (0.0, "#2f9e44", "on-axis: 100%"),
        (r_sec - r_bm, "#f59f00", "θ_fif: onset"),
        (0.55, "#d0342b", "off-axis: vignetted"),
    ]
    # Secondary aperture (grey disk)
    axB.add_patch(Circle((0, 0), r_sec, facecolor="0.85", edgecolor="0.4",
                         lw=1.3, zorder=1))
    axB.text(0, -r_sec - 0.18, "secondary clear aperture", ha="center",
             va="top", fontsize=7.5, color="0.3")
    th = np.linspace(0, 2 * np.pi, 100)
    for off, color, label in cases:
        axB.plot(off + r_bm * np.cos(th), r_bm * np.sin(th), color=color,
                 lw=1.6, zorder=3)
    # Shade the lost sliver for the vignetted case (beam outside the aperture)
    off_v = cases[-1][0]
    xs = np.linspace(-r_bm, r_bm, 400) + off_v
    y_top = np.sqrt(np.clip(r_bm ** 2 - (xs - off_v) ** 2, 0, None))
    outside = xs ** 2 > r_sec ** 2  # beam pixels outside the secondary disk
    axB.fill_between(xs, -y_top, y_top, where=outside, color="#d0342b",
                     alpha=0.30, zorder=2)
    # Legend-ish labels
    for i, (off, color, label) in enumerate(cases):
        axB.text(1.35, 0.7 - 0.45 * i, label, color=color, fontsize=7.5,
                 va="center")
        axB.plot(1.22, 0.7 - 0.45 * i, marker="o", color=color, ms=6)
    axB.set_xlim(-1.4, 2.9)
    axB.set_ylim(-1.5, 1.5)
    axB.set_aspect("equal")
    axB.axis("off")

    fig.suptitle("Vignetting — off-axis light clipped by the secondary mirror",
                 fontsize=11, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    return fig


def _figure_to_pixmap(fig, dpi: int = 110) -> QPixmap:
    """Rasterise a matplotlib Figure to a QPixmap (no temp files)."""
    import matplotlib.pyplot as plt
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    buf.seek(0)
    pix = QPixmap()
    pix.loadFromData(buf.getvalue(), "PNG")
    buf.close()
    return pix


def _make_figure_section(title: str, fig, caption_html: str) -> QGroupBox:
    """Section with a rendered matplotlib figure above a rich-text caption."""
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
    img = QLabel()
    img.setPixmap(_figure_to_pixmap(fig))
    img.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    layout.addWidget(img)
    caption = QLabel(caption_html)
    caption.setWordWrap(True)
    caption.setTextFormat(Qt.TextFormat.RichText)
    caption.setStyleSheet("QLabel { font-weight: normal; }")
    caption.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse)
    layout.addWidget(caption)
    box.setLayout(layout)
    return box


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
        layout.addWidget(_make_figure_section(
            "Vignetting (diagram)", _build_vignetting_diagram(),
            VIGNETTING_DIAGRAM_CAPTION_HTML))
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

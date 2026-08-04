"""
Parameters & Physics reference tab.

A read-only, scrollable guide covering telescope types, GUI parameters,
plot descriptions, and implemented physics.
"""

import html as html_lib
import io
import re

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QGroupBox, QLabel
)
from PyQt6.QtCore import Qt, QPoint
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
to focus at the rear.</p>
<p>Four objective designs are modelled, each attacking chromatic aberration
with progressively more glass elements and more exotic materials: <i>singlet</i>,
<i>achromat</i>, <i>APO doublet</i> and <i>APO triplet</i>. The glass types, how
each design cancels colour, the residual focal shift it leaves, and what the
extra performance costs are all set out under
<b>Implemented Physics &rarr; 4. Chromatic Aberration</b> &mdash; which is
where the tutorial's <i>Chromatic Aberration</i> module links to.</p>

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
design &mdash; the glass types and construction of each class are set out
under <i>The glasses, and what each design class buys you</i> further down this
section. The simulation models each with a different magnitude of residual
focal shift:</p>
<ul>
  <li><b>Singlet:</b> severe; focal shift follows the Cauchy index curve of BK7
      directly (no correction). F&ndash;C span ≈ f / 100.</li>
  <li><b>Achromat (BK7+F2 doublet):</b> the doublet brings F (486 nm) and C
      (656 nm) to a common focus, leaving a parabolic residual &ldquo;secondary
      spectrum&rdquo; with peak amplitude ≈ f / 2500 at the F&ndash;C midpoint.</li>
  <li><b>APO doublet (ED + crown):</b> the anomalous partial dispersion of the
      ED glass collapses the residual to ≈ f / 16000 (a faint halo on only the
      brightest stars).</li>
  <li><b>APO triplet (ED + flint + ED, air-spaced):</b> three free degrees of
      freedom drive the residual to ≈ f / 45000 &mdash; below the diffraction
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

<h4>The glasses, and what each design class buys you</h4>
<p>The four <b>Objective</b> settings in the tutorial's <i>Chromatic
Aberration</i> module are not arbitrary labels &mdash; each names a real
construction built from specific glass types, and the residual focal shifts
tabulated above are what those glasses actually achieve. What follows is the
glass behind each design, and what the extra elements cost you.</p>

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
  <td style="padding:4px 8px;">~f / 16000 residual (~1.5&times; Airy: a faint
    halo only on the brightest stars).</td>
</tr>
<tr style="background:#f5f5f5;">
  <td style="padding:4px 8px;"><i>APO triplet</i></td>
  <td style="padding:4px 8px;">Three elements (ED + flint + ED) in an air-spaced
    cell, with synthetic-fluorite or higher-grade ED glass.</td>
  <td style="padding:4px 8px;">Three free design degrees of freedom let the
    designer flatten the focal curve across the entire visible band. Approaches
    a diffraction-limited image at all wavelengths.</td>
  <td style="padding:4px 8px;">~f / 45000 residual (below the Airy radius:
    colour-free).</td>
</tr>
</table>

<p style="margin-top:8px;">The chromatic-aberration tutorial scenario uses the
residual focal-shift coefficients in the right-hand column above, so the
rendered halo sizes match the textbook performance of each design class. In the
module, switch the <b>Objective</b>
between these four designs (and use <b>Focal zoom &rarr; Close</b> to resolve the
tiny achromat/APO residuals that are invisible at the wide singlet scale).</p>

<p><b>Cost vs. performance.</b> Each step up the ladder buys a roughly 3&ndash;5&times;
reduction in the colour error for a similar jump in price (exotic glass and extra
elements dominate the cost):</p>
<ul>
  <li><b>Singlet</b> &mdash; cheapest glass, but the colour error is so large it is
      essentially never sold for astronomy today.</li>
  <li><b>Achromat</b> &mdash; the value choice: ordinary crown+flint, inexpensive,
      and colour is well controlled at slow focal ratios (an f/10&ndash;f/12
      &ldquo;achro&rdquo; shows little false colour). Most beginner refractors.</li>
  <li><b>APO doublet (ED)</b> &mdash; typically several times the price of an achromat
      of the same aperture; ED glass removes almost all visible colour and allows
      much faster focal ratios (f/6&ndash;f/7).</li>
  <li><b>APO triplet (ED/fluorite)</b> &mdash; the most expensive (three exotic
      air-spaced elements); essentially colour-free and the imager's choice, but you
      pay steeply for that last factor of a few &mdash; diminishing returns for
      visual use.</li>
</ul>
<p>Because glass gets heavy and dear with aperture, APOs are usually small
(&le;150 mm) &mdash; for big apertures a mirror (no chromatic aberration at all) is
far cheaper, which is why large scopes are reflectors.</p>

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

<h3>Reading the ray fan (aberration signatures)</h3>
<p>The Spherical Aberration scenario's ray fan plots the <b>transverse ray
error &Delta;x</b> &mdash; where a ray lands at the focal plane relative to the
ideal focus, measured across the optical axis &mdash; against the ray's pupil
entry height <i>h</i>. The <b>shape</b> of that &Delta;x(h) curve identifies the
aberration:</p>
<ul>
<li><b>Spherical aberration</b> &mdash; cubic, &Delta;x &prop; h&sup3; (an
S-shape): outer-zone rays miss most.</li>
<li><b>Coma</b> &mdash; quadratic, &Delta;x &prop; h&sup2; (a U-shape); an
off-axis aberration (see &sect;5).</li>
<li><b>Defocus</b> &mdash; <i>linear</i>, &Delta;x &prop; h: the image plane is
simply at the wrong distance, so every zone is displaced in proportion to h.
Not a lens fault &mdash; it is what refocusing corrects.</li>
<li><b>Tilt</b> &mdash; <i>constant</i>, &Delta;x independent of h: the whole
bundle is shifted sideways (e.g. a misaligned/decentred element or an off-axis
chief ray). Shifts the image without blurring it.</li>
<li><b>Diffraction-limited</b> &mdash; &Delta;x &asymp; 0 at every h: geometric
errors are below the diffraction limit.</li>
</ul>
<p>Defocus and tilt are the two lowest-order terms &mdash; a real wavefront is a
sum of these plus the higher-order aberrations above; the ray-fan curve shape is
how you tell them apart.</p>

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

DETECTOR_VS_EYE_HTML = """
<p>The tutorial shows most images two ways &mdash; a <b>Detector</b> view and an
<b>Eye</b> view &mdash; because a camera sensor and the human eye respond to
light in fundamentally different ways.</p>

<h3>Detector: linear</h3>
<p>A CCD/CMOS pixel counts photons. Its output is <b>proportional</b> to the
light collected: twice the photons &rarr; twice the signal, until the pixel
fills up (<b>saturation</b> / full-well) and clips to white, or drops into the
read/shot <b>noise</b> floor at the faint end. The span between those two is the
detector's <b>dynamic range</b>. A single linear exposure can only capture a
scene whose range fits inside it.</p>

<h3>Eye: logarithmic</h3>
<p>The eye's <i>perceived</i> brightness grows roughly as the <b>logarithm</b>
of the light flux. This compresses an enormous physical range (full sunlight to
the faintest visible star spans a factor of &sim;10<sup>14</sup>) into a
comfortable perceptual range &mdash; a built-in "HDR". It is why you can see a
bright and a faint star in the same field at once, where a linear detector
cannot.</p>

<h3>Evidence that the eye is logarithmic</h3>
<ul>
<li><b>Weber&ndash;Fechner law</b> (E. Weber 1834; G. Fechner 1860): the
smallest detectable change in a stimulus is proportional to the stimulus itself
(&Delta;I/I &asymp; constant). Integrating that relationship gives
<i>perception &prop; log(intensity)</i> &mdash; the classic result for vision,
hearing, and other senses.</li>
<li><b>The astronomical magnitude scale.</b> Hipparchus (&sim;150&nbsp;BC)
ranked naked-eye stars from 1 (brightest) to 6 (faintest) purely <i>by eye</i>,
in what felt like equal steps. In 1856 Norman <b>Pogson</b> measured that a
1st-magnitude star is about <b>100&times;</b> brighter in flux than a
6th-magnitude one &mdash; so each equal-<i>perceived</i> step of one magnitude is
a fixed <i>multiplicative</i> flux ratio of 100<sup>1/5</sup> &approx;
<b>2.512&times;</b>. Equal perceptual steps mapping to equal flux <i>ratios</i>
is exactly a logarithmic response:</li>
</ul>
<p style="font-family:monospace; margin-left:20px;">
m = &minus;2.5 log<sub>10</sub>(F / F<sub>0</sub>)</p>
<p>In the tutorial, the <b>Detector (linear)</b> view maps pixel value straight
to screen brightness; the <b>Eye (log)</b> view applies an <code>asinh</code>
stretch (a smooth curve that is logarithmic for bright values and linear near
zero, avoiding a singularity at black) to mimic this response.</p>

<h3>Eye resolution &amp; spatial integration</h3>
<p>Brightness response is only half the story: the eye also has a finite
<b>spatial resolution</b>. The naked eye resolves &sim;1 arcminute; at a moderate
eyepiece magnification the eye's grain projects to roughly <b>1&Prime;</b> on the
sky. The eye <i>integrates</i> light over that small patch, softening fine
structure (and blending the colours of a chromatic blur disk into the perceived
core). This is a separate effect from the logarithmic <i>intensity</i> response.
The <b>Eye + integration</b> view (and the "Eye blur" toggle) adds this &sim;1&Prime;
spatial blur, so together the two Eye modes model <i>both</i> how the eye maps
brightness (log) <i>and</i> how it resolves detail (finite grain) &mdash; which
is why a diffraction-limited detector image can look sharper than the same scene
does to the eye at the eyepiece.</p>
<p>This makes the eye a <b>third resolution limit</b>, alongside aperture
diffraction and atmospheric seeing (see the <i>Aperture vs Seeing</i> module).
Whichever is <i>largest</i> dominates: a big aperture beats its own diffraction
limit but is still capped by the seeing disk, and at low magnification the eye's
&sim;1&Prime; grain can be the coarsest limit of all. The eye also integrates in
<i>time</i> (&sim;0.1&nbsp;s), so it averages the fast atmospheric fluctuations
and &mdash; unlike a long exposure that smears them into one fat blur &mdash;
lets an observer catch the fleeting moments of steady air when detail snaps into
view.</p>
<p><i>Accuracy: perceptual model. The asinh stretch and 1&Prime; integration are
qualitative stand-ins for human vision, not calibrated psychophysics; they
convey the linear-vs-log and finite-resolution distinctions, not exact retinal
response.</i></p>
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


# Realism audit (R3.3): things that ARE modelled, but approximately — with an
# honest note on why the shortcut is taken and what a higher-fidelity version
# would require. Sometimes less realism is deliberate, to isolate one effect.
REALISM_AUDIT_HTML = """
<p>Everything below <b>is</b> modelled, but with a simplification. Each entry
says what the shortcut is, why it's acceptable (often: to isolate one teaching
effect, or because the exact version is disproportionately hard), and what a
higher-fidelity upgrade would take.</p>

<h3>Eye-mode diffraction rings look too obvious</h3>
<p>Good catch if you noticed this. The Eye view uses an <b>asinh</b> (log-like)
stretch with a very low linear floor (a&nbsp;=&nbsp;0.001) to lift faint
structure. That floor is aggressive: the Airy pattern's 1st ring is only
<b>1.7%</b> of the peak in raw flux, but the stretch renders it at <b>~47%</b>
brightness (2nd ring 0.4%&rarr;28%, 3rd 0.16%&rarr;16%). So the rings show far
more prominently than a real observer sees them &mdash; visually you catch the
first ring (sometimes the second) on a <i>bright</i> star only in <i>excellent</i>
seeing; the higher rings are washed out by the atmosphere and your eye's real
contrast threshold. <i>Accepted</i> because it makes the diffraction structure
legible for teaching. <i>To improve:</i> raise the asinh floor toward the eye's
true ~1% contrast threshold and gate ring visibility on the seeing value.</p>

<h3>Atmospheric seeing = a Gaussian blur</h3>
<p>Real seeing is a rapidly boiling speckle pattern (Kolmogorov turbulence); we
convolve with a fixed Gaussian of the stated FWHM. <i>Accepted</i> &mdash; it
captures the time-averaged resolution loss, which is the lesson.
<i>To improve:</i> simulate a time-varying phase screen and average many
short exposures (a genuine speckle model).</p>

<h3>Aberrations = geometric / 3rd-order Seidel</h3>
<p>Coma, spherical and defocus come from the Seidel formulae or geometric ray
offsets, shown as ray fans and spot diagrams &mdash; not from a diffraction
(wavefront) PSF. <i>Accepted</i>: the ray-fan <i>signature</i> (cubic = SA,
parabola = coma) is exactly what these views teach, and near the diffraction
limit the geometric blur is correctly small. <i>To improve:</i> build the PSF
from the aberrated wavefront (Zernike &rarr; FFT) so aberration and diffraction
interfere realistically.</p>

<h3>Planet &amp; Moon surfaces</h3>
<p>The Moon uses a real NASA/LRO albedo map; Jupiter and Saturn are
<b>procedural</b> (parametric belts, Great Red Spot, rings) rather than
photographs. <i>Accepted</i> &mdash; a procedural disk stays honest under any
zoom, phase and libration without baking in one photo's lighting/projection,
and it renders at any resolution for the PSF convolution. <i>To improve:</i>
map real spacecraft imagery (Cassini/Juno/Hubble) the way the Moon already does.</p>

<h3>Colour = 3 channels, not a spectrum</h3>
<p>Rendering carries R/G/B at the Fraunhofer C/d/F wavelengths; filters
point-sample their transmission at those three points. <i>Accepted</i> for
qualitative colour and filter contrast. <i>To improve:</i> render many
wavelength bins and integrate against real detector/eye response curves.</p>

<h3>No atmospheric dispersion</h3>
<p>Low-altitude objects show a real vertical red&ndash;blue colour smear from
the atmosphere acting as a weak prism; we don't model it (targets are treated as
near the zenith). <i>To improve:</i> add a dispersion offset per channel as a
function of target altitude.</p>

<h3>Perceptual eye model</h3>
<p>The Eye view (asinh brightness + ~1&prime; spatial integration + cone
desaturation) is a <i>qualitative</i> stand-in for human vision, not calibrated
psychophysics, and magnification is not modelled (the view is a fixed angular
scale). <i>Accepted</i> &mdash; it conveys linear-vs-log and finite-resolution
distinctions. <i>To improve:</i> a calibrated luminance/contrast model plus an
explicit eyepiece magnification stage.</p>

<h3>Vignetting = secondary-only</h3>
<p>Only the beam sliding off the secondary mirror is modelled (a
circle&ndash;circle overlap). Tube, focuser-drawtube and undersized-diagonal
vignetting are ignored. <i>To improve:</i> add each aperture stop along the beam
and intersect them all.</p>
"""


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------

VIGNETTING_DIAGRAM_CAPTION_HTML = (
    "<p>The <b>secondary clear aperture</b> is simply the reflective face of "
    "the secondary (diagonal) mirror &mdash; the patch of mirror the "
    "converging beam has to land on to be relayed out to the eyepiece. It is "
    "<i>not</i> the shadow the secondary casts on the incoming light (that's "
    "the central obstruction, a separate thing); here it acts like a stop the "
    "cone must pass through.</p>"
    "<p>Left panel: light from the <b>&#9733; off-axis star (the source, top "
    "left)</b> arrives as parallel rays travelling down-right, reflects off the "
    "primary, and converges toward the <b>&#9711; prime focus (the circle)</b>. "
    "Because the star is off-axis, that converging cone arrives at the secondary "
    "shifted sideways. The rays that <b>land on the mirror face are caught</b> "
    "(green &mdash; they stop there because the mirror relays them out to the "
    "eyepiece); the rays that <b>miss the mirror carry on to the prime focus</b> "
    "(red) and are <b>lost</b>, so the star is dimmed. The right panel is the "
    "same effect face-on: the circular beam footprint slides off the circular "
    "mirror face, and the non-overlapping sliver is the vignetted light (the "
    "<i>circle&ndash;circle overlap</i> model the simulation uses).</p>"
    "<p style='font-family:monospace; margin-left:20px;'>"
    "Fully-illuminated field &theta;<sub>fif</sub> = (r<sub>sec</sub> "
    "&minus; r<sub>beam</sub>) / d<sub>sec</sub> &times; 206265&Prime;</p>"
    "<p>Inside &theta;<sub>fif</sub> illumination is 100%; beyond it the "
    "overlap fraction &mdash; and the illumination &mdash; falls smoothly "
    "toward the 50% edge.</p>"
    "<p><b>Vignetting vs central obstruction &mdash; the secondary's two jobs.</b> "
    "The <i>same</i> secondary mirror both (1) must be big enough to <b>catch</b> "
    "the converging cone (small &rArr; off-axis vignetting) and (2) sits in the "
    "incoming beam and <b>blocks</b> its centre (big &rArr; larger central "
    "obstruction, which lowers on-axis contrast/Strehl). So they pull opposite "
    "ways: enlarging the secondary reduces vignetting but worsens the "
    "obstruction. Different rays are involved &mdash; obstruction removes the "
    "<i>central</i> rays of every beam (the mirror's shadow); vignetting removes "
    "the <i>edge</i> rays of an <i>off-axis</i> beam (the ones that slide past "
    "the mirror). Designers pick the secondary size to balance the two for the "
    "intended use.</p>"
    "<p><b>When is vignetting actually observable?</b> For a normally-sized "
    "secondary &theta;<sub>fif</sub> is huge &mdash; a 200&nbsp;mm f/4 Newtonian "
    "is fully illuminated out to roughly 75&prime;, far beyond a high-power "
    "visual field, so you never see it there (that's why the Star Field Showcase "
    "shows none). You DO see it in: <b>fast wide-field astrographs</b> (f/4 and "
    "faster) where a large camera sensor reaches past &theta;<sub>fif</sub> and "
    "the corners darken; <b>visual-optimised Newtonians</b> given a deliberately "
    "<i>undersized</i> secondary (to shrink the obstruction) then used for "
    "imaging; and scopes with an undersized diagonal, focuser drawtube or "
    "baffle. It shows up as corner-darkening on wide fields / large sensors, not "
    "on a small high-power field. (Tube/focuser vignetting is not modelled.)</p>"
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

    axA.set_title("Side view (schematic): off-axis light\n"
                  "clipped by the secondary", fontsize=9)
    # Primary mirror at the bottom.
    axA.plot([-D / 2, D / 2], [0, 0], color="black", lw=3, solid_capstyle="butt")
    axA.text(0, -0.28, "Primary mirror (aperture D)", ha="center",
             va="top", fontsize=7.5)

    # Secondary mirror face (grey bar) at y_sec, seen edge-on.
    axA.plot([-sec_half, sec_half], [y_sec, y_sec], color="0.25", lw=7,
             solid_capstyle="butt", zorder=4)
    axA.annotate(
        "secondary mirror face\n(“clear aperture”)",
        xy=(-sec_half, y_sec), xytext=(-D / 2 - 1.9, y_sec + 0.9),
        ha="left", va="center", fontsize=6.6, color="0.25",
        arrowprops=dict(arrowstyle="->", color="0.4", lw=0.8))

    # R4.6: SOURCE star (top-left) → light arrives from the upper-left as
    # PARALLEL rays (an off-axis star). Draw a few incoming parallel rays down
    # to the primary so the direction of travel is explicit.
    dx = 0.5                          # focus shift for this off-axis angle
    star_xy = (-D / 2 - 1.15, F + 0.15)
    axA.plot(*star_xy, marker="*", color="#e08a2b", ms=15, zorder=6)
    axA.text(star_xy[0], star_xy[1] + 0.32,
             "off-axis star\n(light source)", ha="center", va="bottom",
             fontsize=6.8, color="#a9631a")
    in_slope = 0.42                   # incoming tilt (from upper-left)
    for x_prim in np.linspace(-D / 2, D / 2, 3):
        x_top = x_prim - in_slope * (F * 0.42)
        axA.annotate("", xy=(x_prim, 0.02), xytext=(x_top, F * 0.42),
                     arrowprops=dict(arrowstyle="-|>", color="#e0a060",
                                     lw=0.8, alpha=0.7))

    # Converging beam after the primary → toward the off-axis focus (dx, F).
    # R4.6c INVERT: the SUCCESSFUL (caught) rays STOP at the secondary face
    # (they are reflected out to the eyepiece); the MISSED rays continue on to
    # the prime focus (a CIRCLE, R4.6a) — that light is lost.
    caught_any = missed_any = False
    for x0 in np.linspace(-D / 2, D / 2, 7):
        x_at_sec = x0 + (dx - x0) * (y_sec / F)
        if abs(x_at_sec) <= sec_half:            # lands on the mirror → caught
            axA.plot([x0, x_at_sec], [0, y_sec], color="#2f9e44", lw=1.1,
                     zorder=3)
            caught_any = True
        else:                                    # misses → continues to focus
            axA.plot([x0, dx], [0, F], color="#d0342b", lw=1.2, alpha=0.9,
                     zorder=2)
            missed_any = True
    # Convergence point = an open CIRCLE (not a star).
    axA.plot(dx, F, marker="o", markerfacecolor="none",
             markeredgecolor="#a11", ms=11, mew=1.6, zorder=6)
    axA.text(dx + 0.15, F + 0.05, "prime focus\n(missed rays\nconverge → lost)",
             ha="left", va="center", fontsize=6.6, color="#a11")
    if caught_any:
        axA.annotate("caught → stop at the\nsecondary (→ eyepiece)",
                     xy=(0.0, y_sec), xytext=(-D / 2 - 1.5, y_sec - 1.0),
                     fontsize=6.6, color="#2f7a34", ha="left",
                     arrowprops=dict(arrowstyle="->", color="#2f9e44", lw=0.9))
    axA.set_xlim(-D / 2 - 1.9, D / 2 + 1.4)
    axA.set_ylim(-0.6, F + 0.9)
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
    axB.text(0, -r_sec - 0.18, "secondary mirror face\n(“clear aperture”)",
             ha="center", va="top", fontsize=7.5, color="0.3")
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


# ---------------------------------------------------------------------------
# Section anchors — deep links from the Tutorial tab's "Learn more" line
# ---------------------------------------------------------------------------
# Every tutorial scenario carries a `learn_more_section` hint ("Coma",
# "Spider Vanes", "Photometry & Filters", ...). Those strings are written for
# humans, so they rarely match a heading character-for-character: reference
# headings are numbered ("5. Coma & Seidel Aberrations") and often shift
# number ("Spider Vanes" vs "Spider Vane Diffraction"). Instead of a
# hand-written alias table that silently rots as headings are edited, each
# heading is normalised to a token tuple and matched by token overlap.
# tests/test_gui_controls.py asserts that *every* learn_more_section in the
# scenario registry resolves to a real anchor, so an unmatched hint fails the
# suite rather than producing a dead link.

_H3_SPLIT_RE = re.compile(r"(?=^<h3>)", re.MULTILINE)
_H3_TITLE_RE = re.compile(r"\A<h3>(.*?)</h3>", re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_LEADING_NUMBER_RE = re.compile(r"^\s*\d+[.)]\s*")


def _section_tokens(name: str) -> tuple[str, ...]:
    """Normalise a section name (or heading) to comparable tokens.

    Strips markup and entities, drops any leading "4." numbering, lowercases,
    and crudely de-pluralises so "Spider Vanes" and "Spider Vane Diffraction"
    share tokens. Both sides of a comparison go through this, so the
    de-pluralisation only has to be *consistent*, not linguistically right.
    """
    text = html_lib.unescape(_TAG_RE.sub("", name))
    text = _LEADING_NUMBER_RE.sub("", text).lower()
    return tuple(
        tok[:-1] if len(tok) > 3 and tok.endswith("s") else tok
        for tok in re.findall(r"[a-z0-9]+", text)
    )


def _match_anchor(name: str, anchors: list) -> QWidget | None:
    """Pick the anchor widget that best matches a `learn_more_section` hint.

    `anchors` holds (tokens, is_numbered, widget) records. Candidates must
    contain every query token; among those the ranking prefers, in order:
    an exact heading match, a match at the *start* of the heading, then a
    numbered physics heading. That ordering is what makes "Diffraction" land
    on "1. Diffraction (Wave Optics)" rather than "3. Spider Vane
    Diffraction" (prefix), and "Coma" land on "5. Coma & Seidel Aberrations"
    rather than the "Coma Field Analysis" plot description (numbered).
    """
    query = _section_tokens(name)
    if not query:
        return None
    best, best_score = None, None
    for tokens, is_numbered, widget in anchors:
        if not all(tok in tokens for tok in query):
            continue
        score = (
            tokens == query,                       # exact heading
            tokens[:len(query)] == query,          # heading starts with hint
            is_numbered,                           # numbered physics section
            -len(tokens),                          # fewest extra words
        )
        if best_score is None or score > best_score:
            best, best_score = widget, score
    return best


def _register_anchor(anchors, name: str, widget: QWidget) -> None:
    """Record `widget` as the scroll target for a heading/section name."""
    if anchors is None:
        return
    is_numbered = bool(_LEADING_NUMBER_RE.match(_TAG_RE.sub("", name).strip()))
    anchors.append((_section_tokens(name), is_numbered, widget))


_GROUPBOX_STYLE = (
    "QGroupBox { font-weight: bold; font-size: 13px; "
    "margin-top: 18px; padding: 24px 8px 8px 8px; "
    "border: 1px solid palette(mid); border-radius: 4px; }"
    "QGroupBox::title { subcontrol-origin: margin; "
    "subcontrol-position: top left; padding: 4px 8px; "
    "background: palette(window); }"
)


def _make_rich_label(html: str) -> QLabel:
    """A word-wrapped, selectable rich-text label in the body style."""
    label = QLabel(html)
    label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.RichText)
    label.setStyleSheet("QLabel { font-weight: normal; }")
    label.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse
    )
    return label


def _make_figure_section(title: str, fig, caption_html: str,
                         anchors: list | None = None) -> QGroupBox:
    """Section with a rendered matplotlib figure above a rich-text caption."""
    box = QGroupBox(title)
    box.setStyleSheet(_GROUPBOX_STYLE)
    _register_anchor(anchors, title, box)
    layout = QVBoxLayout()
    img = QLabel()
    img.setPixmap(_figure_to_pixmap(fig))
    img.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    layout.addWidget(img)
    layout.addWidget(_make_rich_label(caption_html))
    box.setLayout(layout)
    return box


def _make_section(title: str, html: str,
                  anchors: list | None = None) -> QGroupBox:
    """Create a styled QGroupBox with rich-text content.

    The body is split at each top-level ``<h3>`` into its own QLabel so every
    subsection is an addressable widget the tutorial's "Learn more" link can
    scroll to; rendering is otherwise identical to one monolithic label.
    """
    box = QGroupBox(title)
    box.setStyleSheet(_GROUPBOX_STYLE)
    _register_anchor(anchors, title, box)

    layout = QVBoxLayout()
    # Qt drops a block's top margin when it starts a rich-text document, so
    # splitting costs each <h3> its leading gap; the layout spacing puts it
    # back (measured: restores the pre-split page height to within 0.3%).
    layout.setSpacing(10)
    for chunk in _H3_SPLIT_RE.split(html):
        if not chunk.strip():
            continue
        label = _make_rich_label(chunk)
        layout.addWidget(label)
        heading = _H3_TITLE_RE.match(chunk)
        if heading:
            _register_anchor(anchors, heading.group(1), label)
    box.setLayout(layout)
    return box


class ParametersPhysicsTab(QWidget):
    """Read-only reference tab documenting telescope parameters and physics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # (tokens, is_numbered, widget) per addressable heading; see
        # _match_anchor / scroll_to_section.
        self._anchors: list = []
        self._scroll = None
        self._init_ui()

    def _init_ui(self):
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._scroll = scroll

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
        anchors = self._anchors
        layout.addWidget(_make_section(
            "Telescope Types", TELESCOPE_TYPES_HTML, anchors))
        layout.addWidget(_make_section(
            "Telescope Parameters", PARAMETERS_HTML, anchors))
        layout.addWidget(_make_section(
            "Understanding the Plots", PLOTS_HTML, anchors))
        layout.addWidget(_make_section(
            "Detector vs Eye (linear vs logarithmic)", DETECTOR_VS_EYE_HTML,
            anchors))
        layout.addWidget(_make_figure_section(
            "Vignetting (diagram)", _build_vignetting_diagram(),
            VIGNETTING_DIAGRAM_CAPTION_HTML, anchors))
        layout.addWidget(_make_section(
            "Implemented Physics", PHYSICS_HTML, anchors
        ))
        layout.addWidget(_make_section(
            "Realism audit — approximations & how to improve them",
            REALISM_AUDIT_HTML, anchors
        ))
        layout.addWidget(_make_section(
            "Not Yet Implemented", NOT_IMPLEMENTED_HTML, anchors
        ))

        layout.addStretch()
        container.setLayout(layout)
        scroll.setWidget(container)

        outer.addWidget(scroll)
        self.setLayout(outer)

    # ------------------------------------------------------------------
    # Deep linking (Tutorial tab "Learn more →" line)
    # ------------------------------------------------------------------

    def resolve_section(self, name: str) -> QWidget | None:
        """Widget a `learn_more_section` hint points at, or None if unmatched."""
        return _match_anchor(name, self._anchors)

    def scroll_to_section(self, name: str) -> bool:
        """Scroll the reference so `name`'s heading sits at the top of view.

        Returns False (leaving the view alone) when the hint matches nothing,
        so a caller can tell a dead link from a successful jump.
        """
        widget = self.resolve_section(name)
        container = self._scroll.widget() if self._scroll else None
        if widget is None or container is None:
            return False
        top = widget.mapTo(container, QPoint(0, 0)).y()
        bar = self._scroll.verticalScrollBar()
        # Back off a little so the heading isn't flush against the viewport
        # edge (and clamp: short sections near the end can't scroll that far).
        bar.setValue(max(0, min(top - 8, bar.maximum())))
        return True

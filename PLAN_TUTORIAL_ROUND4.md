# Tutorial Tab — Round 4 feedback ledger

**Branch:** `feature/tutorial-testing-tab` (Round 3 complete at commit c94a45b).
**Rule (same as Round 3):** record every item verbatim; do NOT paraphrase away or
mark DONE without canvas-pipeline verification through the REAL GUI navigation.
Status: ⬜ open · 🔧 in progress · ✅ done+verified · ❓ needs decision/answer.

---

## Verbatim feedback (2026-07-18)

### R4.1 — Airy disc (2D mode)
> "Make sure the left plot in 2d mode is clearly labeled 'Reference' to make it
> clear why there are two figures."
- ✅ (a) Airy before_label → "Reference — 200 mm aperture".

### R4.2 — Rayleigh criterion
> "also describe the spatial integration when it is used in the legend describing
> the image processing (i.e., along with exposure = N/A). It also doesn't seem like
> the brightness is scaling with aperture as the legend describes. As I look at
> this, perhaps actually we should add a new module to introduce eye vs detector
> view. What do you think about this? Perhaps we should bring the exposure
> saturation up and recast it from exposure/saturation to viewing modes or
> something like that."
- ✅ (a) Eye-view annotation now adds "+ ~1″ eye spatial integration (finite eye
  resolution)" whenever the eye-blur (log_integrated) mode is active, alongside
  "exposure N/A".
- ✅ (b) Root cause: a mag-0 star saturates even at 100 mm, so the ∝aperture²
  scaling is clipped away (it looks the same at every aperture). Annotation now
  says "star brightness ∝ aperture² (until it saturates)". (Deeper reframe lands
  with the viewing-modes module, D1.)
- ✅ (c) DONE per D1. Recast the exposure/saturation module into "Viewing Modes:
  Detector vs Eye" and MOVED it to Act 1, right after Airy disc (it already showed
  Eye-left/Detector-right, so it absorbs exposure/saturation cleanly). Description
  reframed as the foundational intro (START HERE; why detector=linear vs
  eye=logarithmic; aperture shared, exposure detector-only). learn_more links the
  P&P Detector-vs-Eye section. Act 1 now 8 modules, Act 3 now 3. Verified sidebar
  order airy_disk → viewing_modes → rayleigh …; both panes render; eye-blur toggle
  present.

### R4.3 — Central obstruction (1D mode)
> "when it converts to 1d mode the figure titles should be changed- instead of No
> obstruction and With obstruction, they should be labeled with the normalization
> basis for each plot. The legend labels are good there but now cover up the
> formulas."
- ✅ (a) 1D obstruction plot title is now the per-side normalisation basis
  ("Normalised to each own peak → SHAPE" / "Obstructed scaled to Strehl → PEAK
  loss") + the blue/red colour key; cleared the colliding "PSF" suptitle.
- ✅ (b) Folded the colour key into the title and REMOVED the separate legend, so
  nothing covers the side-panel formulas.

### R4.4 — Formulas (general, cross-cutting)
> "More generally with formulas we should make sure that the variables are clear,
> and that we have the appropriate formulas (only) for the module in question. For
> example Airy disc seems to have Strehl/obstruction formulas that don't belong
> there."
- ✅ (a) Added variable keys to formulas (Airy: λ,D,N; obstruction: ε,S).
- ✅ (b) **FIXED in Round 5, Batch P.** The earlier "could not reproduce" was wrong,
  not stale: it checked the overlay and the theory readout, where Strehl *is*
  correctly scoped to central_obstruction. The offending text is in the figure's own
  metrics/formula panel — `plot_psf_profile` printed `Strehl ≈ {strehl:.3f}` and the
  Marechal formula `Strehl ≈ 1/(1+(πσ/2r₁)²)` unconditionally, so a perfect parabola
  with obstruction off read "Strehl ≈ 1.000" plus a formula in σ and r₁ the module
  never introduces. Both now gated on `strehl < 0.9995`. See PLAN_TUTORIAL_ROUND5.md.

### R4.5 — Chromatic aberration
> "We still don't have the legends in the left ray trace pulled outside of the plot
> like they are supposed to be. There is a lot of white space in the canvas outside
> the plot that should be used for this. In chromatic aberration parameters and
> physics, add a note on the different types of glasses that are used, how they
> relate to the achromat vs APO designs, including how they are applied in the
> tutorial module and relative costs/performance improvement for them."
- ✅ (a) The offender was `plot_polychromatic_ray_trace` (NOT the R3.18 pupil
  trace): its "Focal offsets" readout + idealise note sat ON the narrow ray
  bundle. Moved both OUTSIDE the axes into the left/right canvas whitespace.
- ✅ (b) Chromatic P&P already had the glass-types table (singlet BK7 / achromat
  crown+flint / APO doublet ED / APO triplet fluorite + residual focal-shift);
  added how to switch them in the module and a Cost-vs-Performance section
  (~3–5× less colour per price step; why big scopes are mirrors).

### R4.6 — Vignetting (P&P diagram)
> "the physics and parameters plot and description is better, but I am still a
> little confused. The side view schematic- the stars are where the light is
> converging to, not the source right? That is confusing- it would be helpful to
> show where the light is conceptually coming from (for the off-axis is coming from
> the left and going to the right?)- use stars to show the source of the light, and
> use a circle instead of the star to show where it converges to. And actually it
> might be better to do the opposite of what you did- have the successful rays stop
> at the secondary mirror face and pass the missed rays on to the focus. Is there
> any relationship between the central obstruction and vignetting? Some relation
> between which rays get blocked vs successfully reflected? You note that in our
> case we don't really observe it, you should specify (more concretely) what
> cases/telescopes would actually have it observed in."
- ✅ (a) Panel A reworked: a STAR now marks the off-axis light SOURCE (top-left)
  and an open CIRCLE marks the prime-focus convergence.
- ✅ (b) Incoming parallel rays drawn from the star (upper-left) down to the
  primary — light travels left→right into the scope.
- ✅ (c) INVERTED: caught rays (green) STOP at the secondary face (→ eyepiece);
  missed rays (red) continue on to the prime-focus circle (lost).
- ✅ (d) Caption adds "the secondary's two jobs": bigger secondary → less
  vignetting but MORE central obstruction; obstruction removes central rays
  (its shadow), vignetting removes the edge rays of an off-axis beam.
- ✅ (e) Caption names concrete cases: fast wide-field astrographs with big
  sensors, visual-optimised Newtonians with undersized secondaries used for
  imaging, undersized diagonal/focuser/baffle — corner-darkening on wide fields.

### R4.7 — Spherical aberration
> "the left plot zoomed in inset is blank; it should also be made into a new plot
> like with chromatic aberration. Specifically, it should be made into a new plot
> in the upper right equivalent to the chromatic aberration plots. It is analogous
> right? You can use that new upper right plot to help better explain the ray fan
> then. In the ray fan, you mention defocus/tilt but this is not mentioned anywhere
> else. Am I correct? Should that aberration be mentioned somewhere? At least in
> parameter and physics?"
- ✅ (a) Removed the blank R3.8a inset (it used the raw folded-Newtonian axis-
  crossing → spurious spread even for a parabola, often blank).
- ✅ (b) New secondary `plot_spherical_focal_analysis` (top = focal-region
  CAUSTIC showing marginal rays crossing short of the paraxial ★, derived from the
  reliable ray-fan Δx(h); bottom = the ray fan). Mirrors the chromatic focal-plane
  layout and explains WHY the fan is an S-cubic. Refactored ray-fan tracing/drawing
  into shared helpers. +1 test.
- ✅ (c) Defocus + tilt are already described in P&P ("Reading the ray fan"
  subsection, R3.8b): defocus = linear Δx∝h (wrong focus distance); tilt =
  constant Δx (decentre/off-axis). Verified present.

### R4.8 — Chromatic aberration + seeing
> "the brightness is better. Is it realistic? Even the APO doublet has significant
> color fringing; I would think the APO doublet would be approaching no observable
> artifacts more. For APO triplet the stars actually have non-uniform coloring, and
> with eye view they all appear larger than detector. Is that right? The legend in
> the upper left partially covers up the upper left star so you can move all stars
> slightly lower on the plot."
- ✅ (a) The APO residuals were too loose: doublet f/8000 gave a ~3×-Airy halo.
  Tightened to f/16000 (~1.5× Airy) → faint halo only on the brightest stars,
  "approaching no observable artifacts". Verified: per-channel spread [925,113,657]
  → [310,113,207]. P&P table + text updated to match.
- ✅ (b) APO triplet f/20000 left R/B ~2× the green core (green-cored stars).
  Tightened to f/45000 (~0.55× Airy, BELOW diffraction) → colour-free, channels
  near-equal [160,113,121]; green cores gone (verified in a 3-objective render).
  The "eye view larger than detector" is EXPECTED — the eye's asinh log response
  reveals the faint PSF wings/halo the linear detector clips to black, so a bright
  star genuinely bloats to the eye; the magnitude is exaggerated by the aggressive
  asinh floor, already documented in the R3.3a realism-audit. +1 test.
- ✅ (c) MultiColorStarField y-positions shifted down ~6″ so the top row clears
  the upper-left labels/info box.

### R4.9 — Aperture vs seeing
> "this is better. Make sure you label the left plot as the reference with both
> effects. On the right, when you turn off both blurring effects the star
> disappears, there should presumably still be a very bright dot right?"
- ✅ (a) aperture_vs_seeing before_label → "Reference — both effects + limit overlays".
- ✅ (b) The ideal point (aperture off, no seeing) now renders as a small VISIBLE
  Gaussian dot (~45 px, flux-preserved) instead of a single invisible pixel —
  still far sharper than the Airy/seeing disk. (R4.9a label pending in Batch H.)

### R4.10 — F/ratio and coma
> "the two plots on the left have their x-axis labels overlapping the gray
> description below them. You can make these two plots shorter (less vertical
> extent) to make more room for the grey descriptions under them."
- ✅ (a) Coma gridspec given bottom=0.22/top=0.9 → panels are shorter, the grey
  caption sits clear below the x-axis labels.

### R4.11 — ND filter on the Moon
> "the ND-2.0 filter basically makes the moon completely dark – this seems like too
> strong of an effect- is it correct? The exit pupil also seems to only affect the
> eye view, not detector. Is that right?"
- ✅ (a) Correct: OD 2.0 = 1% transmission, a heavy cut (visual observers use
  ND-0.9/1.0 ≈ 10–12%). Reads nearly black in the linear Detector view; the eye's
  log response keeps it visible in the Eye view. Noted in the description.
- ✅ (b) Correct: exit pupil is a visual concept (beam width at the eye); a
  detector at the focal plane collects all the light regardless, so it has no
  exit-pupil term. Explained in the description.

### R4.12 — Colour filters on Jupiter  **(REPEAT — user frustrated, no improvement seen)**
> "all my comments from before seem to still hold with no improvements: the red
> filter just makes everything look red. The left Jupiter plot also appears to be
> sort of more artificially colored now, with the great red spot being almost
> highlighter orange color- it is that that is concerning, that the original image
> is messed up, not that the filter isn't working. Re-review that the filters are
> doing what they are supposed to, that the module is appropriately designed to
> show the effect (the red filter does not appear to be showing anything), and that
> planetary and lunar objects are being implanted correctly/well with their
> original basis definition."
- ✅ (a) FIXED at the root: replaced the procedural Jupiter with a REAL bundled
  cylindrical photo-map (jupiter_2k.jpg, CC BY 4.0) projected onto an oblate globe
  like the Moon. The GRS is now a natural pale salmon (rendered saturation 0.39 vs
  the old 0.49 "highlighter"); no procedural palette. Whitewash also fixed:
  default exposure 0.4→0.3 drops the blown-white fraction 0.40→0.02.
- ✅ (b) With the real texture + 0.3 exposure the module reads correctly — blue
  (W80A) pops the belts, red (W25) is the uniform low-contrast disk (correct
  physics, already reframed in R3.14). Verified in a 6-panel render.
- ✅ (c) Planetary construction reworked to the real photographic basis: Jupiter
  and Saturn globes now project real maps (shared `_project_globe`/`_sample_equirect`
  helpers, refactored out of the Moon so all three share ONE honest implementation).
  Saturn keeps its detailed procedural rings (Cassini/Encke/shadow). +3 tests.

### R4.13 — Bright + dim: dynamic range
> "The eye view on the right appears to have a boxed outline artificially making
> square images."
- ✅ (a) Root cause: the seeing blur used a full-image SQUARE Gaussian kernel via
  FFT; its truncated corners are tiny but the eye's asinh stretch lifted them into
  a faint box around bright stars. Switched to `scipy.ndimage.gaussian_filter`
  (separable, no square footprint) — stars stay round. Verified before/after.

### R4.14 — Saturn brightness
> "we see brightness issues again. There appears to be a step change in brightness
> between 885 and 890 mm aperture (with no seeing); on either side of this the
> brightness does not appear to change as a function of aperture. Note that some
> factors are not expected to show a noticeable result here."
- ✅ (a) Root cause: the extended-source downsample SUM-binned only when the
  internal render was ≥2× the display (bin_factor≥2). Below the threshold no
  binning ran; at 890 mm the render hit 1024 px = 2×512 → 2×2 sum = ×4 flux, a
  +0.036 brightness STEP. Switched to MEAN-binning (surface brightness is
  aperture-invariant for a resolved object) → step drops to +0.001; flat vs
  aperture as expected. Defaults (bin_factor 1) unchanged.

### R4.15 — Star field brightness / colours
> "are these colors realistic? They seem very pronounced."
- ✅ (a) Desaturated the spectral palette toward white (`_TINT_STRENGTH=0.45`):
  real stars show only subtle colour to the eye. ShowcaseStarField per-star
  saturation dropped mean 0.16→0.07, max 0.60→0.27 — the field now reads as gently
  tinted (mostly white with subtle blue/orange), not garish. Verified render.

---

## Diagnosis (2026-07-18)

- **R4.12 (Jupiter GRS) ROOT CAUSE:** the R3.14 base mute [188,122,100] IS applied,
  but the extended-source render normalises the disk peak toward saturation, so the
  GRS renders as [0.99, 0.72, 0.5] — a vivid "highlighter orange" (saturation ~0.49
  survives, brightness pushes it vivid). The zones also blow to pure white. So the
  fix must reduce the texture SATURATION much more AND/OR tame the whitewashing
  brightness normalisation — the base-colour mute alone can't win. Also revisit
  whether the procedural texture reads "artificial" regardless (→ decision).
- **R4.14 (Saturn step) ROOT CAUSE FOUND:** `bin_factor = num_pixels //
  display_num_pixels`. Below D≈890 mm the effective render is ~1018 px → bin_factor
  1 → NO binning; at D=890 it hits exactly 1024 px → bin_factor 2 → **sum**-bins 2×2
  = ×4 flux. Since the texture is per-pixel surface brightness, summing quadruples
  it → +0.036 brightness step at 890 mm, flat elsewhere. Fix: **mean-bin** (average)
  instead of sum-bin → surface brightness invariant to render resolution → no step.
  Defaults (bin_factor 1) are unchanged. User's "flat on either side is expected" is
  correct (surface brightness is aperture-independent); only the step is the bug.
- **R4.11a (ND-2.0 Moon):** detector/linear → mean 0.10, max 0.15 (dim but not black;
  ~correct for 1% transmission on a near-saturated Moon). eye/log → 0.68 (bright). The
  weak "detail emerges" story at exposure 1.0 is because the Moon isn't saturated
  enough to benefit — ties into the viewing-modes/exposure rework.
- **R4.11b (exit pupil):** confirmed — exit pupil changes ONLY the eye (log) view,
  not the detector (linear). This is CORRECT physics (exit pupil is a visual/eye
  concept; a detector integrates all focal-plane light regardless). Needs a NOTE,
  not a code fix.
- **R4.9b (aperture both-off):** confirmed — the ideal point is a single pixel
  (invisible at display scale). Fix: render the "no-diffraction" point as a small
  visible bright dot (a few px), not 1 px.
- **R4.7a (spherical inset blank):** the pupil ray trace has only 2 axes (trace +
  colorbar) — the R3.8a focal-zoom inset isn't present/populated here → blank.
  R4.7b wants it removed and promoted to a proper UPPER-RIGHT secondary plot, like
  chromatic's focal-plane zoom. → restructure spherical to mirror chromatic.
- **R4.5a (chromatic ray-trace legend):** chromatic uses `plot_polychromatic_ray_
  trace` (NOT the pupil-trace fixed in R3.18). Its legend is still an in-plot
  overlay — reverify + move out.
- **R4.3/R4.4 (obstruction 1D titles + formulas):** 1D still titled "No/With
  obstruction" (should be the per-side normalisation basis); legend now overlaps the
  formula panel; Airy-disc formula box carries Strehl/obstruction terms that don't
  belong.

## Plan — proposed batches (pending 2 decisions below)

**DECISIONS (user, 2026-07-18):**
- **D1 = new Viewing-Modes module, placed right after the Airy disc module (early,
  Act 1), and ABSORB exposure/saturation into it** (drop the separate later
  Exposure & Saturation module). The new module covers Detector-vs-Eye AND
  exposure/saturation together.
- **D2 = REAL photo-texture for Jupiter/Saturn now** (project a real cylindrical map
  like the Moon's LRO map; Saturn = real globe + keep procedural rings). User OK'd
  bundling image assets. Need to source the map image(s).

- **Batch H — quick label/legend/formula fixes:** R4.1 (Airy "Reference"), R4.9a
  (aperture-vs-seeing "Reference"), R4.3a/b (obstruction 1D titles + legend/formula
  overlap), R4.4a/b (formula variables + module-appropriate formulas; strip Strehl
  from Airy), R4.5a (chromatic legend out), R4.10 (coma panels shorter for caption),
  R4.8c (chromatic+seeing stars lower / legend off star).
- **Batch I — render/physics fixes:** R4.14 (Saturn mean-bin), R4.9b (visible ideal
  dot), R4.13 (dynamic-range square-outline artifact), R4.2b (Rayleigh brightness
  vs aperture), R4.15 (star-field colour saturation).
- **Batch J — planet texture (R4.12) + ND/exit-pupil notes (R4.11):** per D2.
- **Batch K — spherical restructure (R4.7a/b) + defocus/tilt P&P (R4.7c) + chromatic
  glass-types P&P (R4.5b) + vignetting diagram rework (R4.6a–e).**
- **Batch L — chromatic+seeing realism (R4.8a/b) + viewing-modes module (R4.2/R4.11
  reframing) per D1.**

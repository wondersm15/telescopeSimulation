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
- ⬜ (a) 2D mode: label the left plot clearly as "Reference".

### R4.2 — Rayleigh criterion
> "also describe the spatial integration when it is used in the legend describing
> the image processing (i.e., along with exposure = N/A). It also doesn't seem like
> the brightness is scaling with aperture as the legend describes. As I look at
> this, perhaps actually we should add a new module to introduce eye vs detector
> view. What do you think about this? Perhaps we should bring the exposure
> saturation up and recast it from exposure/saturation to viewing modes or
> something like that."
- ⬜ (a) Describe the spatial integration in the image-processing legend (along
  with exposure = N/A) when it is used.
- ⬜ (b) Brightness doesn't seem to scale with aperture as the legend describes —
  investigate/fix.
- ❓ (c) DESIGN QUESTION: add a new module to introduce eye vs detector view?
  Possibly promote exposure/saturation and recast it from exposure/saturation to
  "viewing modes". → needs user decision.

### R4.3 — Central obstruction (1D mode)
> "when it converts to 1d mode the figure titles should be changed- instead of No
> obstruction and With obstruction, they should be labeled with the normalization
> basis for each plot. The legend labels are good there but now cover up the
> formulas."
- ⬜ (a) 1D mode: change the figure titles from "No obstruction"/"With obstruction"
  to the NORMALIZATION BASIS for each plot.
- ⬜ (b) The legend labels now cover up the formulas — fix the overlap.

### R4.4 — Formulas (general, cross-cutting)
> "More generally with formulas we should make sure that the variables are clear,
> and that we have the appropriate formulas (only) for the module in question. For
> example Airy disc seems to have Strehl/obstruction formulas that don't belong
> there."
- ⬜ (a) Ensure formula variables are clearly defined.
- ⬜ (b) Each module shows ONLY the formulas appropriate to it (e.g. Airy disc
  wrongly shows Strehl/obstruction formulas).

### R4.5 — Chromatic aberration
> "We still don't have the legends in the left ray trace pulled outside of the plot
> like they are supposed to be. There is a lot of white space in the canvas outside
> the plot that should be used for this. In chromatic aberration parameters and
> physics, add a note on the different types of glasses that are used, how they
> relate to the achromat vs APO designs, including how they are applied in the
> tutorial module and relative costs/performance improvement for them."
- ⬜ (a) Move the left ray-trace legend OUT of the plot into canvas white space
  (STILL not done per user — reverify; may be a different ray-trace fn than the
  ones fixed in R3.18).
- ⬜ (b) Chromatic P&P: add a note on glass types, achromat vs APO designs, how
  they're applied in the module, and relative cost/performance.

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
- ⬜ (a) Side-view schematic: stars currently mark where light CONVERGES; that's
  confusing. Use STARS for the light SOURCE and a CIRCLE for the convergence point.
- ⬜ (b) Show where light comes from conceptually (off-axis from the left → right).
- ⬜ (c) INVERT the ray drawing: have the SUCCESSFUL (caught) rays stop at the
  secondary mirror face, and draw the MISSED rays continuing to the focus.
- ⬜ (d) Explain the relationship (if any) between central obstruction and
  vignetting — which rays get blocked vs successfully reflected.
- ⬜ (e) Specify CONCRETELY which cases/telescopes actually show observable
  vignetting.

### R4.7 — Spherical aberration
> "the left plot zoomed in inset is blank; it should also be made into a new plot
> like with chromatic aberration. Specifically, it should be made into a new plot
> in the upper right equivalent to the chromatic aberration plots. It is analogous
> right? You can use that new upper right plot to help better explain the ray fan
> then. In the ray fan, you mention defocus/tilt but this is not mentioned anywhere
> else. Am I correct? Should that aberration be mentioned somewhere? At least in
> parameter and physics?"
- ⬜ (a) The left-plot zoomed inset is BLANK — fix.
- ⬜ (b) Promote the inset to a NEW plot in the UPPER RIGHT, equivalent to the
  chromatic-aberration focal-zoom plots (analogous). Use it to better explain the
  ray fan.
- ⬜ (c) Ray fan mentions defocus/tilt but nowhere else — add defocus/tilt to P&P
  (at least).

### R4.8 — Chromatic aberration + seeing
> "the brightness is better. Is it realistic? Even the APO doublet has significant
> color fringing; I would think the APO doublet would be approaching no observable
> artifacts more. For APO triplet the stars actually have non-uniform coloring, and
> with eye view they all appear larger than detector. Is that right? The legend in
> the upper left partially covers up the upper left star so you can move all stars
> slightly lower on the plot."
- ⬜ (a) Is the brightness realistic? APO DOUBLET still shows significant colour
  fringing — should be closer to no observable artifacts. Re-check the doublet
  chromatic model.
- ⬜ (b) APO TRIPLET: stars have non-uniform colouring, and in eye view they all
  appear larger than in detector view. Is that correct? Investigate.
- ⬜ (c) The upper-left legend partially covers the upper-left star — move all
  stars slightly lower (or move the legend).

### R4.9 — Aperture vs seeing
> "this is better. Make sure you label the left plot as the reference with both
> effects. On the right, when you turn off both blurring effects the star
> disappears, there should presumably still be a very bright dot right?"
- ⬜ (a) Label the LEFT plot as the reference (with both effects).
- ⬜ (b) On the right, turning off BOTH blurring effects makes the star disappear;
  there should still be a bright dot (the ideal point collapses to a sub-pixel).

### R4.10 — F/ratio and coma
> "the two plots on the left have their x-axis labels overlapping the gray
> description below them. You can make these two plots shorter (less vertical
> extent) to make more room for the grey descriptions under them."
- ⬜ (a) The two left panels' x-axis labels overlap the grey caption below. Make
  the panels shorter (less vertical extent) to make room.

### R4.11 — ND filter on the Moon
> "the ND-2.0 filter basically makes the moon completely dark – this seems like too
> strong of an effect- is it correct? The exit pupil also seems to only affect the
> eye view, not detector. Is that right?"
- ⬜ (a) ND-2.0 makes the Moon completely dark — too strong? Is it correct?
- ⬜ (b) The exit pupil seems to affect only the EYE view, not the detector. Is
  that right? (explain or fix)

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
- ⬜ (a) The eye-view (right) shows a boxed/square outline artifact around images.

### R4.14 — Saturn brightness
> "we see brightness issues again. There appears to be a step change in brightness
> between 885 and 890 mm aperture (with no seeing); on either side of this the
> brightness does not appear to change as a function of aperture. Note that some
> factors are not expected to show a noticeable result here."
- ⬜ (a) Step change in Saturn brightness between 885–890 mm aperture (no seeing);
  flat on either side. Investigate the brightness-vs-aperture behaviour.

### R4.15 — Star field brightness / colours
> "are these colors realistic? They seem very pronounced."
- ⬜ (a) Star-field colours seem very pronounced — are they realistic? Re-assess
  the spectral-tint saturation.

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

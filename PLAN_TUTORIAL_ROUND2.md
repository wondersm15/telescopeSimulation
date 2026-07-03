# Plan: Tutorial Tab — Round 2 (user feedback, June 2026)

**Branch:** `feature/tutorial-testing-tab`
**Created:** 2026-06-22
**Source of truth:** the user's verbatim feedback after reviewing the
post–Phase‑1 tutorial. This document exists because that feedback was only ever
captured as a one‑line "Phases 2–5" sketch in `IMPLEMENTATION_LOG.md`; the
item‑level detail (bugs, diagnoses, answers) lived in a chat session that was
cleared. **Keep this file current as each item is diagnosed/fixed** (per the
user's standing request to keep the implementation logs updated).

Status legend: ✅ done in Phase 1 (re‑verify) · 🟡 partial · 🔴 not started ·
❓ question to answer · 🔬 needs empirical diagnosis before fixing.

---

## A. Answers to the questions you raised

These recur across several items, so they're collected here.

1. **"Should the Eye view have an exposure setting, or is exposure
   detector‑only?"** (Rayleigh, Chromatic+seeing, Exposure, etc.) — **You're
   right: exposure is detector‑only.** Exposure = integration time, which only a
   detector has; the eye has a fixed ~0.1 s integration. Phase 1.4 already
   changed this: in Eye view the exposure slider is ignored and brightness is
   optics‑driven (stars ∝ aperture²; extended objects ∝ (exit‑pupil/7 mm)²,
   capped at naked‑eye). **Remaining work:** make this obvious in the UI — grey
   out / hide the exposure slider in Eye view instead of leaving it live‑looking
   but inert (it currently only says "exposure N/A" in the annotation).

2. **"Should the singlet show spherical aberration, or remove it to show
   chromatic better?"** (Chromatic) — A real spherical singlet has *both* CA and
   SA. For a scenario whose job is to isolate **chromatic** aberration, the SA is
   a confound. **Recommendation: idealise the singlet to CA‑only, with a note**
   (same treatment already applied to the APO models). This was logged as a
   decision in Phase 1 but never implemented.

3. **"For a brightness scenario, should aperture affect brightness — or
   deactivate it?"** (ND Moon) — In **Detector** view aperture genuinely changes
   brightness (∝ collected photons), so it's not wrong. But for a scenario whose
   lesson is *the filter*, the aperture is a confound. **Recommendation: drop the
   diameter control** for `nd_filter_moon` (same call we made for the vignetting
   scenario), so the comparison is purely filter vs no‑filter.

4. **"Ray fan: shouldn't it show Δx at the focal plane (image‑plane
   misalignment) rather than the axial offset?"** (Spherical) — The standard
   *transverse ray‑fan* plots exactly what you describe: transverse ray
   aberration (image‑plane offset) vs pupil height. The S‑curve is the SA
   signature. **Action: confirm the current plot is transverse (image‑plane),
   not longitudinal (axial); fix if it's plotting the axial offset.** 🔬

5. **"Are the planets built as hi‑res + standard, or should we always start
   highest‑res and let the sim degrade?"** (Planets) — **Always start at the
   highest intrinsic resolution and let the telescope sim (PSF, seeing,
   obstruction, vignetting) degrade it** — that's the physically honest pipeline
   and avoids double‑blurring. **Action: verify the current path does this and
   isn't capping intrinsic detail.** 🔬

---

## B. Per‑item plan (in your feedback order)

### B1. Airy disc — "second pane reverted; not locked, auto‑scaled again" ✅🔬
- **Maps to:** root cause #1 → Phase 1.1 (axis lock).
- **Why it happens:** `plot_psf_2d` sets its own axis to `image_scale = 10 ×
  airy_radius`, and `airy_radius ∝ f/D`. With focal length fixed, a bigger
  aperture shrinks both the disk *and* the axis → looks identical. Phase 1.1's
  fix re‑applies the before‑side limits to the after‑side.
- **Action:** Re‑verify through the canvas pipeline that the after axis is
  actually locked to the before range when aperture changes (you saw the pre‑fix
  state). If it regressed, fix.

### B2. Rayleigh — "plot size changes w/ aperture; autoscaling; square box per star" ✅🟡🔬
- **Maps to:** axis lock (1.1), circular taper (1.3), eye‑exposure (1.4, answered).
- **Actions:** (a) Re‑verify axis stays fixed when aperture changes (aperture
  must not change FOV). (b) Re‑verify the per‑star **square‑box** artifact is
  gone (1.3 taper applies to the DoubleStar path) — you saw pre‑fix. (c) Confirm
  the FOV only changes with *separation* (legitimate), not aperture.

### B3. Central obstruction — "left stays fixed; should it update w/ different normalization? label normalization on each" 🟡
- **Maps to:** shared normalisation (1.5) + per‑side labelling (1.2).
- **Diagnosis/answer:** The left (unobstructed) is intentionally the fixed
  *reference* whose peak anchors the right's shared normalisation — that's how
  the Strehl drop is made visible. But it's **not labelled**, so the intent is
  invisible.
- **Action:** Add a clear normalisation label to each pane (e.g. left =
  "Unobstructed reference (peak = 1.0)", right = "Shared scale — peak =
  Strehl"). Decide w/ user whether the left should also become tweakable; for
  now keep it as the reference but make the label explain why.

### B4. Chromatic aberration — "singlet SA? + two zoom modes for focal‑plane images" ❓🔴
- **Actions:** (a) Idealise singlet to CA‑only (answer A2). (b) Add a **zoom
  toggle** on the focal‑plane (after) panel: "wide" (current, shows singlet
  spread) and "close" (zoom to resolve achromat / APO‑doublet / APO‑triplet
  differences).

### B5. Vignetting — "autoscaling; label obstruction on fixed left; show on starfields; maybe a diagram" 🟡🔴
- **Actions:** (a) Lock the vignetting‑curve axes so changes are visible, not
  auto‑hidden. (b) Label the baseline's obstruction ratio. (c) Ensure vignetting
  is one of the toggleable effects on the star‑field showcase (B12). (d)
  *Optional:* a one‑time explanatory diagram in Parameters & Physics.

### B6. Spherical aberration — "checkerboard artifacts; rect outline; solid/dotted transition; ray‑fan Δx vs Δy; autoscaling; parabolic keep spherical y‑axis" 🔬🔴
- **Actions:** (a) 🔬 Diagnose the checkerboard / rectangular‑outline / line‑style
  artifacts in `plot_ray_trace_pupil_colored`. (b) Confirm/fix the ray fan plots
  transverse (image‑plane) aberration (answer A4). (c) Lock axes. (d) Make the
  parabolic case share the spherical case's y‑axis so "collapses to ~0" reads.

### B7. Chromatic + seeing — "detector barely visible even at max exposure; eye exposure?; fixed left no stars (label+fix); purple rectangle (small domain)" 🟡🔬
- **Actions:** (a) 🔬 Diagnose why the Detector/linear view is nearly black even
  at max exposure (brightness calibration for this multi‑star field). (b)
  Eye‑exposure answered (A1). (c) Per‑side: label the left and decide its view
  (likely Eye so the stars show), keep it fixed/labelled. (d) Re‑verify the
  **purple rectangle** (per‑star chromatic square box) is gone via 1.3 taper.

### B8. Exposure & saturation — "eye exposure?; live detector‑vs‑eye (not fixed eye left); truncating box; focal length no effect; no colour" 🟡🔴🔬
- **Actions:** (a) Eye‑exposure answered (A1). (b) **Redesign**: left = live
  Detector, right = live Eye (both update) — *not* my Phase‑1 "before 0.1×"
  design, which didn't match your request. (c) 🔬 Confirm/fix the truncating box
  (1.3 taper on PointSource path). (d) 🔬 Focal length: determine whether it
  should affect this view; if not, remove the control. (e) Colour: a mag‑0 white
  star has no hue — either reword the description or use a coloured star so cone
  desaturation is actually demonstrable.

### B9. ND filter on Moon — "left = no‑filter following exposure; aperture→brightness?; W25 makes Moon yellow" 🟡🔴🐛
- **Bug found (W25):** `WRATTEN_25` is a Gaussian centred 660 nm with **FWHM
  140 nm — too wide**, leaking ~15% green (T_G≈0.15 @550 nm) on top of red
  (T_R≈0.85). White → red+green = orange/yellow. A real W25 cuts off sharply
  below ~580 nm. **Fix: narrow/curve the W25 (and re‑check W47/W58) so it's a
  proper long‑pass red.**
- **Actions:** (a) Per‑side: left = no filter, follows the same exposure (✅ set
  in 1.2 — verify). (b) Aperture/brightness: drop the diameter control (answer
  A3). (c) Fix the W25 filter.

### B10. Colour filters on Jupiter — "left unfiltered following exposure; live‑ephemeris clip; plus‑sign blur (H/V only); W25 doesn't enhance GRS; colours wash then creep back" 🟡🔴🔬🐛
- **Actions:** (a) Per‑side left unfiltered following exposure (✅ 1.2 — verify).
  (b) 🔬 Diagnose the live‑ephemeris render (shrinks disk + clipped white
  outline). (c) Explain/address the **plus‑sign**: Jupiter_200mm has 4 spider
  vanes → 4 spikes at H/V (perpendicular to vanes). It's physically correct but
  reads oddly on a planet; consider dropping spiders here or noting it. (d) W25
  GRS enhancement: depends on both the W25 fix (B9) **and** the Jupiter texture
  actually having a red GRS to differentially pass — 🔬 verify the texture. (e)
  Colour‑wash‑then‑creep‑back at high exposure: diagnose the
  filter×saturation×desaturation interaction.

### B11. Bright + dim (dynamic range) — "left detector, right eye (not fixed left)" ✅
- **Maps to:** Phase 1.2. Already set `before_display_stretch="linear"` (left =
  Detector) and after default `"log"` (right = Eye), both tracking aperture.
  **Action: verify** it matches your intent.

### B12. Star‑field showcase — "we lost it; bring back an extensively thought‑out field showing ALL effects with toggles" 🔴 **(highest priority)**
- **Actions:** Design a flagship wide‑field star‑field scenario: off‑axis stars
  (coma), planted double stars (resolution), wide brightness range, with the
  full effect‑toggle set (obstruction / spider / coma / vignetting / seeing) and
  honest brightness + a visual treatment that survives canvas rasterisation.
  Audit whether the current `starfield_resolution` / `StarFieldResolutionField`
  is the intended showcase or whether it needs a redesign.

### B13. Propagate fixes across all cases 🟡
- **Action:** Apply each cross‑cutting fix (axis lock, per‑side controls, taper,
  eye‑exposure, labels) to **every** affected scenario, not just the ones first
  noticed. Maintain a per‑scenario verification matrix.

### B14. Planet construction (Jupiter/Moon/Saturn) — "hi‑res + standard, or always highest then degrade?" ❓🔬
- **Answer A5:** always start highest‑res, let the sim degrade. **Action:**
  verify the pipeline renders intrinsic texture at max resolution then degrades
  (no premature capping / double blur).

---

## C. Proposed execution order

1. **Diagnose‑first batch** (🔬, read‑only): B1/B2 axis‑lock re‑verify, B6
   spherical artifacts + ray‑fan, B7 detector visibility, B8 truncating box +
   focal length, B10 live‑ephemeris + plus‑sign + texture, B14 planet pipeline.
   → fill in findings/answers here, return to user.
2. **Quick correctness fixes:** B9 W25 filter (+ W47/W58 check), labels (B3, B5,
   B7c), eye‑exposure UI (A1), drop confounding controls (B5, B9 aperture, B8
   focal length).
3. **Per‑scenario redesigns:** B4 chromatic (CA‑only + zoom), B8 exposure
   (live detector‑vs‑eye + colour), B6 spherical (Δx + shared y‑axis).
4. **Star‑field showcase (B12)** — the big one.
5. **Planet validation + tests (B14)**, then **propagation pass (B13)** with a
   verification matrix; update `IMPLEMENTATION_LOG.md` per batch.

Tests run + canvas‑pipeline verification after every batch (figsize=(5,5),
dpi=100), per the engineering‑pattern discipline.

---

## D. Diagnosis results (2026‑06‑22, read‑only canvas‑pipeline pass)

Each item reproduced by driving `TutorialTab` offscreen and capturing the final
figures the tab displays (post axis‑lock / overlay), rasterised at canvas scale.

- **B1 Airy axis lock — ✅ ALREADY FIXED (Phase 1.1).** After‑side at 400 mm
  stays locked to the before‑side 200 mm range (xlim ±0.0335). You saw the
  pre‑fix state. No action.
- **B2 Rayleigh — ✅ ALREADY FIXED.** Changing aperture no longer changes the
  FOV (before & after stay ±5″); changing separation grows it (±25″ at 5″),
  which is correct. The per‑star **square box is gone** (clean circular Airy
  disks) — Phase 1.3 taper. No action.
- **B3 Central obstruction — 🟡 confirmed.** Left is intentionally the fixed
  *unobstructed reference* (anchors the shared normalisation), but it's
  **unlabelled** so the intent is invisible. Action: per‑pane normalisation
  labels.
- **B4 Chromatic — 🔴 not started** (singlet SA + zoom modes).
- **B5 Vignetting — to verify during impl** (curve y‑axis autoscale + labels).
- **B6 Spherical — 🔬 CONFIRMED:** (a) ray trace has dashed post‑secondary rays
  on a regular pitch → reads as a checkerboard/grid + rectangular bound (visual
  cleanup needed in `plot_ray_trace_pupil_colored`). (b) The ray fan **already
  plots transverse image‑plane offset** ("Transverse focal‑plane offset Δy") —
  that's what you asked for; the "Δy" name caused the axial confusion (answer
  A4: just relabel, no physics change). (c) Parabolic ray fan **auto‑scales to
  ±1e‑11 µm** (floating‑point noise) → fake zigzag though RMS=0.00. Fix: floor
  the y‑axis to a physical (diffraction / spherical‑case) scale; lock axes.
- **B7 Chromatic+seeing — 🔬 CONFIRMED:** Detector/linear view shows only faint
  dim blobs even at 100× exposure (80 mm + 1.5″ seeing spreads the light too
  thin — it's inherently an eye/colour lesson). Recommend default Eye view +
  pin/label the before side to Eye. **Purple rectangle is GONE** ✅ (Phase 1.3).
  (Secondary: the spectral stars render uniformly greenish — worth a look.)
- **B8 Exposure — 🔬 CONFIRMED:** star core RGB = [102,102,102] → **no colour**
  (mag‑0 white star; description over‑promises). Focal length **does** change
  the raster (maxdiff 255) but shouldn't meaningfully for a point source
  (angular size is aperture‑driven) — it's the f‑ratio‑scaled PSF kernel; your
  instinct to drop the control is right. Redesign to live Detector‑vs‑Eye.
- **B9 ND Moon — 🐛 CONFIRMED bug.** W25 channel transmissions = T_R 0.848 /
  T_G 0.153 / T_B 0.012 → 15% green leak → white reads orange/yellow. Fix W25
  to a sharp long‑pass red. (W47 ok; W58 leaks some blue, minor.) Per‑side
  left=no‑filter already set (verify); drop diameter control.
- **B10 Colour Jupiter — 🔬🐛 CONFIRMED:** (a) **Live‑ephemeris square‑panel /
  clipped‑outline artifact** = axis‑lock × FOV‑mismatch: ephemeris shrinks
  Jupiter to 47″ but the lock clamps the after axis to the before's 60″, so the
  image sits in an oversized frame with the axes background showing as a grey
  border. Fix: skip axis lock when before/after half‑FOV differ. (b) Plus‑sign =
  4 spider vanes → H/V spikes (physically correct; explain or rotate/remove for
  a planet). (c) W25 doesn't enhance GRS, just orange — the texture **does** have
  a red GRS (redness 0.42), so once W25 is a proper red the contrast should
  emerge; verify after the filter fix. (d) "Features creep back at higher
  exposure" should be resolved by 1.4 (exposure N/A in Eye view) — verify.
- **B11 Bright+dim — ✅ done (Phase 1.2).** Left Detector / right Eye. Verify.
- **B12 Star field — 🔴 CONFIRMED needs redesign.** Current field renders as
  tiny sub‑pixel dots at 600″ FOV; coma/spikes not visible at that scale → reads
  as sparse/"lost". Needs a visibility‑driven showcase (FOV/zoom so PSF features
  resolve, planted edge stars for coma + doubles + brightness range, treatment
  that survives rasterisation, full effect toggles).
- **B13 Propagation — ongoing.**
- **B14 Planets — ✅ ALREADY CORRECT (answer A5).** Jupiter/Saturn render
  procedurally at full requested resolution (1024²+), Moon from a texture file;
  `plot_source_image` renders extended sources at high internal res then
  **sum‑bins (degrades)** to display res. No premature capping. Add tests to
  lock it in.

**Net:** already‑fixed (verify only): B1, B2, B11, B14. Quick fixes: B9 (W25),
B3 (labels), B10a (lock×FOV), B6c (ray‑fan floor), eye‑exposure UI. Redesigns:
B4, B6a, B7, B8. Big build: **B12 star‑field showcase**.

---

## E. Batch 1 — quick correctness fixes (DONE, 2026‑06‑29)

All verified through the canvas pipeline; **372 tests pass** (was 360; +12:
`tests/test_filters.py` ×7, `TestRound2Batch1` ×5).

- **B9 W25/W58 filters ✅.** New `_longpass_transmission` helper; W25 is now a
  sharp long‑pass red (cut‑on ~595 nm): T_R 0.90 / T_G 0.02 / T_B 0.00 (was
  0.85/0.15/0.01). W58 narrowed 80→55 nm FWHM (blue leak 0.17→0.07). Verified:
  Moon and Jupiter render **red, not yellow/orange**. (The subtler GRS‑contrast
  enhancement + eye‑view colour‑wash remain B10 redesign items.)
- **B10a axis‑lock × FOV ✅.** `_render_after` now skips the lock per‑axis for
  `plot_source_image` when before/after natural spans differ >5%. Verified: Airy
  still locks (psf_2d, mm), Rayleigh equal‑FOV locks, Jupiter live‑ephemeris now
  shows at its own 47″ FOV (no grey oversized frame).
- **B6c ray‑fan floor ✅.** y‑axis floored to 3× Airy radius. Parabolic reads as
  a flat line at 0 (was ±1e‑11 µm zigzag); spherical autoscales to ±192 µm.
- **B3 central‑obstruction labels ✅.** Panel captions state the normalisation
  ("reference (PSF peak ≡ 1.0)" / "same scale; peak = Strehl"); before figure
  annotated "Reference: normalised to own peak"; after already shows "Peak vs
  unobstructed: <Strehl>".
- **A1 eye‑view exposure UI ✅.** Exposure slider greys out and shows "N/A (Eye)"
  in log/log_integrated views (exposure = detector‑only). Synced on view change
  and on scenario load.
- **B5/B8/B9 dropped confounding controls ✅.** `nd_filter_moon` drops diameter
  (filter lesson); `exposure_demo` drops focal_length, keeps diameter (D²
  affects saturation). Fixed the controls‑panel early‑return so source‑image
  scenarios keep the View/Filter/Exposure combos even with no telescope params.

**Next: Batch 2 — per‑scenario redesigns** (B4 chromatic CA‑only + zoom modes;
B7 chromatic+seeing default‑Eye + labels; B8 exposure live detector‑vs‑eye +
colour; B6a spherical ray‑trace visual cleanup), then **B12 star‑field
showcase**, then **B14 planet tests + B13 propagation pass**.

---

## F. Batch 2 — per‑scenario redesigns (DONE, 2026‑06‑29)

All verified through the canvas pipeline; **379 tests pass** (was 372; +7).
All 18 scenarios smoke‑tested (0 render failures).

- **B4 chromatic ✅.** `plot_polychromatic_ray_trace(idealize_sa=True)` draws
  each colour converging to a point (SA removed, flagged on‑plot) so the
  singlet/achromat/APO comparison isolates *chromatic* shift; new scenario flag
  `idealize_singlet_sa`. Added a "Focal zoom" combo (Wide ±120″ / Close ±12″)
  threaded as `fixed_xlim_arcsec` → `plot_chromatic_focal_planes`; Close
  resolves the achromat/APO residuals invisible at Wide. Description updated.
- **B7 chromatic+seeing ✅ (explicit asks).** Default Eye view; before side
  pinned to Eye + relabelled "Reference — Eye view" so the spectral stars are
  always visible (Detector is genuinely near‑black at 80 mm + 1.5″ — a real
  lesson, switchable on the right). Purple rectangle already gone (1.3).
  **Finding (flagged, not hacked):** the spectral stars render green‑cored even
  in linear view — `chromatic_psf_kernel` is flux‑normalised so the in‑focus G
  channel peaks highest; the achromat's ~f/2000 secondary spectrum (physically
  real) spreads R/B into wide halos, so the per‑pixel core is green while the
  *integrated* flux is the true SED. Defensible physics + coupled to B4's
  achromat magnitude → needs a user decision before changing.
- **B8 exposure ✅.** Redesigned to live Detector (left, linear, pinned) vs Eye
  (right, log default), both tracking aperture; dropped the fixed before‑0.1×.
  New `PointSource(spectral_rgb=…)` + a non‑chromatic colour‑stamping path so a
  star renders its intrinsic SED colour through a reflector (colour is not a
  chromatic artefact). Verified: faint orange star → saturated white core +
  orange rings as Detector exposure rises; Eye view exposure‑invariant; no
  truncating box. Gated on `star_spectral_rgb` so white stars are unchanged.
- **B6a spherical ray‑trace ✅.** Extension rays drawn solid (was dotted) → the
  picket‑fence/checkerboard moiré and the solid→dotted transition are gone;
  each ray is one continuous colour line and the SA crossover (marginal rays
  converging short of paraxial) reads clearly.

**Cross‑cutting win:** chroma‑preserving asinh in the eye view (stretch
luminance, preserve RGB ratio) — replaces per‑channel asinh that washed colour.
Verified it improves plain Jupiter (bands + red GRS now visible), W25‑filtered
Jupiter (saturated red, addresses much of B10), and leaves white double‑stars
unchanged.

**Next: B12 star‑field showcase** (the big one — the wide field renders as
sub‑pixel dots at 600″; needs a visibility‑driven redesign), then **B14 planet
tests + B13 propagation pass**. Open decision for the user: the B7 green‑star
core (see finding above).

---

## G. Batch 3 — B12 star‑field showcase (DONE, 2026‑06‑30)

Verified through the canvas pipeline; **383 tests pass** (was 379; +4). 18/18
scenarios smoke‑test clean.

- **New `ShowcaseStarField`** (`sources.py`): 66 stars at 300″ FOV — 1 bright
  on‑axis reference, 4 bright coloured edge stars (coma + spikes), a double‑star
  ladder (8″/4″/2″), ~55 seeded background stars, all with spectral‑class RGB
  tints (`_SPECTRAL_PALETTE`). Exported + registered in the runner.
- **Colour through a reflector:** reuses the B8 non‑chromatic colour‑stamping
  path, so the field renders in rich spectral colour (was uniform grayscale
  dots). Verified ≥4 distinct tints, chroma present in the render.
- **Spider‑spike kernel fix** (`_render_source_through_telescope`): the per‑star
  kernel was capped at 8× Airy, cropping spikes to a stub; now expands to ~45×
  Airy when `spider_vanes>0` (the FFT PSF already spans ~100×). Bright stars now
  show real diffraction spikes on the per‑star path (previously only the
  extended‑source path expanded for spiders).
- **Scenario redesign** (`starfield_resolution` → "Star Field Showcase"):
  before = ideal optics (no obstruction/spider/coma/vignetting/seeing) vs after
  = realistic 200 mm f/4 with the effect toggles. Verified each of coma /
  spider / obstruction / seeing produces a clear render change (≈15k–25k px;
  quantitatively, since offscreen Qt hides the toggle checkboxes so the tab
  harness can't read them — the toggle→render wiring is unchanged from the
  Phase‑1 jupiter_full verification).
- **Vignetting dropped from the toggles (finding):** for a 200 mm f/4 with a
  normal secondary the fully‑illuminated field is ~75′ — 15× this 5′ field — so
  NO star is ever vignetted (even at obstruction 0.10, FIF ≈ 33′). Tube
  vignetting isn't modelled. A vignetting toggle here would be a guaranteed
  no‑op, so it's omitted and explained in the description; the dedicated
  Vignetting scenario covers it via the falloff curve. (This contradicts the
  original request to show vignetting on the star field — flagged for the user;
  it's a model limitation, not a wiring bug.)

**Next: B14 planet render‑then‑degrade tests + B13 propagation pass.** Open user
decisions: (1) B7 green‑star core; (2) vignetting‑on‑starfield can't be shown
under the current model.

---

## H. Batch 4 — B14 planet validation + B13 propagation (DONE, 2026‑06‑30)

**390 tests pass** (was 383; +7). 18/18 scenarios smoke‑test clean.

**B14 — planet render‑then‑degrade (A5 confirmed, tests added).** Validated
empirically: (1) Jupiter/Saturn/Moon textures render at the full requested
resolution; (2) `plot_source_image` renders extended sources oversampled then
sum‑bins to display (e.g. Jupiter 260→120; Moon 2048→512) while star sources
render == display; (3) degradation is monotonic (hi‑vs‑median contrast
0.996→0.87 as seeing 0→6″); (4) colour survives PSF+seeing+eye view (Jupiter
R>G>B). No premature cap, no double blur. New `TestPlanetPipeline` (5 tests).

**B13 — propagation pass.** Built a per‑scenario config matrix across all 18:
no inconsistencies (every extended‑source scenario has realtime + exit‑pupil;
filter combos only on source‑image scenes). Confirmed the cross‑cutting fixes
live in generic paths (renderer/tab) so they auto‑propagate, and verified the
detector‑vs‑eye brightness invariant at runtime for all six source types
(PointSource, DoubleStar, MultiColorStarField, ShowcaseStarField, Jupiter,
Moon): eye view exposure‑invariant, detector view exposure‑sensitive. New
`TestBrightnessModelPropagation` (2 tests) locks the invariant in.

**Round 2 status: all feedback items addressed** (B1–B14). Two items are
documented model‑limitation/judgement calls awaiting a user decision (B7
green‑star core; vignetting‑on‑starfield). Nothing committed.

**User decision (2026‑07‑02):** (1) B7 green‑star core — **leave for now**;
(2) vignetting — **add a static diagram in Parameters & Physics** (the user's
own suggested alternative). Done: `_build_vignetting_diagram()` in
`reference_tab.py` (side‑view clip + secondary‑face circle‑overlap, θ_fif
caption, note on why it can't show on the star field); embedded via
`_make_figure_section`; showcase description points to it. **392 tests pass.**
B7 green‑star remains the one open item, deferred by the user.

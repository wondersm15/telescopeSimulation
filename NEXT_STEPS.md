# Next Steps — Terminal Integration & Educational Testing

**Date**: 2026-03-28
**Status**: Planning phase — DO NOT implement yet

---

## Workflow

1. **Create feature branch** to keep main branch clean and functional
2. **Use Opus for planning** (detailed design, architecture decisions)
3. **Use Sonnet for implementation** (write code based on Opus's plan)

---

## Feature 1: Terminal Integration & Learning Mode (Phase 3)

**Goal**: Show users the underlying Python commands being executed, helping them learn the API and transition from GUI to programmatic use.

### Components

**Bottom Terminal Panel** (`telescope_gui/widgets/terminal_panel.py`):
- Collapsible/resizable panel at bottom of main window
- Read-only text display with syntax highlighting
- Shows equivalent Python commands for current GUI actions
- Copy-to-clipboard button
- Optional: "Run in IPython" button to launch interactive session

**Command Logging**:
- Each tab's `update_view()` logs commands to terminal panel
- Example output:
  ```python
  >>> telescope = NewtonianTelescope(
          primary_diameter=200.0,
          focal_length=1000.0,
          primary_type="parabolic"
      )
  >>> source = Jupiter(distance_au=5.2)
  >>> plot_ray_trace(telescope, num_display_rays=11)
  >>> plot_source_image(telescope, source, seeing_arcsec=1.5)
  >>> # Calculation complete (1.2s)
  ```

**Interactive Tooltips**:
- Hover over parameters → see definitions
- Links to relevant sections in USER_GUIDE.md or PHYSICS.md

### Educational Value
- Users see API structure transparently
- Can copy/paste commands into scripts for batch processing
- Demystifies the GUI — shows it's just calling the same functions
- Supports learning progression from GUI → programmatic use

---

## Feature 2: Simulation Testing & Educational Program

**Goal**: Interactive testing plan that demonstrates the physics is working correctly, with guided experiments showing cause-and-effect relationships. Educational program teaching optical physics through hands-on simulation.

### New Top-Level Tab: "Simulation Testing"

**Structure** (alongside "Single Telescope", "Comparison", "Parameters & Physics"):
- Educational testing scenarios with step-by-step instructions
- Each test shows:
  1. **What to do**: "Set telescope to X, source to Y, change parameter Z"
  2. **What to observe**: "Notice how spider vanes create diffraction spikes"
  3. **Why it happens**: Brief physics explanation
  4. **Code reference**: "See `telescope_sim/physics/fft_psf.py:45-67` for implementation"
  5. **Deeper dive**: Links to PHYSICS.md, FORMULAS.md, relevant papers

### Example Test Scenarios

**1. Spider Vane Diffraction**:
- Start: 200mm Newtonian, no spider vanes, Point Source
- Observe: Perfect Airy disk
- Change: Add 4 spider vanes, 2mm width
- Observe: Four diffraction spikes perpendicular to vanes
- Physics: Fraunhofer diffraction from thin obstacles
- Code: `fft_psf.py` - 2D FFT pupil mask

**2. Central Obstruction Effects**:
- Start: 200mm Newtonian, 20% obstruction, Point Source
- Observe: Bright secondary rings, reduced Strehl ratio
- Change: Disable obstruction
- Observe: Cleaner PSF, higher peak intensity
- Physics: Annular aperture diffraction (modified Bessel function)
- Code: `diffraction.py:compute_psf()` with ε parameter

**3. Chromatic Aberration**:
- Start: 80mm singlet refractor, Jupiter, polychromatic ON
- Observe: Purple/green fringing on limb
- Change: Switch to achromatic doublet
- Observe: Fringing reduced ~10×
- Physics: Wavelength-dependent refraction (Cauchy dispersion)
- Code: `refraction.py:GLASS_CATALOG`, `lenses.py:AchromaticDoublet`

**4. Seeing Limits vs Aperture**:
- Start: 50mm aperture, seeing=1.5", Point Source
- Observe: Seeing-limited performance (resolution display shows ⚠)
- Change: Increase aperture to 250mm
- Observe: Still seeing-limited (atmosphere dominates)
- Change: Set seeing=None (space telescope)
- Observe: Now diffraction-limited (resolution ✓)
- Physics: Atmospheric turbulence vs diffraction limit
- Code: `ray_trace_plot.py:_render_source_through_telescope()` - Gaussian seeing blur

**5. f-ratio and Coma**:
- Start: 200mm f/5 Newtonian, show coma analysis
- Observe: Narrow coma-free field (~0.1°)
- Change: f/8
- Observe: Wider coma-free field (~0.26°, scales as f²)
- Physics: Off-axis Seidel aberrations
- Code: `aberrations.py:compute_coma_spot()`

**6. Exit Pupil Washout**:
- Start: Jupiter, 25mm eyepiece (low mag, large exit pupil)
- Observe: Washed out, low contrast
- Change: 5mm eyepiece (high mag, small exit pupil)
- Observe: Brighter, better contrast and saturation
- Physics: Surface brightness, eye adaptation
- Code: `ray_trace_plot.py:_apply_exit_pupil_washout()`

### Implementation Details

**Tab Layout**:
- Left sidebar: List of test scenarios (clickable)
- Main area: Current test instructions + "Run Test" button
- Right area: Results display or comparison view
- Bottom: Progress tracker (X of Y tests completed)

**Auto-Configuration**:
- Clicking a test scenario auto-configures the telescope/source
- User can modify and re-run to explore
- "Reset to Test Defaults" button

**Progress Tracking**:
- Check boxes for completed tests
- Optional: Save progress to user config file
- Completion certificate / achievement system (optional, gamification)

### Educational Extensions

**"Why This Matters" sections**:
- Real-world context: "This is why refractors cost more than reflectors"
- Design implications: "This is why most planetary imagers use f/10+"
- Observing tips: "This is why you need good seeing for high-resolution work"

**Guided Learning Path**:
1. **Basics**: Diffraction limit, Airy disk, resolution
2. **Aberrations**: Spherical, chromatic, coma
3. **Design Trade-offs**: Obstruction, f-ratio, aperture
4. **Atmospheric Effects**: Seeing, transparency
5. **Advanced**: Polychromatic imaging, multi-element optics

**Links to Theory**:
- Each test links to relevant equations in FORMULAS.md
- Links to "Further Reading" (textbooks, papers)
- Suggestions for next tests in learning sequence

---

## Implementation Plan

### Step 1: Branch & Planning (Opus)
```bash
git checkout -b feature/terminal-and-testing
```

**Opus tasks**:
1. Design terminal panel architecture (widget structure, command logging system)
2. Design "Simulation Testing" tab structure and user flow
3. Write detailed specifications for 10-15 test scenarios
4. Plan integration points with existing tabs
5. Define data structures for test scenarios (JSON? Python classes?)
6. Specify educational content format and progression
7. Create file structure and module organization plan

### Step 2: Implementation (Sonnet)

**Phase 1: Terminal Panel**
- Create `telescope_gui/widgets/terminal_panel.py`
- Integrate into `main_window.py` as collapsible bottom panel
- Add command logging to all 5 existing tabs
- Implement copy-to-clipboard functionality
- Add syntax highlighting (use `pygments` or simple color coding)

**Phase 2: Testing Tab Foundation**
- Create `telescope_gui/testing_tab.py`
- Add to mode selector as 4th option (or separate menu item)
- Implement test scenario data structure
- Create left sidebar with test list

**Phase 3: Test Scenarios**
- Implement 6 core test scenarios listed above
- Add auto-configuration logic
- Add results comparison views
- Link to code references and documentation

**Phase 4: Educational Content**
- Add "Why This Matters" sections
- Create guided learning path structure
- Add progress tracking
- Polish and user testing

### Step 3: Testing & Documentation
- Manual testing of all scenarios
- Update USER_GUIDE.md with terminal panel documentation
- Update GUI_PLAN.md to mark Phase 3 as complete
- Add "Educational Features" section to README.md

---

## Wait for User Command

**DO NOT implement this plan yet.**

When ready to proceed, user will say "proceed" and we will:
1. Create feature branch
2. Use Opus for detailed planning
3. Use Sonnet for implementation following Opus's design

---

## Notes

- This aligns with original GUI_PLAN.md Phase 3 and Phase 6 (Educational Content Integration)
- Terminal panel makes the GUI a true learning tool, not just a convenience wrapper
- Testing tab bridges the gap between "it works" and "I understand why"
- Both features support the project's goal of teaching optical physics through hands-on simulation
- Consider adding these features to ROADMAP.md as high priority once implemented

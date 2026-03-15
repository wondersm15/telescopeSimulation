# GUI Development Plan

**Last updated**: March 2026
**Status**: Planning phase

---

## Vision

Transform the telescope simulator from a script-based tool into an interactive GUI application that makes optical design exploration accessible to non-programmers while maintaining transparency for learning.

### Core Principles

1. **Preserve existing functionality** - GUI wraps around `telescope_sim` package, no major refactor
2. **Learning-focused** - Show underlying commands/parameters to teach the API
3. **Progressive enhancement** - Start simple, add features incrementally
4. **Realism-first** - Maintain physics accuracy, don't sacrifice for UI convenience

---

## Framework Decision

### Options Considered

| Framework | Pros | Cons | Verdict |
|-----------|------|------|---------|
| **PyQt6** | Professional look, rich widgets, mature, cross-platform | Steeper learning curve, GPL/commercial licensing | **Recommended** |
| **Tkinter** | Built-in (no install), simple, lightweight | Dated appearance, limited widgets | Fallback option |
| **Streamlit/Dash** | Web-based, beautiful, easy to deploy | Less control, requires server, slower | Not ideal for desktop tool |
| **Dear PyGui** | Fast, modern, GPU-accelerated | Less mature, smaller community | Future consideration |

### Recommendation: **PyQt6**

**Rationale:**
- Professional appearance suitable for educational/scientific use
- Excellent matplotlib integration (can embed plots directly)
- Rich widget library (sliders, spinboxes, tabs, etc.)
- Cross-platform (macOS, Windows, Linux)
- Active development and community
- LGPL license compatible with open-source project

**Installation:**
```bash
pip install PyQt6
```

---

## Phase 1: Minimum Viable Product (MVP)

**Goal**: Create a functional GUI that replaces the most common `main.py` editing workflows.

**Timeline estimate**: 3-4 weeks (full implementation)

### Tab 1: Telescope Design View (Default)

**Layout**: Split view with ray trace + simulated image side-by-side

```
┌─────────────────────────────────────────────────────────────┐
│ Telescope Design                                        [×] │
├─────────────────────────────────────────────────────────────┤
│ ┌──────────────────────┐ ┌─────────────────────────────┐   │
│ │                      │ │                             │   │
│ │   Ray Trace          │ │   Simulated Image           │   │
│ │   (matplotlib)       │ │   (Jupiter/Moon/etc.)       │   │
│ │                      │ │                             │   │
│ │                      │ │                             │   │
│ └──────────────────────┘ └─────────────────────────────┘   │
│                                                             │
│ ┌─── Controls ────────────────────────────────────────────┐│
│ │ Telescope Type: [Newtonian ▼]                          ││
│ │ Aperture (mm):  [200     ] f-ratio: [5.0    ]          ││
│ │ Primary Type:   [Parabolic ▼]                          ││
│ │ Source:         [Jupiter ▼]   Seeing: [Good ▼]         ││
│ │                                                         ││
│ │ [Update View]  [Export Images...]  [Save Config...]    ││
│ └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**Controls (Phase 1 MVP):**
- **Telescope Type**: Dropdown (Newtonian, Cassegrain, Refractor, Maksutov, Schmidt-Cassegrain)
- **Aperture**: Spinbox (50-500mm, increment 10mm)
- **f-ratio**: Spinbox (3.0-15.0, increment 0.5) OR focal length (auto-calculate)
- **Primary Type**: Dropdown (Parabolic, Spherical) - only for Newtonian
- **Source**: Dropdown (Jupiter, Moon, Saturn, Star, None)
- **Seeing**: Dropdown (Excellent, Good, Average, Poor, None)
- **Update View**: Button to re-render (initially manual, later auto-update)

**Interaction:**
1. User selects parameters
2. Clicks "Update View"
3. GUI calls existing `telescope_sim` functions
4. Matplotlib figures embedded in Qt widgets
5. Updates both ray trace and simulated image

**Technical Implementation:**
- `QMainWindow` with `QTabWidget`
- Matplotlib `FigureCanvas` embedded in Qt widgets
- Signals/slots for button clicks
- Backend: reuse existing `plot_ray_trace()` and `_render_source_through_telescope()`

### Tab 2: Comparison View

**Layout**: Side-by-side comparison of 2-4 telescope configurations

```
┌─────────────────────────────────────────────────────────────┐
│ Comparison                                              [×] │
├─────────────────────────────────────────────────────────────┤
│ Config 1           Config 2           Config 3              │
│ ┌────────────┐    ┌────────────┐    ┌────────────┐         │
│ │ Ray Trace  │    │ Ray Trace  │    │ Ray Trace  │         │
│ └────────────┘    └────────────┘    └────────────┘         │
│ ┌────────────┐    ┌────────────┐    ┌────────────┐         │
│ │ Simulated  │    │ Simulated  │    │ Simulated  │         │
│ │ Image      │    │ Image      │    │ Image      │         │
│ └────────────┘    └────────────┘    └────────────┘         │
│                                                             │
│ [Add Config] [Remove Config] [Export Comparison...]         │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Start with 2 configs by default
- Add up to 4 configs maximum (screen real estate limit)
- Each config has independent controls (collapsible panel)
- Same source across all configs (for fair comparison)
- Export comparison as single multi-panel figure

**Use Cases:**
- f/5 vs f/8 Newtonian comparison
- Singlet vs achromat refractor (chromatic aberration)
- Parabolic vs spherical primary
- Different apertures at same f-ratio

### Menu Bar

**File Menu:**
- New Configuration
- Open Configuration... (load from JSON/YAML)
- Save Configuration...
- Save Configuration As...
- Export Current View... (PNG/PDF)
- Exit

**View Menu:**
- Show/Hide Controls Panel
- Show/Hide Terminal (Phase 2+)
- Zoom In/Out (matplotlib controls)

**Help Menu:**
- User Guide (open USER_GUIDE.md in browser or text viewer)
- Physics Reference (open PHYSICS.md)
- About

### Status Bar

Bottom status bar showing:
- Current configuration name
- Last update timestamp
- Calculation status ("Ready", "Calculating...", "Error: ...")

---

## Phase 2: Enhanced Interactivity

**Timeline**: 2-3 weeks after MVP

### Features to Add

**1. Auto-Update Mode**
- Checkbox: "Auto-update on parameter change"
- Real-time re-rendering as sliders move (with debouncing)
- Progress indicator for long calculations

**2. Advanced Controls Panel**
- Collapsible sections (Basic / Advanced / Physics)
- **Advanced**:
  - Spider vanes: count (0/3/4/6) and width
  - Eyepiece focal length
  - Wavelength selection (for monochromatic mode)
  - Number of display rays
- **Physics**:
  - Polychromatic mode toggle
  - Central obstruction size override
  - Atmospheric seeing (custom arcsec value, not just presets)

**3. PSF Analysis Tab**
- Dedicated tab for point spread function analysis
- Show Airy pattern, combined PSF, radial profile
- Strehl ratio, FWHM calculations
- Export PSF data (CSV for further analysis)

**4. Configuration Presets**
- Dropdown: "Load Preset..."
  - "8\" f/6 Newtonian (common Dobsonian)"
  - "6\" f/8 Cassegrain"
  - "80mm f/11 Achromat Refractor"
  - "90mm f/5 Maksutov-Cassegrain"
  - User can save custom presets

**5. Better Error Handling**
- Validate inputs (e.g., f-ratio must be > 0)
- Graceful error messages in UI (not terminal crashes)
- Tooltips explaining constraints ("f-ratio must be ≥ 3.5 for Cassegrain secondary clearance")

---

## Phase 3: Terminal Integration & Learning Mode

**Timeline**: 2-3 weeks

### Terminal Window Panel

**Goal**: Show the underlying Python commands being executed so users learn the API.

**Layout**: Bottom panel (collapsible/resizable)

```
┌─────────────────────────────────────────────────────────────┐
│ [Main View Area]                                            │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Terminal / Command Log                              [▲] [×] │
├─────────────────────────────────────────────────────────────┤
│ >>> telescope = NewtonianTelescope(                         │
│         primary_diameter=200.0,                             │
│         focal_length=1000.0,                                │
│         primary_type="parabolic"                            │
│     )                                                       │
│ >>> source = JupiterSource(distance_au=5.2)                 │
│ >>> plot_ray_trace(telescope, num_display_rays=11)          │
│ >>> render_source_through_telescope(telescope, source, ...) │
│ >>> # Calculation complete (1.2s)                           │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Read-only text display (syntax highlighted)
- Shows equivalent Python code for current configuration
- Copy button to copy commands to clipboard
- "Run in IPython" button to launch interactive session with config
- Optional: actual embedded IPython console (advanced)

**Educational Value:**
- Users see the API structure
- Can copy/paste into scripts for batch processing
- Demystifies the GUI - it's just calling the same functions
- Supports transition from GUI to programmatic use

### Interactive Tooltips

- Hover over any parameter → see definition
- Example: Hover "f-ratio" → "Ratio of focal length to aperture diameter. Lower f-ratio = faster optics, wider field, more coma."
- Links to relevant section in USER_GUIDE.md or PHYSICS.md

---

## Phase 4: Real-World Integration

**Timeline**: 3-4 weeks (depends on API integration complexity)

### Location & Time Panel

**New section in main tab controls:**

```
┌─── Observing Conditions ────────────────────────────────┐
│ Mode: ○ Standard    ● Real-World                        │
│                                                         │
│ Location: [San Francisco, CA    ▼] [Detect Auto]       │
│ Date/Time: [2026-03-14 21:30 PST  ] [Use Now]          │
│                                                         │
│ Current Conditions:                                     │
│   Seeing: 2.1" (calculated from weather)               │
│   Transparency: Good                                    │
│   Object Altitude: 45° (Jupiter)                       │
│   Angular Diameter: 44.2" (current Earth-Jupiter dist) │
└─────────────────────────────────────────────────────────┘
```

**Features:**
- **Standard Mode**: User-defined parameters (current behavior)
- **Real-World Mode**:
  - Fetch current seeing from weather API (or estimate from humidity, wind, temp)
  - Calculate object position (altitude/azimuth) from location + time
  - Use current Earth-object distance for angular size
  - Warn if object is below horizon or in poor conditions

**APIs to integrate:**
- `astropy` - ephemeris, coordinate transforms
- `skyfield` - planetary positions
- Weather API (OpenWeatherMap, etc.) - approximate seeing conditions

**Use Case:**
"I want to observe Jupiter tonight at 9pm from my backyard. What will it look like through my 8\" Dob with current atmospheric conditions?"

---

## Phase 5: Constellation & Sky Navigation

**Timeline**: 2-3 weeks

### New Tab: Sky View

**Interactive star chart showing telescope FOV in context**

```
┌─────────────────────────────────────────────────────────────┐
│ Sky Navigator                                           [×] │
├─────────────────────────────────────────────────────────────┤
│ ┌───────────────────────────────────────────────────────┐   │
│ │           *  Orion    *                               │   │
│ │         *       *                                     │   │
│ │    *  Betelgeuse                                      │   │
│ │         *   *  *  (Belt)                              │   │
│ │           *                                           │   │
│ │      *  Rigel                                         │   │
│ │                                                       │   │
│ │  [○] ← Telescope FOV (1.2° with 20mm eyepiece)       │   │
│ │                                                       │   │
│ │  Click to point telescope                            │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                             │
│ Pointing: Orion Nebula (M42)                                │
│ Constellation: Orion                                        │
│ Objects in FOV: [M42], [θ¹ Ori (Trapezium)]                │
│                                                             │
│ [Show Info...]  [Simulate View]                             │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Interactive star chart (clickable)
- Constellation lines and labels
- Bright stars and DSOs (Messier catalog, NGC/IC subset)
- Telescope FOV overlay (circle showing eyepiece field)
- Click to "point" telescope → update main tab with simulated view
- Filter: "Show only objects visible now" (real-world mode integration)

**Data Sources:**
- Hipparcos star catalog (bright stars)
- Messier catalog (DSOs)
- IAU constellation boundaries and patterns
- Integrate with `astropy.coordinates`

**Educational Value:**
- Learn constellation patterns
- Understand FOV vs sky scale ("How much of Orion fits in my view?")
- Plan observations ("What's visible tonight?")

---

## Phase 6: Educational Content Integration

**Timeline**: 2 weeks

### New Tab: Learn

**Interactive educational content with linked simulations**

**Sections:**

1. **Telescope Design Guide**
   - Overview of telescope types (Newtonian, Cassegrain, Refractor, etc.)
   - When to choose each type (portability, cost, FOV, obstruction, etc.)
   - Click "Try Example" → loads preset in Design tab

2. **Optics Concepts**
   - Diffraction limits
   - Chromatic aberration (interactive: toggle singlet/achromat)
   - Spherical aberration (interactive: parabolic vs spherical)
   - f-ratio and its effects
   - Each concept has "See Example" button

3. **Observing Tips**
   - Surface brightness and magnification
   - Exit pupil sweet spots
   - Seeing conditions and planetary imaging
   - When to use filters, eyepieces

4. **Constellation Guide**
   - Notes on each constellation (mythology, notable objects)
   - Linked to Sky Navigator tab

**Implementation:**
- Markdown content rendering (Qt supports basic markdown)
- Embedded hyperlinks to tabs/presets
- Images/diagrams from `docs/outputs/products/`

---

## Phase 7: Advanced Features

**Timeline**: Ongoing / as needed

### Batch Analysis Mode
- Run parameter sweep (e.g., test f-ratios from 4 to 10 in 0.5 steps)
- Export results table (CSV)
- Plot trends (Strehl vs f-ratio, resolution vs aperture, etc.)

### Astrophotography Mode
- Simulate sensor/camera instead of eyepiece
- Pixel scale calculations
- Sampling considerations (Nyquist, oversampling factor)
- Integration time estimates

### Custom Optical Designs
- Advanced users can define custom optical surfaces
- Upload prescription files (Zemax format?)
- Ray trace through arbitrary systems

### 3D Visualization
- 3D ray trace (not just 2D side view)
- Rotate camera view
- VTK or Mayavi integration

---

## Technical Architecture

### Directory Structure

```
telescopeSimulationProject/
├── main.py                      # Keep CLI entry point
├── gui.py                       # NEW - GUI entry point
├── telescope_sim/               # Existing package (unchanged)
│   ├── geometry/
│   ├── physics/
│   ├── source/
│   └── plotting/
├── telescope_gui/               # NEW - GUI package
│   ├── __init__.py
│   ├── main_window.py          # QMainWindow, tab management
│   ├── design_tab.py           # Tab 1: Design view
│   ├── comparison_tab.py       # Tab 2: Comparison view
│   ├── psf_tab.py              # Tab 3: PSF analysis (Phase 2)
│   ├── sky_tab.py              # Tab 4: Sky navigator (Phase 5)
│   ├── learn_tab.py            # Tab 5: Educational (Phase 6)
│   ├── widgets/                # Reusable custom widgets
│   │   ├── telescope_controls.py
│   │   ├── matplotlib_canvas.py
│   │   └── terminal_panel.py
│   └── config.py               # Configuration save/load
├── tests/
└── docs/
```

### Code Reuse Strategy

**DO NOT refactor `telescope_sim` package** — GUI wraps around it.

**Pattern:**
```python
# In telescope_gui/design_tab.py

def update_view(self):
    # Read GUI parameters
    telescope_type = self.telescope_type_dropdown.currentText()
    aperture = self.aperture_spinbox.value()
    # ... etc.

    # Build telescope using existing classes
    if telescope_type == "Newtonian":
        telescope = NewtonianTelescope(
            primary_diameter=aperture,
            focal_length=aperture * f_ratio,
            primary_type=primary_type
        )

    # Call existing plotting functions
    fig = plot_ray_trace(telescope, num_display_rays=11)

    # Display in GUI
    self.ray_trace_canvas.figure = fig
    self.ray_trace_canvas.draw()
```

**Benefits:**
- Zero risk to existing physics code
- Easy to test (existing tests unchanged)
- Can run CLI and GUI in parallel (different entry points)
- GUI is just a different interface to same engine

### Configuration File Format

**Save telescope configurations as JSON:**

```json
{
  "name": "My 8-inch Dobsonian",
  "telescope_type": "newtonian",
  "primary_diameter": 203.2,
  "focal_length": 1200.0,
  "primary_type": "parabolic",
  "spider_vanes": 4,
  "spider_vane_width": 1.0,
  "source": {
    "type": "jupiter",
    "distance_au": 5.2
  },
  "observing": {
    "seeing_arcsec": 2.0,
    "eyepiece_fl_mm": 9.0
  }
}
```

- Easy to share configurations
- Version control friendly (text format)
- Can be hand-edited by advanced users
- Use `json` module (built-in, no dependencies)

---

## Testing Strategy

### Unit Tests
- Test configuration save/load (JSON I/O)
- Test parameter validation logic
- Mock Qt widgets to test control logic

### Integration Tests
- End-to-end: load config → generate plots → verify output
- Use `pytest-qt` for GUI testing

### Manual Testing Checklist (per phase)
- [ ] All dropdowns populated correctly
- [ ] Parameter ranges enforced (no negative apertures!)
- [ ] Plots update when "Update View" clicked
- [ ] Export functions work (PNG, PDF, CSV)
- [ ] Error messages appear for invalid inputs
- [ ] Cross-platform (test on macOS and Windows)

---

## Development Workflow (Phase 1 Implementation)

### Week 1: Foundation
- [ ] Install PyQt6 and test basic window
- [ ] Create `telescope_gui/` package structure
- [ ] Implement `main_window.py` with empty tabs
- [ ] Embed single matplotlib figure (proof of concept)

### Week 2: Design Tab
- [ ] Layout design tab (split view)
- [ ] Add basic controls (dropdown, spinbox)
- [ ] Wire "Update View" button to call existing plot functions
- [ ] Embed ray trace plot (left side)
- [ ] Embed simulated image plot (right side)

### Week 3: Comparison Tab + Polish
- [ ] Layout comparison tab (2-config minimum)
- [ ] Implement add/remove config buttons
- [ ] Wire comparison plotting
- [ ] Add menu bar (File, Help)
- [ ] Add status bar

### Week 4: Testing & Documentation
- [ ] Write tests for configuration I/O
- [ ] Manual testing checklist
- [ ] Update USER_GUIDE.md with GUI section
- [ ] Screenshot examples for documentation
- [ ] Package for distribution (PyInstaller for standalone .app/.exe?)

---

## Dependencies

**Phase 1 (MVP):**
```
PyQt6>=6.6.0
# Existing dependencies:
numpy>=1.24.0
matplotlib>=3.7.0
scipy>=1.10.0
```

**Phase 4 (Real-World):**
```
astropy>=6.0.0
skyfield>=1.46
requests>=2.31.0  # For weather API
```

**Phase 5 (Constellations):**
```
# Star catalogs - consider:
astroquery>=0.4.6  # Query astronomical databases
# OR bundle static catalog files (CSV/JSON)
```

**Phase 7 (Advanced):**
```
vtk>=9.3.0  # For 3D visualization (optional)
```

---

## Distribution Strategy

### Development
- Run from source: `python gui.py`
- Users need Python + pip install requirements

### Standalone App (Future)
- **macOS**: PyInstaller → `.app` bundle
- **Windows**: PyInstaller → `.exe` installer
- **Linux**: AppImage or Flatpak

**Pros**: Non-programmers can run without Python installation
**Cons**: Large file size (~100MB+), packaging complexity

**Recommendation**: Start with source distribution, add standalone builds in Phase 2+ if there's demand.

---

## Success Metrics

**Phase 1 Success:**
- [ ] Can configure Newtonian, Cassegrain, Refractor from GUI
- [ ] Ray trace and simulated image update correctly
- [ ] Can save/load configurations
- [ ] Comparison mode works for 2 telescopes
- [ ] User guide updated with GUI instructions

**Long-term Success:**
- [ ] Non-programmers can use the tool (observed user testing)
- [ ] Educational users report learning API structure from terminal panel
- [ ] Real-world mode accurately predicts observing conditions
- [ ] Community contributions (if open-sourced)

---

## Open Questions

1. **Auto-update performance**: Should we debounce slider changes, or update on mouse release only?
2. **Cross-platform testing**: Who will test on Windows/Linux? (Primarily developed on macOS)
3. **Deployment**: Standalone app or source-only initially?
4. **Licensing**: If using PyQt6 (LGPL), what are implications for distribution?
5. **Community**: Open source on GitHub? Accept contributions?

---

## Next Steps

**To begin Phase 1 implementation:**

1. **Install PyQt6**: `pip install PyQt6`
2. **Create basic window** (proof of concept): `telescope_gui/main_window.py`
3. **Embed matplotlib figure** (test integration)
4. **Wire one control** (e.g., aperture spinbox → update plot)
5. **Iterate** from there

**Before starting**, confirm:
- [ ] Framework choice (PyQt6 vs alternatives)
- [ ] Tab 1 layout approved (side-by-side vs stacked)
- [ ] Phase 1 scope agreed upon (MVP features)

---

## Summary

This plan provides a **phased, incremental approach** to GUI development:

- **Phase 1 (MVP)**: Core functionality, 2 tabs, basic controls
- **Phase 2**: Enhanced interactivity, auto-update, presets
- **Phase 3**: Terminal integration for learning
- **Phase 4**: Real-world observing conditions
- **Phase 5**: Constellation navigation
- **Phase 6**: Educational content
- **Phase 7**: Advanced features (batch mode, 3D, etc.)

Each phase builds on the previous, maintaining working software at all times. The architecture preserves the existing `telescope_sim` package, minimizing risk and maximizing code reuse.

**Estimated total development time**: 12-16 weeks for Phases 1-6 (if working full-time equivalent).

**Ready to begin?** Start with Phase 1, Week 1, Step 1: Install PyQt6 and create a basic window.

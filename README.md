# Telescope Simulation Project

A physics-based telescope simulation tool for optical design and visualization.

## Overview

This project simulates optical telescope systems from first principles, enabling both practical design decisions and educational visualization. The simulator performs ray tracing through realistic telescope geometries, models wave optics (diffraction), and produces simulated astronomical images.

### Goals

- **Design Tool**: Make informed telescope design decisions (focal ratio, aperture, optical configuration)
- **Visualization**: Ray tracing through mirrors, lenses, and apertures with realistic physics
- **Image Simulation**: Generate authentic views of celestial objects (planets, Moon, etc.) as they would appear through different telescope designs
- **Realism**: Emphasize accurate physics over idealized representations to support real-world design and observing decisions

### Key Capabilities

- **Multiple telescope types**: Newtonian, Cassegrain, Maksutov-Cassegrain, Schmidt-Cassegrain, Refractor (singlet and achromat)
- **Realistic optics**: Parabolic/spherical/hyperbolic mirrors, refractive lenses with dispersion
- **Chromatic aberration**: Multi-wavelength ray tracing and color fringing for refractors
- **Wave optics**: Airy diffraction patterns, central obstruction effects, spider vane diffraction
- **Atmospheric effects**: Configurable seeing conditions
- **Extended sources**: Jupiter, Moon with realistic textures and proper angular size
- **Visual observing**: Eyepiece field of view, magnification, exit pupil effects

## Quick Start

### Installation

1. Clone this repository and navigate to the project directory
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Simulation

**GUI Application (Recommended):**

With the virtual environment active:
```bash
python gui.py
```

This opens an interactive GUI with:
- **Single Telescope Mode**: Design and performance analysis tabs
  - Design tab: Ray trace + simulated images side-by-side
  - Performance tab: PSF analysis, spot diagrams, metrics
- **Comparison Mode**: Compare multiple telescope configurations
  - Ray traces, simulated images, and analytics charts side-by-side
- Interactive controls for telescope type, aperture, f-ratio, sources, seeing conditions
- Real-time updates and eyepiece simulation

**Command-Line Script (Advanced):**

For scripting or batch analysis:
```bash
python main.py
```

This opens matplotlib windows showing ray traces, PSF analysis, and simulated images. Edit `main.py` to configure telescope parameters, source objects, and visualization options. The file includes detailed comments and examples.

### Running Tests

```bash
python -m pytest tests/ -v
```

## Documentation

- **[User Guide](docs/user/USER_GUIDE.md)** - Comprehensive guide to telescope types, features, and examples
- **[Physics Reference](docs/technical/PHYSICS.md)** - Detailed physics implementation inventory
- **[Formulas Reference](docs/technical/FORMULAS.md)** - Mathematical formulas and derivations
- **[Development Roadmap](docs/development/ROADMAP.md)** - Planned features and priorities
- **[Development Log](docs/development/devlog.md)** - Session-by-session development history

## Project Structure

```
telescopeSimulationProject/
├── gui.py                 # GUI entry point (recommended)
├── main.py                # CLI entry point — configure and run simulations
├── requirements.txt       # Python dependencies
├── telescope_sim/         # Main simulation package
│   ├── physics/          # Ray class, reflection, refraction, diffraction
│   ├── geometry/         # Mirror/lens types, telescope assembly
│   ├── source/           # Light source and astronomical object definitions
│   └── plotting/         # Visualization and image rendering
├── telescope_gui/         # GUI application
│   ├── single_mode/      # Design and performance tabs
│   ├── comparison_mode/  # Comparison analysis tabs
│   └── widgets/          # Reusable UI components
├── tests/                # Unit and integration tests (291 passing)
└── docs/                 # Documentation (see above)
```

## Design Philosophy

This simulator emphasizes **realism over idealization**:
- Real optical aberrations (spherical, chromatic, coma)
- Atmospheric seeing and turbulence
- Finite aperture diffraction
- Wavelength-dependent refraction
- Manufacturing approximations noted in code and outputs

The goal is to provide an authentic representation of how telescopes perform in practice, supporting real design decisions and teaching how optical systems work.

## License

(Add license information as appropriate)

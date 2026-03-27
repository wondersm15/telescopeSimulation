"""
Ray traces comparison tab for comparison mode.

Shows side-by-side ray traces of multiple telescope configurations.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QGroupBox, QScrollArea,
    QSizePolicy
)
from PyQt6.QtCore import Qt
import matplotlib.pyplot as plt

from telescope_gui.widgets.matplotlib_canvas import MatplotlibCanvas
from telescope_sim.geometry import (
    NewtonianTelescope, CassegrainTelescope, RefractingTelescope,
    MaksutovCassegrainTelescope, SchmidtCassegrainTelescope
)
from telescope_sim.plotting import plot_ray_trace
from telescope_sim.source.light_source import create_parallel_rays

SIDEBAR_WIDTH = 220


class RayTracesTab(QWidget):
    """Ray traces comparison tab - side-by-side ray traces."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Store telescope configurations
        self.configs = [
            {"label": "Telescope 1", "type": "newtonian", "diameter": 200.0, "fratio": 5.0},
            {"label": "Telescope 2", "type": "cassegrain", "diameter": 200.0, "fratio": 10.0},
        ]

        self.init_ui()

    def _create_sidebar(self, number):
        """Create a vertical sidebar with controls for one telescope.

        Args:
            number: 1 or 2, identifying which telescope.

        Returns:
            QScrollArea containing the sidebar widget.
        """
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(SIDEBAR_WIDTH)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Header
        header = QLabel(f"Telescope {number}")
        header.setStyleSheet("font-weight: bold; font-size: 12pt; padding-bottom: 4px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Controls group
        group = QGroupBox("Controls")
        grid = QGridLayout()
        grid.setContentsMargins(4, 8, 4, 4)
        grid.setVerticalSpacing(2)
        row = 0

        # Telescope Type
        grid.addWidget(QLabel("Telescope Type"), row, 0)
        row += 1
        type_combo = QComboBox()
        type_combo.addItems(["Newtonian", "Cassegrain", "Refractor", "Maksutov-Cassegrain", "Schmidt-Cassegrain"])
        if number == 2:
            type_combo.setCurrentText("Cassegrain")
        grid.addWidget(type_combo, row, 0)
        row += 1

        # Aperture
        grid.addWidget(QLabel("Aperture (mm)"), row, 0)
        row += 1
        diameter_spin = QDoubleSpinBox()
        diameter_spin.setRange(50.0, 500.0)
        diameter_spin.setValue(200.0)
        grid.addWidget(diameter_spin, row, 0)
        row += 1

        # f-ratio
        grid.addWidget(QLabel("f-ratio"), row, 0)
        row += 1
        fratio_spin = QDoubleSpinBox()
        fratio_spin.setRange(3.0, 15.0)
        fratio_spin.setValue(5.0 if number == 1 else 10.0)
        grid.addWidget(fratio_spin, row, 0)
        row += 1

        # Focal Length (derived from aperture * f-ratio, editable)
        focal_length_label = QLabel("Focal Length (mm)")
        grid.addWidget(focal_length_label, row, 0)
        row += 1
        focal_length_spin = QDoubleSpinBox()
        focal_length_spin.setRange(150.0, 7500.0)
        focal_length_spin.setDecimals(1)
        initial_fl = diameter_spin.value() * fratio_spin.value()
        focal_length_spin.setValue(initial_fl)
        grid.addWidget(focal_length_spin, row, 0)
        row += 1

        # Bidirectional sync: aperture or f-ratio → focal length, focal length → f-ratio
        guard = {"active": False}

        def on_aperture_or_fratio_changed(_=None, d=diameter_spin, f=fratio_spin, fl=focal_length_spin, g=guard):
            if g["active"]:
                return
            g["active"] = True
            fl.setValue(d.value() * f.value())
            g["active"] = False

        def on_focal_length_changed(_=None, d=diameter_spin, f=fratio_spin, fl=focal_length_spin, g=guard):
            if g["active"]:
                return
            g["active"] = True
            if d.value() > 0:
                f.setValue(fl.value() / d.value())
            g["active"] = False

        diameter_spin.valueChanged.connect(on_aperture_or_fratio_changed)
        fratio_spin.valueChanged.connect(on_aperture_or_fratio_changed)
        focal_length_spin.valueChanged.connect(on_focal_length_changed)

        # Primary type (reflectors only, Newtonian only)
        primary_label = QLabel("Primary")
        grid.addWidget(primary_label, row, 0)
        row += 1
        primary_combo = QComboBox()
        primary_combo.addItems(["Parabolic", "Spherical"])
        grid.addWidget(primary_combo, row, 0)
        row += 1

        # Objective type (refractors only)
        obj_label = QLabel("Objective")
        grid.addWidget(obj_label, row, 0)
        row += 1
        obj_combo = QComboBox()
        obj_combo.addItems(["Singlet", "Achromat", "APO Doublet", "APO Triplet (air-spaced)"])
        grid.addWidget(obj_combo, row, 0)
        row += 1

        # Spider Vanes (reflectors only)
        spider_label = QLabel("Spider Vanes")
        grid.addWidget(spider_label, row, 0)
        row += 1
        spider_spin = QSpinBox()
        spider_spin.setRange(0, 4)
        spider_spin.setValue(0)
        grid.addWidget(spider_spin, row, 0)
        row += 1

        # Vane Width (reflectors only)
        vane_width_label = QLabel("Vane Width (mm)")
        grid.addWidget(vane_width_label, row, 0)
        row += 1
        vane_width_spin = QDoubleSpinBox()
        vane_width_spin.setRange(0.5, 5.0)
        vane_width_spin.setSingleStep(0.5)
        vane_width_spin.setValue(2.0)
        grid.addWidget(vane_width_spin, row, 0)
        row += 1

        # Obstruction (reflectors only)
        obstruction_label = QLabel("Obstruction")
        grid.addWidget(obstruction_label, row, 0)
        row += 1
        obstruction_spin = QDoubleSpinBox()
        obstruction_spin.setRange(0.0, 0.5)
        obstruction_spin.setSingleStep(0.01)
        obstruction_spin.setValue(0.20 if number == 1 else 0.30)
        obstruction_spin.setDecimals(2)
        obstruction_spin.setToolTip("Secondary diameter / Primary diameter")
        grid.addWidget(obstruction_spin, row, 0)
        row += 1

        group.setLayout(grid)
        layout.addWidget(group)
        layout.addStretch()

        scroll.setWidget(container)

        # Store widget references using the naming convention: type{N}_combo, etc.
        suffix = str(number)
        setattr(self, f"type{suffix}_combo", type_combo)
        setattr(self, f"diameter{suffix}_spin", diameter_spin)
        setattr(self, f"fratio{suffix}_spin", fratio_spin)
        setattr(self, f"focal_length{suffix}_spin", focal_length_spin)
        setattr(self, f"primary{suffix}_label", primary_label)
        setattr(self, f"primary{suffix}_combo", primary_combo)
        setattr(self, f"obj{suffix}_label", obj_label)
        setattr(self, f"obj{suffix}_combo", obj_combo)
        setattr(self, f"spider{suffix}_label", spider_label)
        setattr(self, f"spider{suffix}_spin", spider_spin)
        setattr(self, f"vane_width{suffix}_label", vane_width_label)
        setattr(self, f"vane_width{suffix}_spin", vane_width_spin)
        setattr(self, f"obstruction{suffix}_label", obstruction_label)
        setattr(self, f"obstruction{suffix}_spin", obstruction_spin)

        # Connect visibility toggle
        type_combo.currentTextChanged.connect(self.update_controls_visibility)

        return scroll

    def init_ui(self):
        """Initialize the user interface."""
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # T1 sidebar (left)
        t1_sidebar = self._create_sidebar(1)
        main_layout.addWidget(t1_sidebar)

        # T1 ray trace canvas (stretches)
        self.canvas1 = MatplotlibCanvas(figsize=(8, 6))
        self.canvas1.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(self.canvas1, stretch=1)

        # T2 ray trace canvas (stretches)
        self.canvas2 = MatplotlibCanvas(figsize=(8, 6))
        self.canvas2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(self.canvas2, stretch=1)

        # T2 sidebar (right)
        t2_sidebar = self._create_sidebar(2)
        main_layout.addWidget(t2_sidebar)

        # Add update button at the bottom of T1 sidebar
        # (insert before the stretch in T1's container layout)
        t1_container = t1_sidebar.widget()
        t1_layout = t1_container.layout()
        self.update_button = QPushButton("Update Comparison")
        self.update_button.clicked.connect(self.update_view)
        # Insert before the stretch (which is the last item)
        t1_layout.insertWidget(t1_layout.count() - 1, self.update_button)

        self.setLayout(main_layout)

        # Set initial control visibility
        self.update_controls_visibility()

        # Initial render
        self.update_view()

    def update_controls_visibility(self):
        """Show/hide primary/objective/spider/obstruction controls based on telescope type."""
        # Telescope 1
        type1 = self.type1_combo.currentText()
        is_refractor1 = type1 == "Refractor"
        is_newtonian1 = type1 == "Newtonian"
        is_reflector1 = not is_refractor1

        self.primary1_label.setVisible(is_newtonian1)
        self.primary1_combo.setVisible(is_newtonian1)
        self.obj1_label.setVisible(is_refractor1)
        self.obj1_combo.setVisible(is_refractor1)
        self.spider1_label.setVisible(is_reflector1)
        self.spider1_spin.setVisible(is_reflector1)
        self.vane_width1_label.setVisible(is_reflector1)
        self.vane_width1_spin.setVisible(is_reflector1)
        self.obstruction1_label.setVisible(is_reflector1)
        self.obstruction1_spin.setVisible(is_reflector1)

        # Telescope 2
        type2 = self.type2_combo.currentText()
        is_refractor2 = type2 == "Refractor"
        is_newtonian2 = type2 == "Newtonian"
        is_reflector2 = not is_refractor2

        self.primary2_label.setVisible(is_newtonian2)
        self.primary2_combo.setVisible(is_newtonian2)
        self.obj2_label.setVisible(is_refractor2)
        self.obj2_combo.setVisible(is_refractor2)
        self.spider2_label.setVisible(is_reflector2)
        self.spider2_spin.setVisible(is_reflector2)
        self.vane_width2_label.setVisible(is_reflector2)
        self.vane_width2_spin.setVisible(is_reflector2)
        self.obstruction2_label.setVisible(is_reflector2)
        self.obstruction2_spin.setVisible(is_reflector2)

    def build_telescope(self, telescope_type, diameter, fratio, objective_type="singlet",
                       primary_type="parabolic", spider_vanes=0, spider_vane_width=2.0,
                       obstruction_ratio=0.20):
        """Build telescope object from configuration."""
        telescope_type = telescope_type.lower().replace("-", "")
        focal_length = diameter * fratio
        secondary_diameter = diameter * obstruction_ratio

        if telescope_type == "newtonian":
            return NewtonianTelescope(
                primary_diameter=diameter,
                focal_length=focal_length,
                primary_type=primary_type.lower(),
                spider_vanes=spider_vanes,
                spider_vane_width=spider_vane_width,
                secondary_minor_axis=secondary_diameter,
                enable_obstruction=obstruction_ratio > 0
            )
        elif telescope_type == "cassegrain":
            return CassegrainTelescope(
                primary_diameter=diameter,
                primary_focal_length=focal_length,
                secondary_magnification=3.0,
                spider_vanes=spider_vanes,
                spider_vane_width=spider_vane_width,
                secondary_minor_axis=secondary_diameter,
                enable_obstruction=obstruction_ratio > 0
            )
        elif telescope_type == "refractor":
            objective_map = {
                "singlet": "singlet",
                "achromat": "achromat",
                "apo doublet": "apo-doublet",
                "apo triplet (air-spaced)": "apo-triplet"
            }
            obj_type = objective_map.get(objective_type.lower(), "singlet")
            return RefractingTelescope(
                primary_diameter=diameter,
                focal_length=focal_length,
                objective_type=obj_type
            )
        elif telescope_type == "maksutovcassegrain":
            return MaksutovCassegrainTelescope(
                primary_diameter=diameter,
                primary_focal_length=focal_length,
                secondary_magnification=3.0,
                spider_vanes=spider_vanes,
                spider_vane_width=spider_vane_width,
                secondary_minor_axis=secondary_diameter,
                enable_obstruction=obstruction_ratio > 0
            )
        elif telescope_type == "schmidtcassegrain":
            return SchmidtCassegrainTelescope(
                primary_diameter=diameter,
                primary_focal_length=focal_length,
                secondary_magnification=3.0,
                spider_vanes=spider_vanes,
                spider_vane_width=spider_vane_width
            )
        else:
            return NewtonianTelescope(
                primary_diameter=diameter,
                focal_length=focal_length,
                spider_vanes=spider_vanes,
                spider_vane_width=spider_vane_width
            )

    def update_view(self):
        """Update ray trace comparison."""
        try:
            # Get configurations
            configs = [
                {
                    "type": self.type1_combo.currentText(),
                    "diameter": self.diameter1_spin.value(),
                    "fratio": self.fratio1_spin.value(),
                    "objective": self.obj1_combo.currentText(),
                    "primary": self.primary1_combo.currentText(),
                    "spider_vanes": self.spider1_spin.value(),
                    "spider_vane_width": self.vane_width1_spin.value(),
                    "obstruction_ratio": self.obstruction1_spin.value(),
                },
                {
                    "type": self.type2_combo.currentText(),
                    "diameter": self.diameter2_spin.value(),
                    "fratio": self.fratio2_spin.value(),
                    "objective": self.obj2_combo.currentText(),
                    "primary": self.primary2_combo.currentText(),
                    "spider_vanes": self.spider2_spin.value(),
                    "spider_vane_width": self.vane_width2_spin.value(),
                    "obstruction_ratio": self.obstruction2_spin.value(),
                },
            ]

            # First pass: create all figures and collect axis limits
            figures = []
            all_xlims = []
            all_ylims = []

            for config in configs:
                telescope = self.build_telescope(
                    config["type"],
                    config["diameter"],
                    config["fratio"],
                    config["objective"],
                    config["primary"],
                    config["spider_vanes"],
                    config["spider_vane_width"],
                    config["obstruction_ratio"]
                )

                # Create rays
                rays = create_parallel_rays(
                    num_rays=11,
                    aperture_diameter=telescope.primary_diameter,
                    entry_height=telescope.tube_length * 1.15,
                )
                telescope.trace_rays(rays)
                components = telescope.get_components_for_plotting()

                # Plot
                title = f"{telescope.primary_diameter:.0f}mm f/{telescope.focal_ratio:.1f} {config['type']}"
                fig = plot_ray_trace(rays, components, title=title)
                figures.append(fig)

                # Collect axis limits
                for ax in fig.axes:
                    all_xlims.append(ax.get_xlim())
                    all_ylims.append(ax.get_ylim())

            # Compute shared axis limits
            if all_xlims and all_ylims:
                shared_xlim = (min(lim[0] for lim in all_xlims),
                              max(lim[1] for lim in all_xlims))
                shared_ylim = (min(lim[0] for lim in all_ylims),
                              max(lim[1] for lim in all_ylims))

                # Apply shared limits to all figures
                for fig in figures:
                    for ax in fig.axes:
                        ax.set_xlim(shared_xlim)
                        ax.set_ylim(shared_ylim)

            # Update the pre-created canvases
            canvases = [self.canvas1, self.canvas2]
            for canvas, fig in zip(canvases, figures):
                canvas.set_figure(fig)
                plt.close(fig)

        except Exception as e:
            print(f"Error updating ray traces comparison: {e}")
            import traceback
            traceback.print_exc()

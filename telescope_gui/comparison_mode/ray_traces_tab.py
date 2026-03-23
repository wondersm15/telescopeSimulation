"""
Ray traces comparison tab for comparison mode.

Shows side-by-side ray traces of multiple telescope configurations.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QDoubleSpinBox, QGroupBox, QScrollArea
)
from PyQt6.QtCore import Qt
import matplotlib.pyplot as plt

from telescope_gui.widgets.matplotlib_canvas import MatplotlibCanvas
from telescope_sim.geometry import NewtonianTelescope, CassegrainTelescope, RefractingTelescope, MaksutovCassegrainTelescope
from telescope_sim.plotting import plot_ray_trace
from telescope_sim.source.light_source import create_parallel_rays


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

    def init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout()

        # Title
        title_label = QLabel("Ray Trace Comparison")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; padding: 10px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # Scroll area for plots
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.plots_layout = QHBoxLayout()
        scroll_widget.setLayout(self.plots_layout)
        scroll_area.setWidget(scroll_widget)

        main_layout.addWidget(scroll_area)

        # Controls
        controls_group = QGroupBox("Telescope Configurations")
        controls_layout = QVBoxLayout()

        # Configuration 1
        config1_layout = QGridLayout()
        config1_layout.addWidget(QLabel("Telescope 1:"), 0, 0)

        self.type1_combo = QComboBox()
        self.type1_combo.addItems(["Newtonian", "Cassegrain", "Refractor", "Maksutov-Cassegrain"])
        config1_layout.addWidget(self.type1_combo, 0, 1)

        config1_layout.addWidget(QLabel("Aperture (mm):"), 0, 2)
        self.diameter1_spin = QDoubleSpinBox()
        self.diameter1_spin.setRange(50.0, 500.0)
        self.diameter1_spin.setValue(200.0)
        config1_layout.addWidget(self.diameter1_spin, 0, 3)

        config1_layout.addWidget(QLabel("f-ratio:"), 0, 4)
        self.fratio1_spin = QDoubleSpinBox()
        self.fratio1_spin.setRange(3.0, 15.0)
        self.fratio1_spin.setValue(5.0)
        config1_layout.addWidget(self.fratio1_spin, 0, 5)

        # Primary type for telescope 1 (row 1, shown for reflectors)
        self.primary1_label = QLabel("Primary:")
        config1_layout.addWidget(self.primary1_label, 1, 0)
        self.primary1_combo = QComboBox()
        self.primary1_combo.addItems(["Parabolic", "Spherical"])
        config1_layout.addWidget(self.primary1_combo, 1, 1)

        # Objective type for telescope 1 (row 1, shown for refractors)
        self.obj1_label = QLabel("Objective:")
        config1_layout.addWidget(self.obj1_label, 1, 0)
        self.obj1_combo = QComboBox()
        self.obj1_combo.addItems(["Singlet", "Achromat", "APO Doublet", "APO Triplet (air-spaced)"])
        config1_layout.addWidget(self.obj1_combo, 1, 1)

        # Connect telescope type change to update control visibility
        self.type1_combo.currentTextChanged.connect(self.update_controls_visibility)

        controls_layout.addLayout(config1_layout)

        # Configuration 2
        config2_layout = QGridLayout()
        config2_layout.addWidget(QLabel("Telescope 2:"), 0, 0)

        self.type2_combo = QComboBox()
        self.type2_combo.addItems(["Newtonian", "Cassegrain", "Refractor", "Maksutov-Cassegrain"])
        self.type2_combo.setCurrentText("Cassegrain")
        config2_layout.addWidget(self.type2_combo, 0, 1)

        config2_layout.addWidget(QLabel("Aperture (mm):"), 0, 2)
        self.diameter2_spin = QDoubleSpinBox()
        self.diameter2_spin.setRange(50.0, 500.0)
        self.diameter2_spin.setValue(200.0)
        config2_layout.addWidget(self.diameter2_spin, 0, 3)

        config2_layout.addWidget(QLabel("f-ratio:"), 0, 4)
        self.fratio2_spin = QDoubleSpinBox()
        self.fratio2_spin.setRange(3.0, 15.0)
        self.fratio2_spin.setValue(10.0)
        config2_layout.addWidget(self.fratio2_spin, 0, 5)

        # Primary type for telescope 2 (row 1, shown for reflectors)
        self.primary2_label = QLabel("Primary:")
        config2_layout.addWidget(self.primary2_label, 1, 0)
        self.primary2_combo = QComboBox()
        self.primary2_combo.addItems(["Parabolic", "Spherical"])
        config2_layout.addWidget(self.primary2_combo, 1, 1)

        # Objective type for telescope 2 (row 1, shown for refractors)
        self.obj2_label = QLabel("Objective:")
        config2_layout.addWidget(self.obj2_label, 1, 0)
        self.obj2_combo = QComboBox()
        self.obj2_combo.addItems(["Singlet", "Achromat", "APO Doublet", "APO Triplet (air-spaced)"])
        config2_layout.addWidget(self.obj2_combo, 1, 1)

        # Connect telescope type change to update control visibility
        self.type2_combo.currentTextChanged.connect(self.update_controls_visibility)

        controls_layout.addLayout(config2_layout)

        # Update button
        self.update_button = QPushButton("Update Comparison")
        self.update_button.clicked.connect(self.update_view)
        controls_layout.addWidget(self.update_button)

        controls_group.setLayout(controls_layout)
        main_layout.addWidget(controls_group)

        self.setLayout(main_layout)

        # Set initial control visibility
        self.update_controls_visibility()

        # Initial render
        self.update_view()

    def update_controls_visibility(self):
        """Show/hide primary/objective controls based on telescope type."""
        # Telescope 1
        is_refractor1 = self.type1_combo.currentText() == "Refractor"
        self.primary1_label.setVisible(not is_refractor1)
        self.primary1_combo.setVisible(not is_refractor1)
        self.obj1_label.setVisible(is_refractor1)
        self.obj1_combo.setVisible(is_refractor1)

        # Telescope 2
        is_refractor2 = self.type2_combo.currentText() == "Refractor"
        self.primary2_label.setVisible(not is_refractor2)
        self.primary2_combo.setVisible(not is_refractor2)
        self.obj2_label.setVisible(is_refractor2)
        self.obj2_combo.setVisible(is_refractor2)

    def build_telescope(self, telescope_type, diameter, fratio, objective_type="singlet", primary_type="parabolic"):
        """Build telescope object from configuration."""
        telescope_type = telescope_type.lower().replace("-", "")
        focal_length = diameter * fratio

        # Determine mirror type for reflectors
        from telescope_sim.geometry.mirrors import ParabolicMirror, SphericalMirror
        mirror_type = ParabolicMirror if primary_type.lower() == "parabolic" else SphericalMirror

        if telescope_type == "newtonian":
            return NewtonianTelescope(
                primary_diameter=diameter,
                focal_length=focal_length,
                mirror_type=mirror_type
            )
        elif telescope_type == "cassegrain":
            return CassegrainTelescope(
                primary_diameter=diameter,
                primary_focal_length=focal_length,
                secondary_magnification=3.0,
                mirror_type=mirror_type
            )
        elif telescope_type == "refractor":
            # Map GUI labels to objective_type values
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
                secondary_magnification=3.0
            )
        else:
            return NewtonianTelescope(
                primary_diameter=diameter,
                focal_length=focal_length
            )

    def update_view(self):
        """Update ray trace comparison."""
        try:
            # Clear existing plots
            while self.plots_layout.count():
                child = self.plots_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            # Get configurations
            configs = [
                {
                    "type": self.type1_combo.currentText(),
                    "diameter": self.diameter1_spin.value(),
                    "fratio": self.fratio1_spin.value(),
                    "objective": self.obj1_combo.currentText(),
                    "primary": self.primary1_combo.currentText(),
                },
                {
                    "type": self.type2_combo.currentText(),
                    "diameter": self.diameter2_spin.value(),
                    "fratio": self.fratio2_spin.value(),
                    "objective": self.obj2_combo.currentText(),
                    "primary": self.primary2_combo.currentText(),
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
                    config["primary"]
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

            # Display all figures
            for fig in figures:
                canvas = MatplotlibCanvas(figsize=(7, 6))
                canvas.set_figure(fig)
                self.plots_layout.addWidget(canvas)
                plt.close(fig)

        except Exception as e:
            print(f"Error updating ray traces comparison: {e}")
            import traceback
            traceback.print_exc()

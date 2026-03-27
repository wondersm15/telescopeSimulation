"""
Simulated images comparison tab for comparison mode.

Shows side-by-side simulated images of multiple telescope configurations.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QDoubleSpinBox, QSpinBox, QGroupBox, QScrollArea
)
from PyQt6.QtCore import Qt
import matplotlib.pyplot as plt

from telescope_gui.widgets.matplotlib_canvas import MatplotlibCanvas
from telescope_sim.geometry import (
    NewtonianTelescope, CassegrainTelescope, RefractingTelescope,
    MaksutovCassegrainTelescope, SchmidtCassegrainTelescope
)
from telescope_sim.plotting import plot_source_image
from telescope_sim.source.sources import Jupiter, Moon, Saturn, StarField, PointSource


class ImagesTab(QWidget):
    """Simulated images comparison tab - side-by-side images."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout()

        # Title
        title_label = QLabel("Simulated Images Comparison")
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
        controls_group = QGroupBox("Configuration")
        controls_layout = QVBoxLayout()

        # Source selection
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Source:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems(["Jupiter", "Saturn", "Moon", "Star Field", "Point Source (Star)"])
        source_layout.addWidget(self.source_combo)

        source_layout.addWidget(QLabel("Seeing:"))
        self.seeing_combo = QComboBox()
        self.seeing_combo.addItems(["Excellent", "Good", "Average", "Poor", "None"])
        self.seeing_combo.setCurrentText("Good")
        source_layout.addWidget(self.seeing_combo)

        source_layout.addStretch()
        controls_layout.addLayout(source_layout)

        # Configuration 1
        config1_layout = QGridLayout()
        config1_layout.addWidget(QLabel("Telescope 1:"), 0, 0)

        self.type1_combo = QComboBox()
        self.type1_combo.addItems(["Newtonian", "Cassegrain", "Refractor", "Maksutov-Cassegrain", "Schmidt-Cassegrain"])
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

        # Spider vanes for telescope 1 (row 2, shown for reflectors)
        self.spider1_label = QLabel("Spider Vanes:")
        config1_layout.addWidget(self.spider1_label, 2, 0)
        self.spider1_spin = QSpinBox()
        self.spider1_spin.setRange(0, 4)
        self.spider1_spin.setValue(0)
        config1_layout.addWidget(self.spider1_spin, 2, 1)

        self.vane_width1_label = QLabel("Vane Width (mm):")
        config1_layout.addWidget(self.vane_width1_label, 2, 2)
        self.vane_width1_spin = QDoubleSpinBox()
        self.vane_width1_spin.setRange(0.5, 5.0)
        self.vane_width1_spin.setSingleStep(0.5)
        self.vane_width1_spin.setValue(2.0)
        config1_layout.addWidget(self.vane_width1_spin, 2, 3)

        # Obstruction controls for telescope 1 (row 2, cols 4-5)
        self.obstruction1_label = QLabel("Obstruction:")
        config1_layout.addWidget(self.obstruction1_label, 2, 4)
        self.obstruction1_spin = QDoubleSpinBox()
        self.obstruction1_spin.setRange(0.0, 0.5)
        self.obstruction1_spin.setSingleStep(0.01)
        self.obstruction1_spin.setValue(0.20)
        self.obstruction1_spin.setDecimals(2)
        self.obstruction1_spin.setToolTip("Secondary diameter / Primary diameter")
        config1_layout.addWidget(self.obstruction1_spin, 2, 5)

        # Connect telescope type change to update control visibility
        self.type1_combo.currentTextChanged.connect(self.update_controls_visibility)

        controls_layout.addLayout(config1_layout)

        # Configuration 2
        config2_layout = QGridLayout()
        config2_layout.addWidget(QLabel("Telescope 2:"), 0, 0)

        self.type2_combo = QComboBox()
        self.type2_combo.addItems(["Newtonian", "Cassegrain", "Refractor", "Maksutov-Cassegrain", "Schmidt-Cassegrain"])
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

        # Spider vanes for telescope 2 (row 2, shown for reflectors)
        self.spider2_label = QLabel("Spider Vanes:")
        config2_layout.addWidget(self.spider2_label, 2, 0)
        self.spider2_spin = QSpinBox()
        self.spider2_spin.setRange(0, 4)
        self.spider2_spin.setValue(0)
        config2_layout.addWidget(self.spider2_spin, 2, 1)

        self.vane_width2_label = QLabel("Vane Width (mm):")
        config2_layout.addWidget(self.vane_width2_label, 2, 2)
        self.vane_width2_spin = QDoubleSpinBox()
        self.vane_width2_spin.setRange(0.5, 5.0)
        self.vane_width2_spin.setSingleStep(0.5)
        self.vane_width2_spin.setValue(2.0)
        config2_layout.addWidget(self.vane_width2_spin, 2, 3)

        # Obstruction controls for telescope 2 (row 2, cols 4-5)
        self.obstruction2_label = QLabel("Obstruction:")
        config2_layout.addWidget(self.obstruction2_label, 2, 4)
        self.obstruction2_spin = QDoubleSpinBox()
        self.obstruction2_spin.setRange(0.0, 0.5)
        self.obstruction2_spin.setSingleStep(0.01)
        self.obstruction2_spin.setValue(0.30)
        self.obstruction2_spin.setDecimals(2)
        self.obstruction2_spin.setToolTip("Secondary diameter / Primary diameter")
        config2_layout.addWidget(self.obstruction2_spin, 2, 5)

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

    def get_source(self):
        """Get source object from selection."""
        source_type = self.source_combo.currentText().lower().replace(" ", "")
        if source_type == "jupiter":
            return Jupiter()
        elif source_type == "saturn":
            return Saturn()
        elif source_type == "moon":
            return Moon()
        elif source_type == "starfield":
            return StarField()
        elif source_type == "pointsource(star)":
            return PointSource()
        return None

    def get_seeing(self):
        """Get seeing value from selection."""
        seeing_presets = {
            "excellent": 0.8,
            "good": 1.5,
            "average": 2.5,
            "poor": 4.0,
            "none": None
        }
        seeing = self.seeing_combo.currentText().lower()
        return seeing_presets.get(seeing, None)

    def update_view(self):
        """Update simulated images comparison."""
        try:
            # Clear existing plots
            while self.plots_layout.count():
                child = self.plots_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            # Get source and seeing
            source = self.get_source()
            seeing = self.get_seeing()

            if source is None:
                return

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

            # Create and display images
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

                # Generate image
                result = plot_source_image(
                    telescope,
                    source,
                    seeing_arcsec=seeing
                )

                # Handle list or single figure
                if isinstance(result, list):
                    fig = result[0]
                    if len(result) > 1:
                        plt.close(result[1])
                else:
                    fig = result

                # Add to layout
                canvas = MatplotlibCanvas(figsize=(8, 6))
                canvas.set_figure(fig)
                self.plots_layout.addWidget(canvas)
                plt.close(fig)

        except Exception as e:
            print(f"Error updating images comparison: {e}")
            import traceback
            traceback.print_exc()

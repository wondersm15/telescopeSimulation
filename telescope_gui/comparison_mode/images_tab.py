"""
Simulated images comparison tab for comparison mode.

Shows side-by-side simulated images of multiple telescope configurations.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QDoubleSpinBox, QGroupBox, QScrollArea
)
from PyQt6.QtCore import Qt
import matplotlib.pyplot as plt

from telescope_gui.widgets.matplotlib_canvas import MatplotlibCanvas
from telescope_sim.geometry import NewtonianTelescope, CassegrainTelescope, RefractingTelescope, MaksutovCassegrainTelescope
from telescope_sim.plotting import plot_source_image
from telescope_sim.source.sources import Jupiter, Moon


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
        self.source_combo.addItems(["Jupiter", "Moon"])
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

        controls_layout.addLayout(config2_layout)

        # Update button
        self.update_button = QPushButton("Update Comparison")
        self.update_button.clicked.connect(self.update_view)
        controls_layout.addWidget(self.update_button)

        controls_group.setLayout(controls_layout)
        main_layout.addWidget(controls_group)

        self.setLayout(main_layout)

        # Initial render
        self.update_view()

    def build_telescope(self, telescope_type, diameter, fratio):
        """Build telescope object from configuration."""
        telescope_type = telescope_type.lower().replace("-", "")
        focal_length = diameter * fratio

        if telescope_type == "newtonian":
            return NewtonianTelescope(
                primary_diameter=diameter,
                focal_length=focal_length
            )
        elif telescope_type == "cassegrain":
            return CassegrainTelescope(
                primary_diameter=diameter,
                primary_focal_length=focal_length,
                secondary_magnification=3.0
            )
        elif telescope_type == "refractor":
            return RefractingTelescope(
                primary_diameter=diameter,
                focal_length=focal_length
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

    def get_source(self):
        """Get source object from selection."""
        source_type = self.source_combo.currentText().lower()
        if source_type == "jupiter":
            return Jupiter()
        elif source_type == "moon":
            return Moon()
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
                },
                {
                    "type": self.type2_combo.currentText(),
                    "diameter": self.diameter2_spin.value(),
                    "fratio": self.fratio2_spin.value(),
                },
            ]

            # Create and display images
            for config in configs:
                telescope = self.build_telescope(
                    config["type"],
                    config["diameter"],
                    config["fratio"]
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
                canvas = MatplotlibCanvas(figsize=(6, 6))
                canvas.set_figure(fig)
                self.plots_layout.addWidget(canvas)
                plt.close(fig)

        except Exception as e:
            print(f"Error updating images comparison: {e}")
            import traceback
            traceback.print_exc()

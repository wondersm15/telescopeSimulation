"""
Analytics comparison tab for comparison mode.

Shows comparative metrics and charts for multiple telescope configurations.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QDoubleSpinBox, QGroupBox, QTableWidget, QTableWidgetItem
)
from PyQt6.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from telescope_gui.widgets.matplotlib_canvas import MatplotlibCanvas
from telescope_sim.geometry import NewtonianTelescope, CassegrainTelescope, RefractingTelescope, MaksutovCassegrainTelescope


class AnalyticsTab(QWidget):
    """Analytics comparison tab - comparative metrics and charts."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout()

        # Title
        title_label = QLabel("Analytics & Metrics Comparison")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; padding: 10px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # Top: Comparison table
        table_label = QLabel("Performance Metrics")
        table_label.setStyleSheet("font-weight: bold; font-size: 12pt; padding: 5px;")
        main_layout.addWidget(table_label)

        self.metrics_table = QTableWidget()
        self.metrics_table.setMaximumHeight(200)
        main_layout.addWidget(self.metrics_table)

        # Bottom: Charts
        charts_layout = QHBoxLayout()

        # Left: Resolution comparison chart
        resolution_container = QVBoxLayout()
        resolution_label = QLabel("Resolution Limits")
        resolution_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        resolution_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        resolution_container.addWidget(resolution_label)

        self.resolution_canvas = MatplotlibCanvas(figsize=(6, 5))
        resolution_container.addWidget(self.resolution_canvas)
        charts_layout.addLayout(resolution_container)

        # Right: Light gathering comparison chart
        light_container = QVBoxLayout()
        light_label = QLabel("Light Gathering Power")
        light_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        light_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        light_container.addWidget(light_label)

        self.light_canvas = MatplotlibCanvas(figsize=(6, 5))
        light_container.addWidget(self.light_canvas)
        charts_layout.addLayout(light_container)

        main_layout.addLayout(charts_layout)

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
        self.update_button = QPushButton("Update Analytics")
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

    def calculate_metrics(self, telescope, label):
        """Calculate performance metrics for a telescope."""
        wavelength_nm = 550.0
        wavelength_m = wavelength_nm * 1e-9
        aperture_m = telescope.primary_diameter * 1e-3

        # Resolution limits
        rayleigh_arcsec = 1.22 * wavelength_m / aperture_m * 206265
        dawes_arcsec = 116.0 / telescope.primary_diameter

        # Light gathering (relative to human eye with 7mm pupil)
        human_eye_area = 3.14159 * (7.0/2)**2
        telescope_area = 3.14159 * (telescope.primary_diameter/2)**2
        light_gathering = telescope_area / human_eye_area

        # Limiting magnitude (approximate formula)
        limiting_mag = 2.0 + 5.0 * (telescope.primary_diameter / 7.0) ** 0.4

        return {
            "label": label,
            "aperture": telescope.primary_diameter,
            "focal_length": telescope.focal_length,
            "f_ratio": telescope.focal_ratio,
            "rayleigh": rayleigh_arcsec,
            "dawes": dawes_arcsec,
            "light_gathering": light_gathering,
            "limiting_mag": limiting_mag,
        }

    def update_metrics_table(self, metrics_list):
        """Update the metrics comparison table."""
        # Set up table
        self.metrics_table.setRowCount(len(metrics_list))
        self.metrics_table.setColumnCount(7)
        self.metrics_table.setHorizontalHeaderLabels([
            "Telescope", "Aperture (mm)", "Focal Length (mm)", "f-ratio",
            "Rayleigh (\")", "Dawes (\")", "Light Gathering (×eye)"
        ])

        # Fill table
        for i, metrics in enumerate(metrics_list):
            self.metrics_table.setItem(i, 0, QTableWidgetItem(metrics["label"]))
            self.metrics_table.setItem(i, 1, QTableWidgetItem(f"{metrics['aperture']:.0f}"))
            self.metrics_table.setItem(i, 2, QTableWidgetItem(f"{metrics['focal_length']:.0f}"))
            self.metrics_table.setItem(i, 3, QTableWidgetItem(f"{metrics['f_ratio']:.1f}"))
            self.metrics_table.setItem(i, 4, QTableWidgetItem(f"{metrics['rayleigh']:.2f}"))
            self.metrics_table.setItem(i, 5, QTableWidgetItem(f"{metrics['dawes']:.2f}"))
            self.metrics_table.setItem(i, 6, QTableWidgetItem(f"{metrics['light_gathering']:.0f}×"))

        self.metrics_table.resizeColumnsToContents()

    def plot_resolution_comparison(self, metrics_list):
        """Create resolution comparison bar chart."""
        fig = Figure(figsize=(6, 5))
        ax = fig.add_subplot(111)

        labels = [m["label"] for m in metrics_list]
        rayleigh = [m["rayleigh"] for m in metrics_list]
        dawes = [m["dawes"] for m in metrics_list]

        x = range(len(labels))
        width = 0.35

        ax.bar([i - width/2 for i in x], rayleigh, width, label='Rayleigh Criterion', color='skyblue')
        ax.bar([i + width/2 for i in x], dawes, width, label='Dawes Limit', color='lightcoral')

        ax.set_ylabel('Resolution (arcseconds)')
        ax.set_title('Resolution Comparison\n(Lower is better)')
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)

        fig.tight_layout()
        return fig

    def plot_light_gathering_comparison(self, metrics_list):
        """Create light gathering comparison bar chart."""
        fig = Figure(figsize=(6, 5))
        ax = fig.add_subplot(111)

        labels = [m["label"] for m in metrics_list]
        light_gathering = [m["light_gathering"] for m in metrics_list]

        ax.bar(labels, light_gathering, color='gold', edgecolor='darkorange', linewidth=2)

        ax.set_ylabel('Light Gathering Power (× human eye)')
        ax.set_title('Light Gathering Comparison\n(Higher is better)')
        ax.grid(axis='y', alpha=0.3)

        fig.tight_layout()
        return fig

    def update_view(self):
        """Update analytics comparison."""
        try:
            # Get configurations
            configs = [
                {
                    "label": f"{self.type1_combo.currentText()} 1",
                    "type": self.type1_combo.currentText(),
                    "diameter": self.diameter1_spin.value(),
                    "fratio": self.fratio1_spin.value(),
                },
                {
                    "label": f"{self.type2_combo.currentText()} 2",
                    "type": self.type2_combo.currentText(),
                    "diameter": self.diameter2_spin.value(),
                    "fratio": self.fratio2_spin.value(),
                },
            ]

            # Build telescopes and calculate metrics
            metrics_list = []
            for config in configs:
                telescope = self.build_telescope(
                    config["type"],
                    config["diameter"],
                    config["fratio"]
                )
                metrics = self.calculate_metrics(telescope, config["label"])
                metrics_list.append(metrics)

            # Update table
            self.update_metrics_table(metrics_list)

            # Update resolution chart
            fig_resolution = self.plot_resolution_comparison(metrics_list)
            self.resolution_canvas.set_figure(fig_resolution)
            plt.close(fig_resolution)

            # Update light gathering chart
            fig_light = self.plot_light_gathering_comparison(metrics_list)
            self.light_canvas.set_figure(fig_light)
            plt.close(fig_light)

        except Exception as e:
            print(f"Error updating analytics comparison: {e}")
            import traceback
            traceback.print_exc()

"""
Analytics comparison tab for comparison mode.

Shows comparative metrics and charts for multiple telescope configurations.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QDoubleSpinBox, QSpinBox, QGroupBox, QTableWidget, QTableWidgetItem,
    QFrame
)
from PyQt6.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from telescope_gui.widgets.matplotlib_canvas import MatplotlibCanvas
from telescope_sim.geometry import (
    NewtonianTelescope, CassegrainTelescope, RefractingTelescope,
    MaksutovCassegrainTelescope, SchmidtCassegrainTelescope
)


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
        self.metrics_table.setMaximumHeight(150)
        main_layout.addWidget(self.metrics_table)

        # Charts: all 3 in one row
        charts_layout = QHBoxLayout()

        # Resolution comparison chart
        resolution_container = QVBoxLayout()
        resolution_label = QLabel("Resolution Limits")
        resolution_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        resolution_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        resolution_container.addWidget(resolution_label)

        self.resolution_canvas = MatplotlibCanvas(figsize=(5, 4))
        resolution_container.addWidget(self.resolution_canvas)
        charts_layout.addLayout(resolution_container)

        # Light gathering comparison chart
        light_container = QVBoxLayout()
        light_label = QLabel("Light Gathering Power")
        light_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        light_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        light_container.addWidget(light_label)

        self.light_canvas = MatplotlibCanvas(figsize=(5, 4))
        light_container.addWidget(self.light_canvas)
        charts_layout.addLayout(light_container)

        # PSF Comparison (same row)
        psf_container = QVBoxLayout()
        psf_label = QLabel("PSF Comparison")
        psf_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        psf_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        psf_container.addWidget(psf_label)

        self.psf_canvas = MatplotlibCanvas(figsize=(5, 4))
        psf_container.addWidget(self.psf_canvas)
        charts_layout.addLayout(psf_container)

        main_layout.addLayout(charts_layout)

        # Controls
        controls_group = QGroupBox("Telescope Configurations")
        controls_layout = QVBoxLayout()

        # Telescope 1 header
        t1_header = QLabel("Telescope 1")
        t1_header.setStyleSheet("font-weight: bold; font-size: 11pt; padding: 2px 0;")
        controls_layout.addWidget(t1_header)

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

        # Separator between T1 and T2
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setLineWidth(2)
        separator.setStyleSheet("QFrame { color: #555555; }")
        controls_layout.addWidget(separator)

        # Telescope 2 header
        t2_header = QLabel("Telescope 2")
        t2_header.setStyleSheet("font-weight: bold; font-size: 11pt; padding: 2px 0;")
        controls_layout.addWidget(t2_header)

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
        self.update_button = QPushButton("Update Analytics")
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
        fig = Figure(figsize=(5, 4))
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
        fig = Figure(figsize=(5, 4))
        ax = fig.add_subplot(111)

        labels = [m["label"] for m in metrics_list]
        light_gathering = [m["light_gathering"] for m in metrics_list]

        ax.bar(labels, light_gathering, color='gold', edgecolor='darkorange', linewidth=2)

        ax.set_ylabel('Light Gathering Power (× human eye)')
        ax.set_title('Light Gathering Comparison\n(Higher is better)')
        ax.grid(axis='y', alpha=0.3)

        fig.tight_layout()
        return fig

    def plot_psf_comparison(self, telescopes, labels):
        """Create overlaid 1D PSF profile comparison."""
        from telescope_sim.physics.diffraction import compute_psf
        import numpy as np

        fig = Figure(figsize=(5, 4))
        ax = fig.add_subplot(111)

        wavelength_nm = 550.0
        wavelength_mm = wavelength_nm * 1e-6

        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

        for i, (telescope, label) in enumerate(zip(telescopes, labels)):
            aperture = telescope.primary_diameter
            focal_length = telescope.focal_length
            f_ratio = focal_length / aperture
            airy_radius = 1.22 * wavelength_mm * f_ratio
            obs_ratio = telescope.obstruction_ratio

            # Generate radial profile
            r_max = airy_radius * 6
            r = np.linspace(0, r_max, 1000)
            psf = compute_psf(r, aperture, focal_length, wavelength_mm, obs_ratio)

            # Normalize
            psf_norm = psf / np.max(psf)

            color = colors[i % len(colors)]
            ax.plot(r * 1000, psf_norm, label=label, color=color, linewidth=2)

        ax.set_xlabel('Radius (μm)')
        ax.set_ylabel('Normalized Intensity')
        ax.set_title('PSF Radial Profile Comparison (550nm)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_xlim(left=0)

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
                    "objective": self.obj1_combo.currentText(),
                    "primary": self.primary1_combo.currentText(),
                    "spider_vanes": self.spider1_spin.value(),
                    "spider_vane_width": self.vane_width1_spin.value(),
                    "obstruction_ratio": self.obstruction1_spin.value(),
                },
                {
                    "label": f"{self.type2_combo.currentText()} 2",
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

            # Build telescopes and calculate metrics
            metrics_list = []
            telescopes = []
            labels = []
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
                telescopes.append(telescope)
                labels.append(config["label"])
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

            # Update PSF comparison
            fig_psf = self.plot_psf_comparison(telescopes, labels)
            self.psf_canvas.set_figure(fig_psf)
            plt.close(fig_psf)

        except Exception as e:
            print(f"Error updating analytics comparison: {e}")
            import traceback
            traceback.print_exc()

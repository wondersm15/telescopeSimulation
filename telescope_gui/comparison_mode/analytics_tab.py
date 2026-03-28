"""
Analytics comparison tab for comparison mode.

Shows comparative metrics and charts for multiple telescope configurations.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np

from telescope_gui.widgets.matplotlib_canvas import MatplotlibCanvas
from telescope_gui.widgets.telescope_controls import TelescopeControlPanel
from telescope_gui.telescope_builder import build_telescope

SIDEBAR_WIDTH = 220


class AnalyticsTab(QWidget):
    """Analytics comparison tab - comparative metrics and charts."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # ---- T1 sidebar (left) ----
        t1_scroll = QScrollArea()
        t1_scroll.setWidgetResizable(True)
        t1_scroll.setFixedWidth(SIDEBAR_WIDTH)
        t1_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        t1_container = QWidget()
        t1_layout = QVBoxLayout(t1_container)
        t1_layout.setContentsMargins(6, 6, 6, 6)
        t1_layout.setSpacing(4)

        header1 = QLabel("Telescope 1")
        header1.setStyleSheet("font-weight: bold; font-size: 12pt; padding-bottom: 4px;")
        header1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t1_layout.addWidget(header1)

        self.panel1 = TelescopeControlPanel(
            number=1, layout_mode="sidebar", show_group_box=True,
            default_type="Newtonian", default_fratio=5.0
        )
        t1_layout.addWidget(self.panel1)

        self.update_button = QPushButton("Update Analytics")
        self.update_button.clicked.connect(self.update_view)
        t1_layout.addWidget(self.update_button)

        t1_layout.addStretch()
        t1_scroll.setWidget(t1_container)
        main_layout.addWidget(t1_scroll)

        # ---- Center content area ----
        center_widget = QWidget()
        center_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(4, 4, 4, 4)

        # Title
        title_label = QLabel("Analytics & Metrics Comparison")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 4px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(title_label)

        # Metrics table
        self.metrics_table = QTableWidget()
        self.metrics_table.setMaximumHeight(150)
        center_layout.addWidget(self.metrics_table)

        # Charts row: all 3 side by side
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

        # PSF Comparison
        psf_container = QVBoxLayout()
        psf_label = QLabel("PSF Comparison")
        psf_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        psf_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        psf_container.addWidget(psf_label)
        self.psf_canvas = MatplotlibCanvas(figsize=(5, 4))
        psf_container.addWidget(self.psf_canvas)
        charts_layout.addLayout(psf_container)

        center_layout.addLayout(charts_layout, stretch=1)
        main_layout.addWidget(center_widget, stretch=1)

        # ---- T2 sidebar (right) ----
        t2_scroll = QScrollArea()
        t2_scroll.setWidgetResizable(True)
        t2_scroll.setFixedWidth(SIDEBAR_WIDTH)
        t2_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        t2_container = QWidget()
        t2_layout = QVBoxLayout(t2_container)
        t2_layout.setContentsMargins(6, 6, 6, 6)
        t2_layout.setSpacing(4)

        header2 = QLabel("Telescope 2")
        header2.setStyleSheet("font-weight: bold; font-size: 12pt; padding-bottom: 4px;")
        header2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t2_layout.addWidget(header2)

        self.panel2 = TelescopeControlPanel(
            number=2, layout_mode="sidebar", show_group_box=True,
            default_type="Cassegrain", default_fratio=10.0
        )
        t2_layout.addWidget(self.panel2)

        t2_layout.addStretch()
        t2_scroll.setWidget(t2_container)
        main_layout.addWidget(t2_scroll)

        self.setLayout(main_layout)

        # Initial render
        self.update_view()

    def calculate_metrics(self, telescope, label):
        """Calculate performance metrics for a telescope."""
        wavelength_nm = 550.0
        wavelength_m = wavelength_nm * 1e-9
        aperture_m = telescope.primary_diameter * 1e-3

        rayleigh_arcsec = 1.22 * wavelength_m / aperture_m * 206265
        dawes_arcsec = 116.0 / telescope.primary_diameter

        human_eye_area = 3.14159 * (7.0/2)**2
        telescope_area = 3.14159 * (telescope.primary_diameter/2)**2
        light_gathering = telescope_area / human_eye_area

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
        self.metrics_table.setRowCount(len(metrics_list))
        self.metrics_table.setColumnCount(7)
        self.metrics_table.setHorizontalHeaderLabels([
            "Telescope", "Aperture (mm)", "Focal Length (mm)", "f-ratio",
            "Rayleigh (\")", "Dawes (\")", "Light Gathering (\u00d7eye)"
        ])

        for i, metrics in enumerate(metrics_list):
            self.metrics_table.setItem(i, 0, QTableWidgetItem(metrics["label"]))
            self.metrics_table.setItem(i, 1, QTableWidgetItem(f"{metrics['aperture']:.0f}"))
            self.metrics_table.setItem(i, 2, QTableWidgetItem(f"{metrics['focal_length']:.0f}"))
            self.metrics_table.setItem(i, 3, QTableWidgetItem(f"{metrics['f_ratio']:.1f}"))
            self.metrics_table.setItem(i, 4, QTableWidgetItem(f"{metrics['rayleigh']:.2f}"))
            self.metrics_table.setItem(i, 5, QTableWidgetItem(f"{metrics['dawes']:.2f}"))
            self.metrics_table.setItem(i, 6, QTableWidgetItem(f"{metrics['light_gathering']:.0f}\u00d7"))

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

        ax.set_ylabel('Light Gathering Power (\u00d7 human eye)')
        ax.set_title('Light Gathering Comparison\n(Higher is better)')
        ax.grid(axis='y', alpha=0.3)

        fig.tight_layout()
        return fig

    def plot_psf_comparison(self, telescopes, labels):
        """Create overlaid 1D PSF profile comparison."""
        from telescope_sim.physics.diffraction import compute_psf

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

            r_max = airy_radius * 6
            r = np.linspace(0, r_max, 1000)
            psf = compute_psf(r, aperture, focal_length, wavelength_mm, obs_ratio)

            psf_norm = psf / np.max(psf)

            color = colors[i % len(colors)]
            ax.plot(r * 1000, psf_norm, label=label, color=color, linewidth=2)

        ax.set_xlabel('Radius (\u03bcm)')
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
            panels = [self.panel1, self.panel2]

            metrics_list = []
            telescopes = []
            labels = []

            for i, panel in enumerate(panels, 1):
                telescope = panel.build()
                ttype = panel.type_combo.currentText()
                label = f"{ttype} {i}"

                telescopes.append(telescope)
                labels.append(label)
                metrics = self.calculate_metrics(telescope, label)
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

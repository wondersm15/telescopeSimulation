"""
Performance tab for single telescope mode.

Shows PSF analysis, spot diagram, and performance metrics.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QDoubleSpinBox, QGroupBox, QCheckBox, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt
import matplotlib.pyplot as plt
import numpy as np

from telescope_gui.widgets.matplotlib_canvas import MatplotlibCanvas
from telescope_gui.widgets.telescope_controls import TelescopeControlPanel
from telescope_gui.telescope_builder import build_telescope
from telescope_sim.plotting import (
    plot_psf_2d, plot_psf_profile, plot_spot_diagram,
    plot_coma_field_analysis, plot_vignetting_curve
)
from telescope_sim.physics.diffraction import rayleigh_criterion_arcsec
from matplotlib.figure import Figure
from scipy.signal import fftconvolve


class PerformanceTab(QWidget):
    """Performance tab - PSF analysis and metrics."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # PSF display options
        self.psf_mode = "2d"  # "1d" or "2d"
        self.psf_scale = "log"  # "log" or "linear"
        self.lock_psf_axes = False

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout()

        # Top section: Plots + Info sidebar
        top_layout = QHBoxLayout()

        # Left: PSF
        self.psf_widget = QWidget()
        psf_container = QVBoxLayout()
        psf_container.setContentsMargins(0, 0, 0, 0)
        self.psf_label_header = QLabel("Point Spread Function (PSF)")
        self.psf_label_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.psf_label_header.setStyleSheet("font-weight: bold; font-size: 12pt;")
        psf_container.addWidget(self.psf_label_header)

        self.psf_canvas = MatplotlibCanvas(figsize=(6, 6))
        psf_container.addWidget(self.psf_canvas)
        self.psf_widget.setLayout(psf_container)
        top_layout.addWidget(self.psf_widget)

        # Center: Spot Diagram
        self.spot_widget = QWidget()
        spot_container = QVBoxLayout()
        spot_container.setContentsMargins(0, 0, 0, 0)
        self.spot_label_header = QLabel("Spot Diagram")
        self.spot_label_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spot_label_header.setStyleSheet("font-weight: bold; font-size: 12pt;")
        spot_container.addWidget(self.spot_label_header)

        self.spot_canvas = MatplotlibCanvas(figsize=(6, 6))
        spot_container.addWidget(self.spot_canvas)
        self.spot_widget.setLayout(spot_container)
        top_layout.addWidget(self.spot_widget)

        # Right: Info sidebar
        sidebar = QVBoxLayout()
        sidebar_widget = QWidget()
        sidebar_widget.setMaximumWidth(300)

        # Analysis View dropdown
        analysis_group = QGroupBox("Analysis View")
        analysis_layout = QVBoxLayout()
        self.analysis_combo = QComboBox()
        self.analysis_combo.addItems([
            "PSF + Spot Diagram",
            "Coma Field Analysis",
            "Vignetting Curve"
        ])
        self.analysis_combo.currentTextChanged.connect(self.on_analysis_view_changed)
        analysis_layout.addWidget(self.analysis_combo)
        analysis_group.setLayout(analysis_layout)
        sidebar.addWidget(analysis_group)

        # Metrics display
        self.metrics_label = QLabel("Click 'Update Analysis' to compute performance metrics")
        self.metrics_label.setWordWrap(True)
        self.metrics_label.setStyleSheet("font-size: 10pt; padding: 6px; background-color: #f0f0f0; color: #222;")
        sidebar.addWidget(self.metrics_label)

        # Explanation label
        explanation = QLabel(
            "<b>PSF</b>: How a point source appears "
            "due to <i>diffraction</i> (wave optics).<br>"
            "<b>Spot Diagram</b>: Where rays converge due to <i>geometry</i> "
            "(geometric optics).<br>"
            "<b>Combined</b>: image = spot \u2297 PSF."
        )
        explanation.setWordWrap(True)
        explanation.setStyleSheet("font-size: 8pt; padding: 4px; background-color: #e8f4f8; color: #004488;")
        sidebar.addWidget(explanation)

        # Physics info panel
        physics_info = QLabel(
            "<b>Included:</b><ul style='margin:2px 0px; padding-left:16px;'>"
            "<li>Diffraction</li>"
            "<li>Obstruction</li>"
            "<li>Spider vanes</li>"
            "<li>Chromatic aberration</li>"
            "<li>Coma</li>"
            "<li>Spherical aberration</li>"
            "</ul>"
            "<b>Not Included:</b><ul style='margin:2px 0px; padding-left:16px;'>"
            "<li>Astigmatism</li>"
            "<li>Field curvature</li>"
            "<li>Seeing</li>"
            "</ul>"
        )
        physics_info.setWordWrap(True)
        physics_info.setStyleSheet("font-size: 8pt; padding: 4px; background-color: #f5f5f5; color: #222;")
        sidebar.addWidget(physics_info)

        # PSF Display Options (grid layout for proper spacing)
        self.psf_options_group = QGroupBox("PSF Display Options")
        psf_grid = QGridLayout()
        psf_grid.setSpacing(4)

        # Row 0: Type: | 1D | 2D
        psf_grid.addWidget(QLabel("Type:"), 0, 0)
        self.psf_1d_radio = QRadioButton("1D")
        self.psf_2d_radio = QRadioButton("2D")
        self.psf_2d_radio.setChecked(True)
        self.psf_mode_group = QButtonGroup()
        self.psf_mode_group.addButton(self.psf_1d_radio)
        self.psf_mode_group.addButton(self.psf_2d_radio)
        psf_grid.addWidget(self.psf_1d_radio, 0, 1)
        psf_grid.addWidget(self.psf_2d_radio, 0, 2)

        # Row 1: Scale: | Log | Linear
        psf_grid.addWidget(QLabel("Scale:"), 1, 0)
        self.psf_log_radio = QRadioButton("Log")
        self.psf_linear_radio = QRadioButton("Linear")
        self.psf_log_radio.setChecked(True)
        self.psf_scale_group = QButtonGroup()
        self.psf_scale_group.addButton(self.psf_log_radio)
        self.psf_scale_group.addButton(self.psf_linear_radio)
        psf_grid.addWidget(self.psf_log_radio, 1, 1)
        psf_grid.addWidget(self.psf_linear_radio, 1, 2)

        # Row 2: Lock PSF Axes checkbox (full width)
        self.lock_axes_check = QCheckBox("Lock PSF Axes")
        self.lock_axes_check.setToolTip("Keep PSF plot axes fixed when updating parameters")
        psf_grid.addWidget(self.lock_axes_check, 2, 0, 1, 3)

        # Row 3: Auto-scale Intensity checkbox (full width)
        self.autoscale_psf_check = QCheckBox("Auto-scale Intensity")
        self.autoscale_psf_check.setToolTip("Automatically adjust color scale to show full dynamic range")
        self.autoscale_psf_check.setChecked(False)
        self.autoscale_psf_check.toggled.connect(self.on_psf_options_changed)
        psf_grid.addWidget(self.autoscale_psf_check, 3, 0, 1, 3)

        self.psf_options_group.setLayout(psf_grid)
        sidebar.addWidget(self.psf_options_group)

        sidebar.addStretch()
        sidebar_widget.setLayout(sidebar)
        top_layout.addWidget(sidebar_widget)

        main_layout.addLayout(top_layout)

        # Connect PSF option changes to auto-update
        self.psf_1d_radio.toggled.connect(self.on_psf_options_changed)
        self.psf_2d_radio.toggled.connect(self.on_psf_options_changed)
        self.psf_log_radio.toggled.connect(self.on_psf_options_changed)
        self.psf_linear_radio.toggled.connect(self.on_psf_options_changed)

        # Connect lock axes checkbox
        self.lock_axes_check.toggled.connect(self.on_lock_axes_toggled)

        # Bottom: Shared telescope controls (grid layout) + wavelength + update button
        bottom_layout = QVBoxLayout()

        self.telescope_panel = TelescopeControlPanel(
            number=1, layout_mode="grid", show_group_box=True
        )
        bottom_layout.addWidget(self.telescope_panel)

        # Wavelength + Update button row
        extra_row = QHBoxLayout()
        extra_row.addWidget(QLabel("\u03bb (nm):"))
        self.wavelength_spin = QDoubleSpinBox()
        self.wavelength_spin.setRange(400.0, 700.0)
        self.wavelength_spin.setSingleStep(10.0)
        self.wavelength_spin.setValue(550.0)
        extra_row.addWidget(self.wavelength_spin)

        extra_row.addStretch()
        self.update_button = QPushButton("Update Analysis")
        self.update_button.clicked.connect(self.update_view)
        extra_row.addWidget(self.update_button)

        bottom_layout.addLayout(extra_row)
        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)

        # Initial render
        self.update_view()

    def on_lock_axes_toggled(self, checked):
        """Handle lock axes checkbox toggle."""
        pass

    def on_analysis_view_changed(self, view_name):
        """Show/hide canvases based on selected analysis view."""
        is_default = view_name == "PSF + Spot Diagram"

        self.spot_widget.setVisible(is_default)
        self.psf_options_group.setVisible(is_default)

        if is_default:
            self.psf_label_header.setText("Point Spread Function (PSF)")
        elif view_name == "Coma Field Analysis":
            self.psf_label_header.setText("Coma Field Analysis")
        elif view_name == "Vignetting Curve":
            self.psf_label_header.setText("Vignetting Curve")

        self.update_view()

    def on_psf_options_changed(self):
        """Handle PSF display option changes - auto-update view."""
        if hasattr(self, 'update_button'):
            self.update_view()

    def calculate_metrics(self, telescope):
        """Calculate performance metrics with breakdown of contributions."""
        wavelength_nm = self.wavelength_spin.value()
        wavelength_m = wavelength_nm * 1e-9
        aperture_m = telescope.primary_diameter * 1e-3
        plate_scale = 206265.0 / telescope.focal_length

        # Diffraction limit — pure aperture (no obstruction)
        rayleigh_base = rayleigh_criterion_arcsec(wavelength_m, aperture_m, 0.0)

        # Diffraction limit — with obstruction
        obstruction_ratio = telescope.obstruction_ratio if hasattr(telescope, 'obstruction_ratio') else 0.0
        rayleigh_with_obs = rayleigh_criterion_arcsec(wavelength_m, aperture_m, obstruction_ratio)

        obstruction_effect = rayleigh_base - rayleigh_with_obs

        # Dawes limit
        dawes_arcsec = 116.0 / telescope.primary_diameter

        # Airy disk diameter
        airy_disk_arcsec = 2.44 * wavelength_m / aperture_m * 206265

        # Spider vane metrics
        n_vanes = int(getattr(telescope, 'spider_vanes', 0))
        vane_width_mm = getattr(telescope, 'spider_vane_width', 0.0)
        radius_mm = telescope.primary_diameter / 2.0
        if n_vanes > 0 and radius_mm > 0:
            blocked_area = n_vanes * vane_width_mm * radius_mm
            total_area = np.pi * radius_mm ** 2
            spider_blocked_frac = blocked_area / total_area
            spider_strehl = (1 - spider_blocked_frac) ** 2
        else:
            spider_blocked_frac = 0.0
            spider_strehl = 1.0

        # Geometric aberrations
        primary_type = getattr(telescope, 'primary_type', 'parabolic')
        spherical_blur_arcsec = 0.0
        if primary_type == 'spherical':
            f_ratio = telescope.focal_ratio
            spherical_blur_arcsec = 1000.0 / (f_ratio ** 3)

        # Chromatic aberration (for refractors)
        chromatic_blur_arcsec = 0.0
        telescope_type = self.telescope_panel.type_combo.currentText().lower()
        objective_type = getattr(telescope, 'objective_type', None)
        if telescope_type == "refractor" and objective_type == "singlet":
            chromatic_blur_arcsec = 30.0 / telescope.focal_ratio

        obstruction_pct = 0.0
        if hasattr(telescope, 'obstruction_ratio'):
            obstruction_pct = telescope.obstruction_ratio * 100

        return {
            "rayleigh": rayleigh_with_obs,
            "rayleigh_base": rayleigh_base,
            "rayleigh_with_obs": rayleigh_with_obs,
            "obstruction_effect": obstruction_effect,
            "spider_blocked_frac": spider_blocked_frac,
            "spider_strehl": spider_strehl,
            "n_vanes": n_vanes,
            "dawes": dawes_arcsec,
            "airy_disk": airy_disk_arcsec,
            "wavelength": wavelength_nm,
            "aperture": telescope.primary_diameter,
            "fratio": telescope.focal_ratio,
            "spherical_blur": spherical_blur_arcsec,
            "chromatic_blur": chromatic_blur_arcsec,
            "obstruction_pct": obstruction_pct,
            "primary_type": primary_type
        }

    def update_metrics_label(self, metrics):
        """Update the metrics display with resolution breakdown."""
        breakdown_parts = [f"Diffraction (aperture): {metrics['rayleigh_base']:.2f}\""]

        if metrics['obstruction_pct'] > 0:
            effect = metrics['obstruction_effect']
            sign = "+" if effect >= 0 else ""
            breakdown_parts.append(
                f"Obstruction: {metrics['obstruction_pct']:.0f}% "
                f"(resolution {sign}{effect:.2f}\" narrower core)"
            )

        if metrics['n_vanes'] > 0:
            breakdown_parts.append(
                f"Spider vanes: {metrics['spider_blocked_frac']*100:.1f}% blocked "
                f"(Strehl \u2248{metrics['spider_strehl']:.2f})"
            )

        if metrics['spherical_blur'] > 0.1:
            breakdown_parts.append(f"Spherical: {metrics['spherical_blur']:.2f}\"")

        if metrics['chromatic_blur'] > 0.1:
            breakdown_parts.append(f"Chromatic: {metrics['chromatic_blur']:.2f}\"")

        breakdown = " \u2022 ".join(breakdown_parts)

        tip = ""
        if metrics['obstruction_pct'] > 0:
            tip = "\nTip: Obstruction effect on extended objects is subtle (modeled in PSF convolution). Use Point Source to see it directly."

        text = (
            f"Current: D={metrics['aperture']:.0f}mm, f/{metrics['fratio']:.1f}, "
            f"\u03bb={metrics['wavelength']:.0f}nm, {metrics['primary_type']} | "
            f"Resolution Breakdown: {breakdown}{tip}"
        )
        self.metrics_label.setText(text)

    def update_view(self):
        """Update PSF, spot diagram, and metrics."""
        try:
            telescope = self.telescope_panel.build()
            wavelength_nm = self.wavelength_spin.value()

            # Update effective f/ratio display
            self.telescope_panel.update_effective_fratio(telescope)

            # Calculate and display metrics
            metrics = self.calculate_metrics(telescope)
            self.update_metrics_label(metrics)

            # Determine analysis view mode
            analysis_view = self.analysis_combo.currentText()
            telescope_type = self.telescope_panel.type_combo.currentText()
            include_obstruction = self.telescope_panel.enable_obstruction_check.isChecked()

            if analysis_view == "Coma Field Analysis":
                fig_coma = plot_coma_field_analysis(
                    telescope,
                    wavelength_nm=wavelength_nm,
                    include_obstruction=include_obstruction,
                    figsize=(14, 7)
                )
                self.psf_canvas.set_figure(fig_coma)
                plt.close(fig_coma)

            elif analysis_view == "Vignetting Curve":
                fig_vig = plot_vignetting_curve(
                    telescope,
                    figsize=(9, 6)
                )
                self.psf_canvas.set_figure(fig_vig)
                plt.close(fig_vig)

            else:
                # Default: PSF + Spot Diagram
                psf_mode = "1d" if self.psf_1d_radio.isChecked() else "2d"
                psf_scale = "log" if self.psf_log_radio.isChecked() else "linear"

                if psf_mode == "1d":
                    title = f"{telescope.primary_diameter:.0f}mm f/{telescope.focal_ratio:.1f} {telescope_type} \u2014 PSF Profile"

                    fig_full = plot_psf_profile(
                        telescope,
                        title=title,
                        wavelength_nm=wavelength_nm,
                        include_obstruction=include_obstruction,
                        figsize=(14, 7)
                    )

                    subplot_idx = 1 if psf_scale == "log" else 0
                    source_ax = fig_full.axes[subplot_idx]

                    fig_psf = Figure(figsize=(8, 6))
                    ax = fig_psf.add_subplot(111)

                    for line in source_ax.get_lines():
                        ax.plot(line.get_xdata(), line.get_ydata(),
                               color=line.get_color(),
                               linestyle=line.get_linestyle(),
                               linewidth=line.get_linewidth(),
                               label=line.get_label())

                    ax.set_xlabel(source_ax.get_xlabel())
                    ax.set_ylabel(source_ax.get_ylabel())
                    ax.set_title(f"{title} ({'Logarithmic' if psf_scale == 'log' else 'Linear'} scale)")

                    if psf_scale == "log":
                        ax.set_yscale('log')
                        ax.set_ylim(source_ax.get_ylim())
                    else:
                        ax.set_ylim(source_ax.get_ylim())

                    ax.set_xlim(source_ax.get_xlim())
                    ax.legend(fontsize=9)
                    ax.grid(True, alpha=0.3)

                    # Add secondary x-axis in arcseconds
                    focal_length = telescope.focal_length
                    plate_scale = 206265.0 / focal_length
                    def _um_to_arcsec(x_um, ps=plate_scale):
                        return x_um * ps / 1000.0
                    def _arcsec_to_um(x_arcsec, ps=plate_scale):
                        return x_arcsec * 1000.0 / ps
                    ax_top = ax.secondary_xaxis('top', functions=(_um_to_arcsec, _arcsec_to_um))
                    ax_top.set_xlabel("Angular distance (arcsec)", fontsize=8)

                    fig_psf.tight_layout()
                    plt.close(fig_full)
                else:
                    autoscale = self.autoscale_psf_check.isChecked()
                    fig_psf = plot_psf_2d(
                        telescope,
                        wavelength_nm=wavelength_nm,
                        include_obstruction=include_obstruction,
                        autoscale=autoscale,
                        figsize=(6, 6)
                    )

                # Apply linear scale if requested (for 2D mode)
                if psf_mode == "2d" and psf_scale == "linear":
                    for ax in fig_psf.axes:
                        for im in ax.images:
                            data = im.get_array()
                            linear_data = 10 ** data
                            im.set_data(linear_data)
                            im.set_norm(plt.Normalize(vmin=linear_data.min(), vmax=linear_data.max()))
                            if hasattr(im, 'colorbar') and im.colorbar is not None:
                                im.colorbar.update_normal(im)

                self.psf_canvas.set_figure(fig_psf, preserve_limits=self.lock_axes_check.isChecked())
                plt.close(fig_psf)

                # Update spot diagram
                from telescope_sim.source.light_source import create_parallel_rays
                rays = create_parallel_rays(
                    num_rays=21,
                    aperture_diameter=telescope.primary_diameter,
                    entry_height=telescope.tube_length * 1.15,
                    wavelength_nm=wavelength_nm
                )
                telescope.trace_rays(rays)

                title = f"{telescope.primary_diameter:.0f}mm f/{telescope.focal_ratio:.1f} {telescope_type} \u2014 Spot Diagram"
                fig_spot = plot_spot_diagram(
                    rays,
                    title=title,
                    figsize=(9, 9)
                )
                self.spot_canvas.set_figure(fig_spot)
                plt.close(fig_spot)

        except Exception as e:
            print(f"Error updating performance view: {e}")
            import traceback
            traceback.print_exc()

"""
Main window for telescope simulator GUI.

Manages mode switching between Single Telescope and Comparison modes.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QRadioButton, QButtonGroup, QLabel, QStatusBar,
    QMenuBar, QMenu
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

from telescope_gui.single_mode.design_tab import DesignTab
from telescope_gui.single_mode.performance_tab import PerformanceTab
from telescope_gui.comparison_mode.ray_traces_tab import RayTracesTab
from telescope_gui.comparison_mode.images_tab import ImagesTab
from telescope_gui.comparison_mode.analytics_tab import AnalyticsTab


class MainWindow(QMainWindow):
    """Main application window with mode toggle and dynamic tabs."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Telescope Simulator")
        self.setGeometry(100, 100, 1400, 900)

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Mode selector
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))

        self.mode_group = QButtonGroup()
        self.single_mode_radio = QRadioButton("Single Telescope")
        self.comparison_mode_radio = QRadioButton("Comparison")

        self.mode_group.addButton(self.single_mode_radio)
        self.mode_group.addButton(self.comparison_mode_radio)

        self.single_mode_radio.setChecked(True)
        self.single_mode_radio.toggled.connect(self.switch_mode)

        mode_layout.addWidget(self.single_mode_radio)
        mode_layout.addWidget(self.comparison_mode_radio)
        mode_layout.addStretch()

        main_layout.addLayout(mode_layout)

        # Tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Menu bar
        self.create_menus()

        # Initialize with single mode tabs
        self.switch_mode()

    def create_menus(self):
        """Create menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        new_action = QAction("&New Configuration", self)
        new_action.setShortcut("Ctrl+N")
        file_menu.addAction(new_action)

        open_action = QAction("&Open Configuration...", self)
        open_action.setShortcut("Ctrl+O")
        file_menu.addAction(open_action)

        save_action = QAction("&Save Configuration", self)
        save_action.setShortcut("Ctrl+S")
        file_menu.addAction(save_action)

        save_as_action = QAction("Save Configuration &As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        user_guide_action = QAction("&User Guide", self)
        help_menu.addAction(user_guide_action)

        physics_ref_action = QAction("&Physics Reference", self)
        help_menu.addAction(physics_ref_action)

        help_menu.addSeparator()

        about_action = QAction("&About", self)
        help_menu.addAction(about_action)

    def switch_mode(self):
        """Switch between Single Telescope and Comparison modes."""
        # Clear existing tabs
        self.tab_widget.clear()

        if self.single_mode_radio.isChecked():
            # Single telescope mode
            self.status_bar.showMessage("Single Telescope Mode")

            design_tab = DesignTab()
            performance_tab = PerformanceTab()

            self.tab_widget.addTab(design_tab, "Design")
            self.tab_widget.addTab(performance_tab, "Performance")

        else:
            # Comparison mode
            self.status_bar.showMessage("Comparison Mode")

            ray_traces_tab = RayTracesTab()
            images_tab = ImagesTab()
            analytics_tab = AnalyticsTab()

            self.tab_widget.addTab(ray_traces_tab, "Ray Traces")
            self.tab_widget.addTab(images_tab, "Simulated Images")
            self.tab_widget.addTab(analytics_tab, "Analytics")

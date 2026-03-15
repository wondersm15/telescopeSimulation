#!/usr/bin/env python
"""
GUI entry point for telescope simulator.

Usage:
    python gui.py
"""

import sys
from PyQt6.QtWidgets import QApplication
from telescope_gui.main_window import MainWindow


def main():
    """Launch the GUI application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Telescope Simulator")
    app.setOrganizationName("TelescopeSimulationProject")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

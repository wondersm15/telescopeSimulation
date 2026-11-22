"""Tests for the browser's Qt stand-in (web/py/PyQt6 + web/py/qtshim).

The browser runs the unmodified desktop GUI on a small re-implementation
of the PyQt6 API. These tests pin the Qt behaviours the GUI relies on,
each checked against what real Qt does (web/tools/qt_parity.py compares
whole sessions; these are the fast, focused cases).

The stand-in replaces ``PyQt6`` in ``sys.modules``, which would break the
real-Qt tests sharing this process, so each case runs in a subprocess.
"""

import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SETUP = """
import sys
sys.path.insert(0, "web/py")
import qtshim
qtshim.install()
from qtshim import nodes
from PyQt6.QtCore import Qt, QTimer
from PyQt6 import QtWidgets as W
app = W.QApplication([])
"""


def run_in_shim(body: str) -> None:
    code = SETUP + textwrap.dedent(body)
    result = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_double_spin_box_rounds_and_clamps_like_qt():
    run_in_shim("""
    spin = W.QDoubleSpinBox()          # Qt default: 0..99.99, 2 decimals
    spin.setValue(1.23456)
    assert spin.value() == 1.23
    spin.setValue(500)
    assert spin.value() == 99.99
    spin.setRange(0, 1000); spin.setDecimals(1); spin.setValue(12.34)
    assert spin.value() == 12.3
    """)


def test_exclusive_radio_signal_order():
    # Qt checks the new button, then emits the old one's toggled(False)
    # before the new one's toggled(True).
    run_in_shim("""
    parent = W.QWidget(); layout = W.QHBoxLayout(parent)
    a, b = W.QRadioButton("a"), W.QRadioButton("b")
    layout.addWidget(a); layout.addWidget(b)
    a.setChecked(True)
    seen = []
    a.toggled.connect(lambda on: seen.append(("a", on, b.isChecked())))
    b.toggled.connect(lambda on: seen.append(("b", on, a.isChecked())))
    b.click()
    assert seen == [("a", False, True), ("b", True, False)], seen
    """)


def test_first_combo_item_becomes_current_and_emits():
    run_in_shim("""
    combo = W.QComboBox()
    seen = []
    combo.currentIndexChanged.connect(seen.append)
    combo.addItem("x"); combo.addItem("y")
    assert combo.currentIndex() == 0 and seen == [0]
    """)


def test_combo_item_flags_disable_an_entry():
    # tutorial_tab disables the "F=C plane" focus item for singlets.
    run_in_shim("""
    combo = W.QComboBox(); combo.addItems(["G", "F=C"])
    item = combo.model().item(1)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
    assert not combo.model().item(1).isEnabled()
    assert combo.model().item(0).isEnabled()
    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEnabled)
    assert combo.model().item(1).isEnabled()
    assert combo.model().item(2) is None
    """)


def test_block_signals_suppresses_emission():
    run_in_shim("""
    box = W.QCheckBox("c"); seen = []
    box.toggled.connect(seen.append)
    box.blockSignals(True); box.setChecked(True); box.blockSignals(False)
    assert box.isChecked() and seen == []
    """)


def test_visibility_follows_ancestors():
    run_in_shim("""
    outer = W.QWidget(); layout = W.QVBoxLayout(outer)
    inner = W.QLabel("x"); layout.addWidget(inner)
    outer.show()
    assert inner.isVisible()
    outer.hide()
    assert not inner.isVisible() and not inner.isHidden()
    """)


def test_timer_restart_and_stop_cancel_pending_timeout():
    run_in_shim("""
    hits = []
    timer = QTimer(); timer.setSingleShot(True)
    timer.timeout.connect(lambda: hits.append(1))
    timer.start(10); timer.start(10); nodes.run_pending()
    assert hits == [1]
    timer.start(10); timer.stop(); nodes.run_pending()
    assert hits == [1] and not timer.isActive()
    """)


def test_flag_algebra():
    # `flags & ~Flag` removes a flag; `|` adds one (as QFlags).
    run_in_shim("""
    enabled, selectable = Qt.ItemFlag.ItemIsEnabled, Qt.ItemFlag.ItemIsSelectable
    both = enabled | selectable
    assert not (enabled & ~enabled)
    assert (both & ~enabled) == selectable
    assert ((both & ~enabled) | enabled) == both
    """)

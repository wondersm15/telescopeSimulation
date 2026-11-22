"""Check the Qt stand-in (web/py) against real PyQt6, widget by widget.

Runs the unmodified desktop MainWindow twice, in separate processes:
once on real PyQt6 (offscreen) and once on the stand-in. Each run follows
the same scripted session (every mode and tab, every tutorial scenario,
and a sequence of control changes) and records after every step:

* the state of every widget on screen: label text, combo items and
  selection, spin values and ranges, check states, enabled, visibility;
* the data in every plot (fig_arrays.figure_arrays).

The two recordings must match exactly. A difference means the stand-in
does not reproduce a Qt behaviour the app relies on.

    venv/bin/python web/tools/qt_parity.py            # compare (≈ 3 min)
    venv/bin/python web/tools/qt_parity.py --quick    # first 3 scenarios

Deliberate differences, excluded from the comparison:
* NavigationToolbar2QT — the zoom/pan toolbar has no browser equivalent
  and is hidden there;
* "Pop Out" (a modal window, which would block here) and "Copy"
  (clipboard) are not clicked.
"""

from __future__ import annotations

import argparse
import os
import pickle
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKIPPED_BUTTONS = ("Pop Out", "Copy")
ACTIONS_PER_TAB = 12
ACTIONS_PER_SCENARIO = 5
# Live-sky views use the current time; both workers see this instant so the
# Moon and planets are in the same place in each.
FROZEN_NOW = "2026-06-21T04:00:00+00:00"


def freeze_clock() -> None:
    from datetime import datetime

    from telescope_sim.source import realtime

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.fromisoformat(FROZEN_NOW).astimezone(tz)

    realtime.datetime = FrozenDatetime


# ── Recording (runs in a worker process) ──────────────────────────────

def record(backend: str, quick: bool) -> list:
    if backend == "shim":
        sys.path.insert(0, str(ROOT / "web" / "py"))
        import qtshim
        qtshim.install()
        from qtshim import nodes
        pump = nodes.run_pending
    else:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    sys.path.insert(1, str(ROOT))
    sys.path.insert(2, str(ROOT / "web" / "tools"))

    freeze_clock()
    from PyQt6 import QtWidgets as W
    from fig_arrays import figure_arrays
    from telescope_gui.main_window import MainWindow

    app = W.QApplication.instance() or W.QApplication([])
    if backend == "real":
        def pump():
            for _ in range(3):
                app.processEvents()

    def kind(w) -> str:
        name = type(w).__name__
        if name in ("FigureCanvasQTAgg", "NavigationToolbar2QT"):
            return name
        for cls in type(w).__mro__:
            if cls.__module__.startswith("PyQt6"):
                return cls.__name__
        return name

    def children(w) -> list:
        if isinstance(w, W.QMainWindow):
            return [w.centralWidget(), w.statusBar()]
        if isinstance(w, W.QScrollArea):
            return [w.widget()] if w.widget() is not None else []
        if isinstance(w, W.QTabWidget):
            return [w.widget(i) for i in range(w.count())]
        if isinstance(w, (W.QAbstractScrollArea, W.QStatusBar)):
            return []  # leaves (internal children are Qt's own, e.g. QSizeGrip)
        return layout_widgets(w.layout()) if w.layout() is not None else []

    def layout_widgets(layout) -> list:
        out = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.widget() is not None:
                out.append(item.widget())
            elif item.layout() is not None:
                out.extend(layout_widgets(item.layout()))
        return out

    def walk(w):
        if kind(w) == "NavigationToolbar2QT":
            return
        yield w
        for child in children(w):
            yield from walk(child)

    def state(w):
        k = kind(w)
        common = (k, w.isVisible(), w.isEnabled())
        if isinstance(w, W.QLabel):
            return common + (w.text(),)
        if isinstance(w, W.QAbstractButton):
            return common + (w.text(), w.isChecked())
        if isinstance(w, W.QComboBox):
            model = w.model()
            return common + (w.currentIndex(), tuple(
                (w.itemText(i), model.item(i).isEnabled())
                for i in range(w.count())))
        if isinstance(w, W.QDoubleSpinBox):
            return common + (w.value(), w.minimum(), w.maximum(), w.decimals())
        if isinstance(w, (W.QSpinBox, W.QSlider)):
            return common + (w.value(), w.minimum(), w.maximum())
        if isinstance(w, W.QTextEdit):
            return common + (w.toPlainText(),)
        if isinstance(w, W.QTableWidget):
            return common + tuple(
                tuple((w.item(r, c).text() if w.item(r, c) else "")
                      for c in range(w.columnCount()))
                for r in range(w.rowCount()))
        if isinstance(w, W.QTabWidget):
            return common + (w.currentIndex(),
                             tuple(w.tabText(i) for i in range(w.count())))
        if isinstance(w, W.QGroupBox):
            return common + (w.title(),)
        if isinstance(w, W.QStatusBar):
            return common + (w.currentMessage(),)
        return common

    window = MainWindow()
    window.show()
    pump()
    steps = []

    def snapshot(name: str) -> None:
        widgets = list(walk(window))
        figures = {f"{i}:{name}": figure_arrays(w.figure)
                   for i, w in enumerate(widgets)
                   if kind(w) == "FigureCanvasQTAgg"}
        steps.append((name, [state(w) for w in widgets], figures))

    def interactive(scope, exclude=()) -> list:
        excluded = {id(w) for e in exclude for w in walk(e)}
        out = []
        for w in walk(scope):
            if id(w) in excluded or not (w.isVisible() and w.isEnabled()):
                continue
            if isinstance(w, W.QPushButton) and w.text() in SKIPPED_BUTTONS:
                continue
            if isinstance(w, (W.QComboBox, W.QAbstractButton, W.QSlider,
                              W.QSpinBox, W.QDoubleSpinBox)):
                out.append(w)
        return out

    def act(w) -> str:
        """Change one control the way a user would; describe the change."""
        if isinstance(w, W.QComboBox):
            if w.count() < 2:
                return ""
            w.setCurrentIndex((w.currentIndex() + 1) % w.count())
            return f"combo→{w.currentText()}"
        if isinstance(w, W.QRadioButton):
            if w.isChecked():
                return ""
            w.click()
            return f"radio {w.text()}"
        if isinstance(w, W.QAbstractButton):
            w.click()
            return f"click {w.text()}"
        if isinstance(w, (W.QSpinBox, W.QDoubleSpinBox)):
            step = w.singleStep()
            w.setValue(w.value() + (step if w.value() + step <= w.maximum()
                                    else -step))
            w.editingFinished.emit()
            return f"spin→{w.value()}"
        if isinstance(w, W.QSlider):
            span = max((w.maximum() - w.minimum()) // 4, 1)
            target = w.value() + span
            w.setValue(target if target <= w.maximum() else w.minimum())
            w.sliderReleased.emit()
            return f"slider→{w.value()}"
        return ""

    def exercise(label: str, scope, limit: int, exclude=()) -> None:
        for n in range(limit):
            controls = interactive(scope, exclude)
            if n >= len(controls):
                break
            what = act(controls[n])
            pump()
            if what:
                snapshot(f"{label} #{n} {what}")

    def each_tab(label: str) -> None:
        tabs = window.tab_widget
        for i in range(tabs.count()):
            tabs.setCurrentIndex(i)
            pump()
            snapshot(f"{label}/{tabs.tabText(i)}")
            exercise(f"{label}/{tabs.tabText(i)}", tabs.widget(i),
                     ACTIONS_PER_TAB)

    snapshot("start")
    each_tab("single")
    window.comparison_mode_radio.click(); pump()
    each_tab("comparison")
    window.reference_mode_radio.click(); pump()
    each_tab("reference")
    window.tutorial_mode_radio.click(); pump()
    tutorial = window.tab_widget.widget(0)
    snapshot("tutorial")
    buttons = [b for b in interactive(tutorial.sidebar)
               if isinstance(b, W.QPushButton)]
    for b in buttons[:3] if quick else buttons:
        b.click(); pump()
        snapshot(f"tutorial/{b.text()}")
        exercise(f"tutorial/{b.text()}", tutorial, ACTIONS_PER_SCENARIO,
                 exclude=(tutorial.sidebar,))
    # "Learn more →" opens the reference beside the tutorial.
    link = tutorial.learn_more_label
    if link.isVisible():
        import re
        from html import unescape
        href = unescape(re.search(r"href=['\"]([^'\"]+)", link.text()).group(1))
        link.linkActivated.emit(href); pump()
        snapshot(f"learn more {href}")
    window.single_mode_radio.click(); pump()
    snapshot("back to single")
    return steps


# ── Comparison (parent process) ───────────────────────────────────────

def run_worker(backend: str, quick: bool, out: Path) -> float:
    start = time.time()
    cmd = [sys.executable, __file__, "--worker", backend, "--out", str(out)]
    if quick:
        cmd.append("--quick")
    subprocess.run(cmd, check=True, cwd=ROOT)
    return time.time() - start


def compare(real: list, shim: list) -> list[str]:
    sys.path.insert(0, str(ROOT / "web" / "tools"))
    from fig_arrays import max_relative_difference
    problems = []
    if [s[0] for s in real] != [s[0] for s in shim]:
        problems.append("the scripted sessions diverged:")
        for a, b in zip(real, shim):
            if a[0] != b[0]:
                problems.append(f"  real: {a[0]!r}\n  shim: {b[0]!r}")
                break
        return problems
    for (name, real_states, real_figs), (_, shim_states, shim_figs) in zip(real, shim):
        if real_states != shim_states:
            if len(real_states) != len(shim_states):
                import difflib
                kinds = difflib.SequenceMatcher(
                    a=[s[0] for s in real_states], b=[s[0] for s in shim_states],
                    autojunk=False)
                for op, i1, i2, j1, j2 in kinds.get_opcodes():
                    if op != "equal":
                        problems.append(
                            f"[{name}] widgets differ at {i1}: real "
                            f"{real_states[i1:i2][:3]} vs shim {shim_states[j1:j2][:3]}")
                        break
                continue
            for i, (a, b) in enumerate(zip(real_states, shim_states)):
                if a != b:
                    problems.append(f"[{name}] widget {i}:\n  real {a}\n  shim {b}")
                    break
        if real_figs.keys() != shim_figs.keys():
            problems.append(f"[{name}] different plots shown")
            continue
        for key in real_figs:
            diff = max_relative_difference(real_figs[key], shim_figs[key])
            if diff > 0:
                problems.append(f"[{name}] plot {key} differs (rel {diff:.2g})")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--worker", choices=("real", "shim"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    if args.worker:
        with open(args.out, "wb") as f:
            pickle.dump(record(args.worker, args.quick), f)
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        paths = {b: Path(tmp) / f"{b}.pkl" for b in ("real", "shim")}
        times = {b: run_worker(b, args.quick, p) for b, p in paths.items()}
        real, shim = (pickle.loads(paths[b].read_bytes()) for b in ("real", "shim"))

    problems = compare(real, shim)
    n_widgets = sum(len(s[1]) for s in real)
    n_plots = sum(len(s[2]) for s in real)
    print(f"{len(real)} steps, {n_widgets} widget states, {n_plots} plots "
          f"(real {times['real']:.0f} s, shim {times['shim']:.0f} s)")
    for p in problems[:40]:
        print(p)
    print("PASS" if not problems else f"FAIL ({len(problems)} differences)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

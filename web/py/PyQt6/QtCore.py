"""Stand-in for PyQt6.QtCore: signals, enums, QTimer, QPoint.

Only what telescope_gui uses, with Qt's semantics where the app depends
on them (signal argument truncation, blockSignals, enum flag algebra).
"""

from __future__ import annotations

import inspect
from typing import Callable

from qtshim import nodes


# ── Enums ─────────────────────────────────────────────────────────────

class _Flag:
    """A named enum value with Qt's flag algebra: `A | B`, `f & ~A`, `A in f`.

    `~A` is "every flag except A"; and-ing with it removes A.
    """

    __slots__ = ("names", "inverted")

    def __init__(self, *names: str, inverted: bool = False):
        self.names = frozenset(names)
        self.inverted = inverted

    def __or__(self, other: "_Flag") -> "_Flag":
        return _Flag(*(self.names | other.names))

    __ror__ = __or__

    def __and__(self, other: "_Flag") -> "_Flag":
        if other.inverted:
            return _Flag(*(self.names - other.names))
        return _Flag(*(self.names & other.names))

    def __invert__(self) -> "_Flag":
        return _Flag(*self.names, inverted=not self.inverted)

    def __bool__(self) -> bool:
        return bool(self.names)

    def __contains__(self, name: str) -> bool:
        return name in self.names

    def __eq__(self, other) -> bool:
        return (isinstance(other, _Flag) and self.names == other.names
                and self.inverted == other.inverted)

    def __hash__(self) -> int:
        return hash((self.names, self.inverted))

    def __repr__(self) -> str:
        return "|".join(sorted(self.names))


class _EnumNamespace:
    """`Qt.AlignmentFlag.AlignCenter`-style access, values made on demand.

    Qt has hundreds of enums; the app uses a dozen. Rather than list them,
    any CamelCase attribute of a namespace is a nested namespace and any
    value is a `_Flag` named after itself — so values compare, hash and
    combine correctly without a table to keep in sync.
    """

    def __init__(self, name: str):
        self._name = name
        self._members: dict[str, object] = {}

    def __getattr__(self, attr: str):
        if attr.startswith("_"):
            raise AttributeError(attr)
        if attr not in self._members:
            self._members[attr] = _Flag(attr)
        return self._members[attr]


class _QtNamespace:
    """The `Qt` namespace: every attribute is an enum namespace."""

    def __init__(self):
        self._enums: dict[str, _EnumNamespace] = {}

    def __getattr__(self, attr: str) -> _EnumNamespace:
        if attr.startswith("_"):
            raise AttributeError(attr)
        return self._enums.setdefault(attr, _EnumNamespace(attr))


Qt = _QtNamespace()


# ── Signals ───────────────────────────────────────────────────────────

def _max_positional(slot: Callable) -> int | None:
    """How many positional args `slot` accepts (None = unlimited).

    PyQt passes a slot only as many of the signal's arguments as it can
    take; e.g. `clicked(bool)` → a zero-arg method is called with none,
    while `lambda checked, sid=x:` receives `checked`. Matching that is
    what lets the desktop's slot signatures work unchanged.
    """
    try:
        params = inspect.signature(slot).parameters.values()
    except (TypeError, ValueError):
        return None
    count = 0
    for p in params:
        if p.kind == p.VAR_POSITIONAL:
            return None
        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD):
            count += 1
    return count


class BoundSignal:
    def __init__(self, owner: "QObject", name: str):
        self._owner = owner
        self._name = name
        self._slots: list[tuple[Callable, int | None]] = []

    def connect(self, slot) -> None:
        if isinstance(slot, BoundSignal):
            self._slots.append((slot.emit, None))
        else:
            self._slots.append((slot, _max_positional(slot)))

    def disconnect(self, slot=None) -> None:
        if slot is None:
            self._slots.clear()
            return
        target = slot.emit if isinstance(slot, BoundSignal) else slot
        self._slots = [(s, n) for s, n in self._slots if s != target]

    def emit(self, *args) -> None:
        if self._owner.signalsBlocked():
            return
        for slot, n in list(self._slots):
            slot(*(args if n is None else args[:n]))


class pyqtSignal:
    """Class-level signal declaration; each instance gets its own BoundSignal."""

    def __init__(self, *types, name: str | None = None):
        self._types = types
        self._name = name

    def __set_name__(self, owner, name: str) -> None:
        self._name = self._name or name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        signals = obj.__dict__.setdefault("_bound_signals", {})
        if self._name not in signals:
            signals[self._name] = BoundSignal(obj, self._name)
        return signals[self._name]


def pyqtSlot(*_args, **_kwargs):
    return lambda fn: fn


class QObject:
    destroyed = pyqtSignal()

    def __init__(self, parent=None, *args, **kwargs):
        self._qparent = parent
        self._signals_blocked = False

    def blockSignals(self, block: bool) -> bool:
        previous = self._signals_blocked
        self._signals_blocked = bool(block)
        return previous

    def signalsBlocked(self) -> bool:
        return getattr(self, "_signals_blocked", False)

    def parent(self):
        return self._qparent

    def setParent(self, parent) -> None:
        self._qparent = parent

    def deleteLater(self) -> None:
        pass

    def setObjectName(self, name: str) -> None:
        self._object_name = name

    def objectName(self) -> str:
        return getattr(self, "_object_name", "")


# ── Small value types ─────────────────────────────────────────────────

class QPoint:
    def __init__(self, x: int = 0, y: int = 0):
        self._x, self._y = int(x), int(y)

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y


class QSize:
    def __init__(self, w: int = 0, h: int = 0):
        self._w, self._h = int(w), int(h)

    def width(self) -> int:
        return self._w

    def height(self) -> int:
        return self._h


class QRect:
    def __init__(self, x: int = 0, y: int = 0, w: int = 0, h: int = 0):
        self._x, self._y, self._w, self._h = int(x), int(y), int(w), int(h)

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y

    def width(self) -> int:
        return self._w

    def height(self) -> int:
        return self._h


class QTimer(QObject):
    timeout = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._interval = 0
        self._single = False
        # Each start() bumps the generation; a scheduled tick from an
        # earlier generation (stopped or restarted timer) does nothing.
        self._generation = 0
        self._active = False

    @staticmethod
    def singleShot(ms: int, fn: Callable) -> None:
        nodes.call_later(int(ms), fn)

    def setInterval(self, ms: int) -> None:
        self._interval = int(ms)

    def setSingleShot(self, single: bool) -> None:
        self._single = bool(single)

    def start(self, ms: int | None = None) -> None:
        """(Re)start: as in Qt, a pending timeout is cancelled first."""
        if ms is not None:
            self._interval = int(ms)
        self._generation += 1
        self._active = True
        self._schedule(self._generation)

    def stop(self) -> None:
        self._generation += 1
        self._active = False

    def isActive(self) -> bool:
        return self._active

    def _schedule(self, generation: int) -> None:
        def tick():
            if generation != self._generation:
                return
            if self._single:
                self._active = False
            else:
                self._schedule(generation)
            self.timeout.emit()
        nodes.call_later(self._interval, tick)

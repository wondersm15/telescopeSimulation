"""Stand-in for PyQt6.QtGui: QPixmap, QFont, QAction, QGuiApplication."""

from __future__ import annotations

import io

from PyQt6.QtCore import QObject, QRect, pyqtSignal
from qtshim.style import strip_mnemonic


class QPixmap:
    """PNG bytes plus size. QLabel.setPixmap shows the bytes as an <img>."""

    def __init__(self, *_args):
        self._png: bytes | None = None
        self._size = (0, 0)

    def loadFromData(self, data: bytes, _format: str | None = None) -> bool:
        from PIL import Image
        try:
            with Image.open(io.BytesIO(bytes(data))) as img:
                self._size = img.size
        except Exception:
            self._png, self._size = None, (0, 0)
            return False
        self._png = bytes(data)
        return True

    def isNull(self) -> bool:
        return self._png is None

    def width(self) -> int:
        return self._size[0]

    def height(self) -> int:
        return self._size[1]

    def png_bytes(self) -> bytes | None:
        return self._png


class QFont:
    def __init__(self, family: str = "", point_size: int = -1, *_args):
        self._family = family
        self._point_size = point_size

    def family(self) -> str:
        return self._family

    def pointSize(self) -> int:
        return self._point_size

    def setPointSize(self, size: int) -> None:
        self._point_size = size

    def setBold(self, bold: bool) -> None:
        self._bold = bold

    def css(self) -> dict:
        family = self._family
        if family.lower() in ("courier", "monospace", "courier new"):
            family = "ui-monospace, Menlo, Consolas, monospace"
        styles = {"font-family": family or None}
        if self._point_size > 0:
            styles["font-size"] = f"{self._point_size}pt"
        return styles


class QIcon:
    def __init__(self, *_args):
        pass


class QAction(QObject):
    triggered = pyqtSignal(bool)
    toggled = pyqtSignal(bool)

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._text = text
        self._checked = False
        self._enabled = True

    def text(self) -> str:
        return strip_mnemonic(self._text)

    def setText(self, text: str) -> None:
        self._text = text

    def setShortcut(self, _shortcut) -> None:
        pass

    def setStatusTip(self, _tip: str) -> None:
        pass

    def setCheckable(self, _checkable: bool) -> None:
        pass

    def setEnabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)

    def trigger(self) -> None:
        self.triggered.emit(self._checked)


class _Screen:
    def availableGeometry(self) -> QRect:
        return QRect(0, 0, 1920, 1080)

    def geometry(self) -> QRect:
        return self.availableGeometry()


class _Clipboard:
    def __init__(self):
        self._text = ""

    def setText(self, text: str) -> None:
        self._text = text
        from qtshim import nodes
        nodes.copy_to_clipboard(text)

    def text(self) -> str:
        return self._text


class QGuiApplication(QObject):
    _instance = None
    _clipboard = _Clipboard()

    def __init__(self, *args):
        super().__init__()
        type(self)._instance = self
        QGuiApplication._instance = self

    @staticmethod
    def primaryScreen() -> _Screen:
        return _Screen()

    @staticmethod
    def clipboard() -> _Clipboard:
        return QGuiApplication._clipboard

    @staticmethod
    def instance():
        return QGuiApplication._instance

    @staticmethod
    def processEvents(*_args) -> None:
        pass

    def setApplicationName(self, _name: str) -> None:
        pass

    def setOrganizationName(self, _name: str) -> None:
        pass

    def exec(self) -> int:
        return 0

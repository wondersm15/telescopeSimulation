"""Stand-in for PyQt6.QtWidgets, rendered as HTML.

Each class keeps the state the application reads back (current index,
checked, value, visibility, …) in Python with Qt's semantics, and mirrors
it onto display nodes (see qtshim/nodes.py). Only the API telescope_gui
uses is provided; anything else raises AttributeError loudly rather than
silently misbehaving.

Qt semantics reproduced because the app depends on them:
* programmatic setters emit change signals (setCurrentIndex, setChecked,
  setValue …) only when the value changes, and not while blockSignals;
* QDoubleSpinBox rounds to `decimals` and clamps to its range (default
  0–99.99, 2 dp), so call order matters exactly as in Qt;
* the first item added to an empty QComboBox becomes current and emits;
* radio buttons are exclusive within a QButtonGroup, else among siblings;
* isVisible() is false unless the widget, every ancestor and the window
  are shown.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, QPoint, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QGuiApplication, QPixmap
from qtshim import nodes
from qtshim.nodes import make_node
from qtshim.style import (might_be_rich_text, plain_to_html, qss_to_css,
                          strip_mnemonic)

_EXPANDING = {"Expanding", "MinimumExpanding", "Ignored"}


class QApplication(QGuiApplication):
    pass


class QSizePolicy:
    Policy = Qt.SizePolicy  # QSizePolicy.Policy.Expanding etc.

    def __init__(self, horizontal=None, vertical=None):
        self._h, self._v = horizontal, vertical

    def horizontalPolicy(self):
        return self._h

    def verticalPolicy(self):
        return self._v


# ── Widgets ───────────────────────────────────────────────────────────

class QWidget(QObject):
    """Base widget: one display node, an optional layout, visibility."""

    _default_grows = (False, False)  # (horizontal, vertical)

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent)
        self._node = make_node("div", "qw " + type(self).__name__)
        self._layout: QLayout | None = None
        self._parent_widget: QWidget | None = parent if isinstance(parent, QWidget) else None
        self._explicitly_hidden = False
        self._shown_window = False
        self._enabled = True
        self._tooltip = ""
        self._style_sheet = ""
        self._size_policy = (None, None)
        self._window_title = ""

    # ── tree ──
    def _set_parent_widget(self, parent: "QWidget | None") -> None:
        self._parent_widget = parent

    def parentWidget(self):
        return self._parent_widget

    def setParent(self, parent=None, *args) -> None:
        super().setParent(parent)
        self._detach()
        self._parent_widget = parent

    def _detach(self) -> None:
        """Remove from whatever layout/container currently shows this widget."""
        owner = getattr(self, "_owner_layout", None)
        if owner is not None:
            owner.removeWidget(self)
        container = getattr(self, "_owner_container", None)
        if container is not None:
            container._release_child(self)

    def deleteLater(self) -> None:
        self._detach()

    def window(self) -> "QWidget":
        w = self
        while w._parent_widget is not None:
            w = w._parent_widget
        return w

    def isWindow(self) -> bool:
        return self._parent_widget is None

    # ── layout ──
    def setLayout(self, layout: "QLayout") -> None:
        if self._layout is layout:
            return
        self._layout = layout
        layout._attach_to_widget(self)
        self._content_node().append(layout._node)

    def layout(self):
        return self._layout

    def _content_node(self):
        """Node that holds this widget's layout (overridden by containers)."""
        return self._node

    # ── visibility / state ──
    def setVisible(self, visible: bool) -> None:
        self._explicitly_hidden = not visible
        if visible and self._parent_widget is None:
            self._shown_window = True
        self._node.toggle_class("qhidden", not visible)

    def show(self) -> None:
        self.setVisible(True)

    def hide(self) -> None:
        self.setVisible(False)

    def close(self) -> bool:
        self.hide()
        return True

    def isHidden(self) -> bool:
        return self._explicitly_hidden

    def isVisible(self) -> bool:
        w = self
        while True:
            if w._explicitly_hidden:
                return False
            if w._parent_widget is None:
                return w._shown_window
            w = w._parent_widget

    def isVisibleTo(self, ancestor) -> bool:
        w = self
        while w is not None and w is not ancestor:
            if w._explicitly_hidden:
                return False
            w = w._parent_widget
        return True

    def setEnabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        self._apply_enabled()

    def setDisabled(self, disabled: bool) -> None:
        self.setEnabled(not disabled)

    def _apply_enabled(self) -> None:
        self._node.toggle_class("qdisabled", not self._enabled)

    def isEnabled(self) -> bool:
        w = self
        while w is not None:
            if not w._enabled:
                return False
            w = w._parent_widget
        return True

    def setToolTip(self, text: str) -> None:
        self._tooltip = text
        self._node.set_attr("title", text or None)

    def toolTip(self) -> str:
        return self._tooltip

    def setStyleSheet(self, sheet: str) -> None:
        self._style_sheet = sheet
        names = tuple(c.__name__ for c in type(self).__mro__)
        self._style_node().set_css_text(qss_to_css(sheet, names))

    def styleSheet(self) -> str:
        return self._style_sheet

    def _style_node(self):
        return self._node

    def setFont(self, font: QFont) -> None:
        self._font = font
        self._style_node().set_style(**font.css())

    def font(self) -> QFont:
        return getattr(self, "_font", QFont())

    # ── geometry (CSS hints; real sizes come from the browser) ──
    def setFixedWidth(self, w: int) -> None:
        self._node.set_style(width=f"{w}px", min_width=f"{w}px", max_width=f"{w}px")

    def setFixedHeight(self, h: int) -> None:
        self._node.set_style(height=f"{h}px", min_height=f"{h}px", max_height=f"{h}px")

    def setFixedSize(self, w, h=None) -> None:
        if isinstance(w, QSize):
            w, h = w.width(), w.height()
        self.setFixedWidth(w)
        self.setFixedHeight(h)

    def setMinimumWidth(self, w: int) -> None:
        self._node.set_style(min_width=f"{w}px")

    def setMinimumHeight(self, h: int) -> None:
        self._node.set_style(min_height=f"{h}px")

    def setMaximumWidth(self, w: int) -> None:
        self._node.set_style(max_width=f"{w}px")

    def setMaximumHeight(self, h: int) -> None:
        self._node.set_style(max_height=f"{h}px")

    def setMinimumSize(self, w, h=None) -> None:
        if isinstance(w, QSize):
            w, h = w.width(), w.height()
        self.setMinimumWidth(w)
        self.setMinimumHeight(h)

    def setMaximumSize(self, w, h=None) -> None:
        if isinstance(w, QSize):
            w, h = w.width(), w.height()
        self.setMaximumWidth(w)
        self.setMaximumHeight(h)

    def setSizePolicy(self, horizontal, vertical=None) -> None:
        if isinstance(horizontal, QSizePolicy):
            horizontal, vertical = horizontal._h, horizontal._v
        self._size_policy = (horizontal, vertical)
        if self._owner_layout_item() is not None:
            self._owner_layout._apply_item_style(self._owner_layout_item())

    def sizePolicy(self) -> QSizePolicy:
        return QSizePolicy(*self._size_policy)

    def _owner_layout_item(self):
        owner = getattr(self, "_owner_layout", None)
        return owner._item_for(self) if owner is not None else None

    def _grows(self) -> tuple[bool, bool]:
        """Whether this widget takes spare (horizontal, vertical) space."""
        h, v = self._size_policy
        grows_h, grows_v = self._default_grows
        if self._layout is not None:
            # Qt: a widget's layout makes it expand if any child expands.
            child_h, child_v = self._layout._grows()
            grows_h, grows_v = grows_h or child_h, grows_v or child_v
        if h is not None:
            grows_h = bool(h.names & _EXPANDING)
        if v is not None:
            grows_v = bool(v.names & _EXPANDING)
        return grows_h, grows_v

    def width(self) -> int:
        return self._node.client_width()

    def height(self) -> int:
        return 0

    def resize(self, *_args) -> None:
        pass

    def adjustSize(self) -> None:
        pass

    def move(self, *_args) -> None:
        pass

    def setGeometry(self, *_args) -> None:
        pass

    def mapTo(self, ancestor: "QWidget", point: QPoint) -> QPoint:
        return QPoint(point.x(), point.y() + self._node.offset_top_in(ancestor._node))

    def setWindowTitle(self, title: str) -> None:
        self._window_title = title

    def windowTitle(self) -> str:
        return self._window_title

    # Cosmetic or event-loop calls with no browser meaning.
    def setCursor(self, *_args) -> None: ...
    def setAttribute(self, *_args) -> None: ...
    def setAutoFillBackground(self, *_args) -> None: ...
    def setContentsMargins(self, *_args) -> None: ...
    def setFocus(self, *_args) -> None: ...
    def setFocusPolicy(self, *_args) -> None: ...
    def update(self, *_args) -> None: ...
    def repaint(self, *_args) -> None: ...
    def raise_(self) -> None: ...
    def activateWindow(self) -> None: ...
    def updateGeometry(self) -> None: ...


class QFrame(QWidget):
    class Shape:
        NoFrame = Qt.FrameShape.NoFrame
        Box = Qt.FrameShape.Box
        Panel = Qt.FrameShape.Panel
        StyledPanel = Qt.FrameShape.StyledPanel
        HLine = Qt.FrameShape.HLine
        VLine = Qt.FrameShape.VLine

    Shadow = Qt.FrameShadow

    def setFrameShape(self, shape) -> None:
        for name in ("HLine", "VLine", "Box", "StyledPanel", "Panel"):
            self._node.toggle_class(f"qframe-{name}", name in shape.names)

    def setFrameShadow(self, *_args) -> None: ...
    def setLineWidth(self, *_args) -> None: ...


class QLabel(QFrame):
    linkActivated = pyqtSignal(str)
    linkHovered = pyqtSignal(str)

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._text = ""
        self._text_format = Qt.TextFormat.AutoText
        self._open_external = False
        self._pixmap: QPixmap | None = None
        self._node.on_link(self._on_link)
        self.setText(text)

    def setText(self, text) -> None:
        self._text = "" if text is None else str(text)
        self._pixmap = None
        self._render()

    def text(self) -> str:
        return self._text

    def setNum(self, value) -> None:
        self.setText(str(value))

    def clear(self) -> None:
        self.setText("")

    def setTextFormat(self, fmt) -> None:
        self._text_format = fmt
        self._render()

    def _is_rich(self) -> bool:
        if "RichText" in self._text_format:
            return True
        if "PlainText" in self._text_format:
            return False
        return might_be_rich_text(self._text)

    def _render(self) -> None:
        if self._pixmap is not None:
            self._node.set_image_png(self._pixmap.png_bytes())
            return
        rich = self._is_rich()
        self._node.toggle_class("qrich", rich)
        if rich:
            self._node.set_html(self._text)
        else:
            self._node.set_text(self._text)

    def setPixmap(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap
        self._render()

    def pixmap(self):
        return self._pixmap

    def setWordWrap(self, on: bool) -> None:
        self._node.toggle_class("qwrap", bool(on))

    def setAlignment(self, alignment) -> None:
        for name, css in (("AlignCenter", "center"), ("AlignHCenter", "center"),
                          ("AlignRight", "right"), ("AlignLeft", "left")):
            if name in alignment:
                self._node.set_style(text_align=css)
                break

    def setOpenExternalLinks(self, on: bool) -> None:
        self._open_external = bool(on)

    def _on_link(self, href: str) -> None:
        if self._open_external:
            nodes.open_url(href)
        else:
            self.linkActivated.emit(href)

    def setTextInteractionFlags(self, *_args) -> None: ...
    def setMargin(self, *_args) -> None: ...
    def setIndent(self, *_args) -> None: ...
    def setScaledContents(self, *_args) -> None: ...
    def setBuddy(self, *_args) -> None: ...


class QAbstractButton(QWidget):
    clicked = pyqtSignal(bool)
    toggled = pyqtSignal(bool)
    pressed = pyqtSignal()
    released = pyqtSignal()

    _tag = "button"

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._text = ""
        self._checkable = False
        self._checked = False
        self._group: QButtonGroup | None = None
        self._build_nodes()
        self.setText(text)

    def _build_nodes(self) -> None:
        self._control = self._node
        self._label_node = self._node
        self._node.on("click", self._user_click)

    def setText(self, text: str) -> None:
        self._text = text or ""
        self._label_node.set_text(strip_mnemonic(self._text))

    def text(self) -> str:
        return self._text

    def setCheckable(self, on: bool) -> None:
        self._checkable = bool(on)

    def isCheckable(self) -> bool:
        return self._checkable

    def isChecked(self) -> bool:
        return self._checked

    def _exclusive_peers(self) -> list["QAbstractButton"] | None:
        return None

    def setChecked(self, checked: bool) -> None:
        checked = bool(checked)
        if not self._checkable or checked == self._checked:
            return
        peers = self._exclusive_peers()
        if not checked and peers is not None:
            return  # Qt: the checked button of an exclusive set can't uncheck itself
        self._checked = checked
        self._sync_checked()
        self._check_state_set()
        if checked and peers is not None:
            for peer in peers:
                if peer is not self and peer._checked:
                    peer._force_uncheck()
        self.toggled.emit(checked)

    def _force_uncheck(self) -> None:
        self._checked = False
        self._sync_checked()
        self._check_state_set()
        self.toggled.emit(False)

    def _check_state_set(self) -> None:
        """Hook for QCheckBox.stateChanged (emitted before toggled, as Qt)."""

    def _sync_checked(self) -> None:
        self._control.set_prop("checked", self._checked)
        self._node.toggle_class("qchecked", self._checked)

    def toggle(self) -> None:
        self.setChecked(not self._checked)

    def click(self) -> None:
        self._user_click()

    def _user_click(self) -> None:
        if not self.isEnabled():
            self._sync_checked()
            return
        if self._checkable:
            if self._exclusive_peers() is not None and self._checked:
                self._sync_checked()  # clicking the checked radio: no change
            else:
                self.setChecked(not self._checked)
        self.clicked.emit(self._checked)
        if self._group is not None:
            self._group._button_clicked(self)

    def _apply_enabled(self) -> None:
        super()._apply_enabled()
        self._control.set_prop("disabled", not self._enabled)

    def setIcon(self, *_args) -> None: ...
    def setIconSize(self, *_args) -> None: ...
    def setShortcut(self, *_args) -> None: ...
    def setAutoExclusive(self, *_args) -> None: ...


class QPushButton(QAbstractButton):
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)

    def _build_nodes(self) -> None:
        self._node = make_node("button", "qw QPushButton")
        super()._build_nodes()

    def setFlat(self, flat: bool) -> None:
        self._node.toggle_class("qflat", bool(flat))

    def setDefault(self, *_args) -> None: ...
    def setAutoDefault(self, *_args) -> None: ...


class _CheckLike(QAbstractButton):
    """<label><input type=checkbox|radio><span>text</span></label>."""

    _input_type = "checkbox"

    def _build_nodes(self) -> None:
        self._node = make_node("label", "qw " + type(self).__name__)
        self._control = make_node("input")
        self._control.set_attr("type", self._input_type)
        self._label_node = make_node("span")
        self._node.append(self._control)
        self._node.append(self._label_node)
        self._checkable = True
        self._control.on("change", self._user_click)

    def _style_node(self):
        return self._node


class QCheckBox(_CheckLike):
    stateChanged = pyqtSignal(int)
    checkStateChanged = pyqtSignal(object)

    def _check_state_set(self) -> None:
        self.stateChanged.emit(2 if self._checked else 0)
        self.checkStateChanged.emit(
            Qt.CheckState.Checked if self._checked else Qt.CheckState.Unchecked)

    def checkState(self):
        return Qt.CheckState.Checked if self._checked else Qt.CheckState.Unchecked

    def setCheckState(self, state) -> None:
        self.setChecked("Checked" in state)

    def setTristate(self, *_args) -> None: ...


class QRadioButton(_CheckLike):
    _input_type = "radio"

    def _exclusive_peers(self):
        if self._group is not None:
            return self._group._buttons if self._group._exclusive else None
        parent = self._parent_widget
        if parent is None:
            return [self]
        return [w for w in _descendant_widgets(parent)
                if isinstance(w, QRadioButton) and w._group is None
                and w._parent_widget is parent]


def _descendant_widgets(widget: QWidget) -> list[QWidget]:
    out = []
    if widget._layout is not None:
        out.extend(widget._layout._all_widgets())
    return out


class QButtonGroup(QObject):
    buttonClicked = pyqtSignal(object)
    idClicked = pyqtSignal(int)
    buttonToggled = pyqtSignal(object, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buttons: list[QAbstractButton] = []
        self._ids: dict[int, QAbstractButton] = {}
        self._exclusive = True

    def addButton(self, button: QAbstractButton, button_id: int = -1) -> None:
        button._group = self
        self._buttons.append(button)
        if button_id == -1:
            button_id = -2 - len(self._ids)
        self._ids[button_id] = button
        button.toggled.connect(lambda on, b=button: self.buttonToggled.emit(b, on))

    def buttons(self) -> list:
        return list(self._buttons)

    def checkedButton(self):
        return next((b for b in self._buttons if b._checked), None)

    def checkedId(self) -> int:
        b = self.checkedButton()
        return next((i for i, x in self._ids.items() if x is b), -1)

    def id(self, button) -> int:
        return next((i for i, x in self._ids.items() if x is button), -1)

    def button(self, button_id: int):
        return self._ids.get(button_id)

    def setExclusive(self, on: bool) -> None:
        self._exclusive = bool(on)

    def _button_clicked(self, button) -> None:
        self.buttonClicked.emit(button)
        self.idClicked.emit(self.id(button))


class QComboBox(QWidget):
    currentIndexChanged = pyqtSignal(int)
    currentTextChanged = pyqtSignal(str)
    activated = pyqtSignal(int)
    textActivated = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._node = make_node("select", "qw QComboBox")
        self._node.on("change", self._user_select)
        self._items: list[dict] = []  # {"text", roles: {role: value}}
        self._index = -1

    # ── items ──
    def addItem(self, *args) -> None:
        # addItem(text, userData=None) or addItem(icon, text, userData=None)
        if args and not isinstance(args[0], str):
            args = args[1:]
        text = args[0]
        data = args[1] if len(args) > 1 else None
        self.insertItem(len(self._items), text, data)

    def addItems(self, texts) -> None:
        for text in texts:
            self.addItem(text)

    def insertItem(self, index: int, text: str, data=None) -> None:
        index = max(0, min(index, len(self._items)))
        self._items.insert(index, {"text": text,
                                   "roles": {Qt.ItemDataRole.UserRole: data},
                                   "flags": _DEFAULT_ITEM_FLAGS})
        self._render_items()
        if self._index == -1:
            self._set_index(0)
        elif index <= self._index:
            self._index += 1  # Qt keeps the same item current
            self._node.set_prop("selectedIndex", self._index)

    def insertItems(self, index: int, texts) -> None:
        for offset, text in enumerate(texts):
            self.insertItem(index + offset, text)

    def removeItem(self, index: int) -> None:
        if not 0 <= index < len(self._items):
            return
        del self._items[index]
        self._render_items()
        if not self._items:
            self._set_index(-1)
        elif index < self._index:
            self._index -= 1
            self._node.set_prop("selectedIndex", self._index)
        elif index == self._index:
            self._index = -2  # force a change notification
            self._set_index(min(index, len(self._items) - 1))

    def clear(self) -> None:
        self._items.clear()
        self._render_items()
        self._set_index(-1)

    def count(self) -> int:
        return len(self._items)

    def itemText(self, index: int) -> str:
        return self._items[index]["text"] if 0 <= index < len(self._items) else ""

    def setItemText(self, index: int, text: str) -> None:
        self._items[index]["text"] = text
        self._render_items()

    def itemData(self, index: int, role=None):
        if not 0 <= index < len(self._items):
            return None
        return self._items[index]["roles"].get(role or Qt.ItemDataRole.UserRole)

    def setItemData(self, index: int, value, role=None) -> None:
        if 0 <= index < len(self._items):
            self._items[index]["roles"][role or Qt.ItemDataRole.UserRole] = value
            self._render_items()

    def model(self) -> "_ComboModel":
        return _ComboModel(self)

    def findData(self, data, role=None, *_flags) -> int:
        role = role or Qt.ItemDataRole.UserRole
        for i, item in enumerate(self._items):
            if item["roles"].get(role) == data:
                return i
        return -1

    def findText(self, text: str, *_flags) -> int:
        return next((i for i, item in enumerate(self._items)
                     if item["text"] == text), -1)

    # ── current ──
    def currentIndex(self) -> int:
        return self._index

    def currentText(self) -> str:
        return self.itemText(self._index)

    def currentData(self, role=None):
        return self.itemData(self._index, role)

    def setCurrentIndex(self, index: int) -> None:
        if not -1 <= index < len(self._items):
            return
        self._set_index(index)

    def setCurrentText(self, text: str) -> None:
        i = self.findText(text)
        if i >= 0:
            self._set_index(i)

    def _set_index(self, index: int) -> None:
        if index == self._index:
            return
        self._index = index
        self._node.set_prop("selectedIndex", index)
        self.currentIndexChanged.emit(index)
        self.currentTextChanged.emit(self.currentText())

    def _user_select(self) -> None:
        index = int(self._node.get_prop("selectedIndex"))
        self._set_index(index)
        self.activated.emit(index)
        self.textActivated.emit(self.currentText())

    def _render_items(self) -> None:
        self._node.clear()
        for item in self._items:
            option = make_node("option")
            option.set_text(item["text"])
            tip = item["roles"].get(Qt.ItemDataRole.ToolTipRole)
            if tip:
                option.set_attr("title", str(tip))
            if "ItemIsEnabled" not in item["flags"]:
                option.set_prop("disabled", True)
            self._node.append(option)
        self._node.set_prop("selectedIndex", self._index)

    def _apply_enabled(self) -> None:
        super()._apply_enabled()
        self._node.set_prop("disabled", not self._enabled)

    def setEditable(self, *_args) -> None: ...
    def setMinimumContentsLength(self, *_args) -> None: ...
    def setSizeAdjustPolicy(self, *_args) -> None: ...
    def setMaxVisibleItems(self, *_args) -> None: ...


_DEFAULT_ITEM_FLAGS = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled


class _ComboItem:
    """One combo entry as QStandardItem: text and enabled flags."""

    def __init__(self, combo: QComboBox, index: int):
        self._combo, self._entry = combo, combo._items[index]

    def text(self) -> str:
        return self._entry["text"]

    def flags(self):
        return self._entry["flags"]

    def setFlags(self, flags) -> None:
        self._entry["flags"] = flags
        self._combo._render_items()

    def isEnabled(self) -> bool:
        return "ItemIsEnabled" in self._entry["flags"]

    def setEnabled(self, enabled: bool) -> None:
        flag = Qt.ItemFlag.ItemIsEnabled
        self.setFlags(self.flags() | flag if enabled else self.flags() & ~flag)


class _ComboModel:
    """QComboBox.model() as a QStandardItemModel (item access only)."""

    def __init__(self, combo: QComboBox):
        self._combo = combo

    def item(self, row: int, _column: int = 0):
        if 0 <= row < len(self._combo._items):
            return _ComboItem(self._combo, row)
        return None

    def rowCount(self, *_args) -> int:
        return len(self._combo._items)


class QAbstractSpinBox(QWidget):
    editingFinished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._node = make_node("span", "qw " + type(self).__name__)
        self._prefix_node = make_node("span", "qaffix")
        self._input = make_node("input")
        self._input.set_attr("type", "number")
        self._suffix_node = make_node("span", "qaffix")
        for node in (self._prefix_node, self._input, self._suffix_node):
            self._node.append(node)
        self._input.on("change", self._user_edit)
        self._prefix = self._suffix = ""

    def setPrefix(self, prefix: str) -> None:
        self._prefix = prefix
        self._prefix_node.set_text(prefix)

    def setSuffix(self, suffix: str) -> None:
        self._suffix = suffix
        self._suffix_node.set_text(suffix)

    def prefix(self) -> str:
        return self._prefix

    def suffix(self) -> str:
        return self._suffix

    def _apply_enabled(self) -> None:
        super()._apply_enabled()
        self._input.set_prop("disabled", not self._enabled)

    def setKeyboardTracking(self, *_args) -> None: ...
    def setButtonSymbols(self, *_args) -> None: ...
    def setAlignment(self, *_args) -> None: ...
    def setAccelerated(self, *_args) -> None: ...
    def setWrapping(self, *_args) -> None: ...
    def setSpecialValueText(self, *_args) -> None: ...
    def setReadOnly(self, on: bool) -> None:
        self._input.set_prop("readOnly", bool(on))


class QDoubleSpinBox(QAbstractSpinBox):
    valueChanged = pyqtSignal(float)
    textChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._decimals = 2
        self._min, self._max = 0.0, 99.99
        self._step = 1.0
        self._value = 0.0
        self._sync_input()

    def _round(self, value: float) -> float:
        # Qt rounds through QString::number(value, 'f', decimals).
        return float(f"{float(value):.{self._decimals}f}")

    def _set(self, value: float, emit: bool = True) -> None:
        value = min(max(self._round(value), self._min), self._max)
        changed = value != self._value
        self._value = value
        self._sync_input()
        if changed and emit:
            self.valueChanged.emit(value)
            self.textChanged.emit(self.text())

    def setValue(self, value: float) -> None:
        self._set(value)

    def value(self) -> float:
        return self._value

    def text(self) -> str:
        return f"{self._prefix}{self._value:.{self._decimals}f}{self._suffix}"

    def cleanText(self) -> str:
        return f"{self._value:.{self._decimals}f}"

    def setRange(self, minimum: float, maximum: float) -> None:
        self._min = self._round(minimum)
        self._max = max(self._min, self._round(maximum))
        self._set(self._value)

    def setMinimum(self, minimum: float) -> None:
        self.setRange(minimum, max(minimum, self._max))

    def setMaximum(self, maximum: float) -> None:
        self.setRange(min(self._min, maximum), maximum)

    def minimum(self) -> float:
        return self._min

    def maximum(self) -> float:
        return self._max

    def setDecimals(self, decimals: int) -> None:
        self._decimals = max(0, int(decimals))
        self.setRange(self._min, self._max)
        self._set(self._value)

    def decimals(self) -> int:
        return self._decimals

    def setSingleStep(self, step: float) -> None:
        self._step = float(step)
        self._sync_input()

    def singleStep(self) -> float:
        return self._step

    def _sync_input(self) -> None:
        self._input.set_attr("min", repr(self._min))
        self._input.set_attr("max", repr(self._max))
        self._input.set_attr("step", "any")
        self._input.set_prop("value", f"{self._value:.{self._decimals}f}")

    def _user_edit(self) -> None:
        raw = self._input.get_prop("value")
        try:
            self._set(float(raw))
        except (TypeError, ValueError):
            self._sync_input()
            return
        self.editingFinished.emit()

    def stepBy(self, steps: int) -> None:
        self._set(self._value + steps * self._step)


class QSpinBox(QAbstractSpinBox):
    valueChanged = pyqtSignal(int)
    textChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._min, self._max, self._step, self._value = 0, 99, 1, 0
        self._sync_input()

    def _set(self, value, emit: bool = True) -> None:
        value = min(max(int(round(value)), self._min), self._max)
        changed = value != self._value
        self._value = value
        self._sync_input()
        if changed and emit:
            self.valueChanged.emit(value)
            self.textChanged.emit(self.text())

    def setValue(self, value: int) -> None:
        self._set(value)

    def value(self) -> int:
        return self._value

    def text(self) -> str:
        return f"{self._prefix}{self._value}{self._suffix}"

    def setRange(self, minimum: int, maximum: int) -> None:
        self._min, self._max = int(minimum), max(int(minimum), int(maximum))
        self._set(self._value)

    def setMinimum(self, minimum: int) -> None:
        self.setRange(minimum, max(minimum, self._max))

    def setMaximum(self, maximum: int) -> None:
        self.setRange(min(self._min, maximum), maximum)

    def minimum(self) -> int:
        return self._min

    def maximum(self) -> int:
        return self._max

    def setSingleStep(self, step: int) -> None:
        self._step = int(step)
        self._sync_input()

    def singleStep(self) -> int:
        return self._step

    def _sync_input(self) -> None:
        self._input.set_attr("min", str(self._min))
        self._input.set_attr("max", str(self._max))
        self._input.set_attr("step", str(self._step))
        self._input.set_prop("value", str(self._value))

    def _user_edit(self) -> None:
        try:
            self._set(float(self._input.get_prop("value")))
        except (TypeError, ValueError):
            self._sync_input()
            return
        self.editingFinished.emit()


class QSlider(QWidget):
    valueChanged = pyqtSignal(int)
    sliderMoved = pyqtSignal(int)
    sliderPressed = pyqtSignal()
    sliderReleased = pyqtSignal()

    TickPosition = Qt.TickPosition

    def __init__(self, orientation=None, parent=None):
        super().__init__(parent if not isinstance(orientation, QWidget) else orientation)
        self._node = make_node("input", "qw QSlider")
        self._node.set_attr("type", "range")
        self._min, self._max, self._value = 0, 99, 0
        self._node.on("input", self._user_move)
        self._node.on("change", self._user_release)
        self._sync()

    def _sync(self) -> None:
        self._node.set_attr("min", str(self._min))
        self._node.set_attr("max", str(self._max))
        self._node.set_prop("value", str(self._value))

    def setValue(self, value: int) -> None:
        value = min(max(int(value), self._min), self._max)
        if value == self._value:
            self._sync()
            return
        self._value = value
        self._sync()
        self.valueChanged.emit(value)

    def value(self) -> int:
        return self._value

    def setRange(self, minimum: int, maximum: int) -> None:
        self._min, self._max = int(minimum), max(int(minimum), int(maximum))
        self.setValue(self._value)

    def setMinimum(self, minimum: int) -> None:
        self.setRange(minimum, max(minimum, self._max))

    def setMaximum(self, maximum: int) -> None:
        self.setRange(min(self._min, maximum), maximum)

    def minimum(self) -> int:
        return self._min

    def maximum(self) -> int:
        return self._max

    def _user_move(self) -> None:
        value = int(float(self._node.get_prop("value")))
        self.setValue(value)
        self.sliderMoved.emit(value)

    def _user_release(self) -> None:
        self._user_move()
        self.sliderReleased.emit()

    def _apply_enabled(self) -> None:
        super()._apply_enabled()
        self._node.set_prop("disabled", not self._enabled)

    def setSingleStep(self, *_args) -> None: ...
    def setPageStep(self, *_args) -> None: ...
    def setTickPosition(self, *_args) -> None: ...
    def setTickInterval(self, *_args) -> None: ...
    def setTracking(self, *_args) -> None: ...


class QGroupBox(QWidget):
    toggled = pyqtSignal(bool)
    clicked = pyqtSignal(bool)

    def __init__(self, title: str = "", parent=None):
        if isinstance(title, QWidget):
            title, parent = "", title
        super().__init__(parent)
        self._node = make_node("fieldset", "qw QGroupBox")
        self._legend = make_node("legend")
        self._node.append(self._legend)
        self.setTitle(title)

    def setTitle(self, title: str) -> None:
        self._title = title or ""
        self._legend.set_text(strip_mnemonic(self._title))
        self._legend.toggle_class("qhidden", not self._title)

    def title(self) -> str:
        return self._title

    def setFlat(self, flat: bool) -> None:
        self._node.toggle_class("qflat", bool(flat))

    def setCheckable(self, *_args) -> None: ...
    def setAlignment(self, *_args) -> None: ...


class QScrollBar(QObject):
    valueChanged = pyqtSignal(int)

    def __init__(self, area: "QScrollArea"):
        super().__init__(area)
        self._area = area

    def value(self) -> int:
        return self._area._node.scroll_top()

    def setValue(self, value: int) -> None:
        self._area._node.scroll_top(int(value))

    def maximum(self) -> int:
        return self._area._node.scroll_height()

    def minimum(self) -> int:
        return 0


class QAbstractScrollArea(QFrame):
    _default_grows = (True, True)

    def setHorizontalScrollBarPolicy(self, policy) -> None:
        self._node.set_style(overflow_x=_overflow(policy))

    def setVerticalScrollBarPolicy(self, policy) -> None:
        self._node.set_style(overflow_y=_overflow(policy))

    def verticalScrollBar(self) -> QScrollBar:
        return QScrollBar(self)

    def horizontalScrollBar(self) -> QScrollBar:
        return QScrollBar(self)


def _overflow(policy) -> str:
    if "ScrollBarAlwaysOff" in policy:
        return "hidden"
    if "ScrollBarAlwaysOn" in policy:
        return "scroll"
    return "auto"


class QScrollArea(QAbstractScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._widget: QWidget | None = None

    def setWidget(self, widget: QWidget) -> None:
        if self._widget is not None:
            self._node.remove_child(self._widget._node)
            self._widget._owner_container = None
        widget._detach()
        self._widget = widget
        widget._set_parent_widget(self)
        widget._owner_container = self
        self._node.append(widget._node)

    def _release_child(self, widget: QWidget) -> None:
        if widget is self._widget:
            self._node.remove_child(widget._node)
            self._widget = None
            widget._owner_container = None

    def widget(self):
        return self._widget

    def takeWidget(self):
        w = self._widget
        if w is not None:
            self._release_child(w)
        return w

    def setWidgetResizable(self, *_args) -> None: ...
    def setAlignment(self, *_args) -> None: ...

    def ensureWidgetVisible(self, widget: QWidget, *_args) -> None:
        self.verticalScrollBar().setValue(
            widget._node.offset_top_in(self._node))


class QTextEdit(QAbstractScrollArea):
    textChanged = pyqtSignal()

    LineWrapMode = Qt.LineWrapMode

    def __init__(self, text: str = "", parent=None):
        if isinstance(text, QWidget):
            text, parent = "", text
        super().__init__(parent)
        self._node = make_node("pre", "qw QTextEdit")
        self._plain = ""
        self._html: str | None = None
        self._read_only = False
        if text:
            self.setText(text)

    def setPlainText(self, text: str) -> None:
        self._plain, self._html = text or "", None
        self._node.set_text(self._plain)
        self.textChanged.emit()

    def setHtml(self, html: str) -> None:
        import re
        from html import unescape
        self._html = html or ""
        self._plain = unescape(re.sub(r"<[^>]+>", "", self._html))
        self._node.set_html(self._html)
        self.textChanged.emit()

    def setText(self, text: str) -> None:
        if might_be_rich_text(text):
            self.setHtml(text)
        else:
            self.setPlainText(text)

    def append(self, text: str) -> None:
        self.setPlainText(f"{self._plain}\n{text}" if self._plain else text)

    def clear(self) -> None:
        self.setPlainText("")

    def toPlainText(self) -> str:
        return self._plain

    def toHtml(self) -> str:
        return self._html if self._html is not None else plain_to_html(self._plain)

    def setReadOnly(self, on: bool) -> None:
        self._read_only = bool(on)

    def isReadOnly(self) -> bool:
        return self._read_only

    def setLineWrapMode(self, mode) -> None:
        self._node.toggle_class("qnowrap", "NoWrap" in mode)

    def setPlaceholderText(self, *_args) -> None: ...
    def setTabStopDistance(self, *_args) -> None: ...
    def setAcceptRichText(self, *_args) -> None: ...
    def setOpenExternalLinks(self, *_args) -> None: ...


QTextBrowser = QTextEdit


class QTableWidgetItem:
    def __init__(self, text: str = ""):
        self._text = str(text)
        self._flags = None
        self._tooltip = ""
        self._align = None
        self._table: QTableWidget | None = None

    def text(self) -> str:
        return self._text

    def setText(self, text: str) -> None:
        self._text = str(text)
        if self._table is not None:
            self._table._render()

    def setFlags(self, flags) -> None:
        self._flags = flags

    def flags(self):
        return self._flags

    def setToolTip(self, tip: str) -> None:
        self._tooltip = tip

    def setTextAlignment(self, align) -> None:
        self._align = align

    def setBackground(self, *_args) -> None: ...
    def setForeground(self, *_args) -> None: ...
    def setFont(self, *_args) -> None: ...


class _HeaderView:
    def __init__(self, table: "QTableWidget", horizontal: bool):
        self._table, self._horizontal = table, horizontal

    def setVisible(self, visible: bool) -> None:
        attr = "_show_hheader" if self._horizontal else "_show_vheader"
        setattr(self._table, attr, bool(visible))
        self._table._render()

    def hide(self) -> None:
        self.setVisible(False)

    def setSectionResizeMode(self, *_args) -> None: ...
    def setStretchLastSection(self, *_args) -> None: ...
    def setDefaultAlignment(self, *_args) -> None: ...


class QTableWidget(QAbstractScrollArea):
    EditTrigger = Qt.EditTrigger
    SelectionBehavior = Qt.SelectionBehavior
    SelectionMode = Qt.SelectionMode

    def __init__(self, rows=0, columns=0, parent=None):
        if isinstance(rows, QWidget):
            rows, parent = 0, rows
        super().__init__(parent)
        self._node = make_node("div", "qw QTableWidget")
        self._rows, self._cols = int(rows), int(columns)
        self._items: dict[tuple[int, int], QTableWidgetItem] = {}
        self._hlabels: list[str] = []
        self._vlabels: list[str] = []
        self._show_hheader = self._show_vheader = True
        self._render()

    def setRowCount(self, rows: int) -> None:
        self._rows = int(rows)
        self._items = {k: v for k, v in self._items.items() if k[0] < self._rows}
        self._render()

    def setColumnCount(self, columns: int) -> None:
        self._cols = int(columns)
        self._render()

    def rowCount(self) -> int:
        return self._rows

    def columnCount(self) -> int:
        return self._cols

    def setHorizontalHeaderLabels(self, labels) -> None:
        self._hlabels = list(labels)
        self._cols = max(self._cols, len(self._hlabels))
        self._render()

    def setVerticalHeaderLabels(self, labels) -> None:
        self._vlabels = list(labels)
        self._rows = max(self._rows, len(self._vlabels))
        self._render()

    def setItem(self, row: int, column: int, item: QTableWidgetItem) -> None:
        item._table = self
        self._items[(row, column)] = item
        self._render()

    def item(self, row: int, column: int):
        return self._items.get((row, column))

    def clearContents(self) -> None:
        self._items.clear()
        self._render()

    def horizontalHeader(self) -> _HeaderView:
        return _HeaderView(self, True)

    def verticalHeader(self) -> _HeaderView:
        return _HeaderView(self, False)

    def _render(self) -> None:
        from html import escape
        rows = []
        if self._show_hheader and self._hlabels:
            corner = "<th></th>" if self._show_vheader and self._vlabels else ""
            rows.append("<tr>" + corner + "".join(
                f"<th>{escape(h)}</th>" for h in self._hlabels) + "</tr>")
        for r in range(self._rows):
            cells = []
            if self._show_vheader and self._vlabels:
                label = self._vlabels[r] if r < len(self._vlabels) else ""
                cells.append(f"<th>{escape(label)}</th>")
            for c in range(self._cols):
                item = self._items.get((r, c))
                tip = f' title="{escape(item._tooltip)}"' if item and item._tooltip else ""
                cells.append(f"<td{tip}>{escape(item.text()) if item else ''}</td>")
            rows.append("<tr>" + "".join(cells) + "</tr>")
        self._node.set_html("<table>" + "".join(rows) + "</table>")

    def resizeColumnsToContents(self) -> None: ...
    def resizeRowsToContents(self) -> None: ...
    def setEditTriggers(self, *_args) -> None: ...
    def setSelectionBehavior(self, *_args) -> None: ...
    def setSelectionMode(self, *_args) -> None: ...
    def setAlternatingRowColors(self, *_args) -> None: ...
    def setSortingEnabled(self, *_args) -> None: ...
    def setWordWrap(self, *_args) -> None: ...
    def setShowGrid(self, *_args) -> None: ...


class QTabWidget(QWidget):
    currentChanged = pyqtSignal(int)
    tabBarClicked = pyqtSignal(int)

    _default_grows = (True, True)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bar = make_node("div", "qtabbar")
        self._stack = make_node("div", "qtabstack")
        self._node.append(self._bar)
        self._node.append(self._stack)
        self._tabs: list[tuple[QWidget, str, object]] = []  # widget, label, button node
        self._index = -1

    def addTab(self, widget: QWidget, label: str) -> int:
        return self.insertTab(len(self._tabs), widget, label)

    def insertTab(self, index: int, widget: QWidget, label: str) -> int:
        widget._detach()
        widget._set_parent_widget(self)
        widget._owner_container = self
        button = make_node("button", "qtab")
        button.set_text(strip_mnemonic(label))
        self._tabs.insert(index, (widget, label, button))
        self._bar.insert(index, button)
        self._stack.append(widget._node)
        self._rebind_buttons()
        if self._index == -1:
            self._set_index(0)
        else:
            if index <= self._index:
                self._index += 1
            self._sync()
        return index

    def _rebind_buttons(self) -> None:
        for i, (_w, _l, button) in enumerate(self._tabs):
            if not getattr(button, "_qt_bound", False):
                button.on("click", lambda b=button: self._user_tab(b))
                button._qt_bound = True

    def _user_tab(self, button) -> None:
        index = next(i for i, t in enumerate(self._tabs) if t[2] is button)
        self.tabBarClicked.emit(index)
        self.setCurrentIndex(index)

    def _release_child(self, widget: QWidget) -> None:
        index = self.indexOf(widget)
        if index >= 0:
            self.removeTab(index)

    def removeTab(self, index: int) -> None:
        widget, _label, button = self._tabs.pop(index)
        self._bar.remove_child(button)
        self._stack.remove_child(widget._node)
        widget._owner_container = None
        if not self._tabs:
            self._set_index(-1)
        elif index < self._index or self._index >= len(self._tabs):
            self._index = -2
            self._set_index(max(0, min(index, len(self._tabs) - 1)))
        elif index == self._index:
            self._index = -2
            self._set_index(min(index, len(self._tabs) - 1))
        else:
            self._sync()

    def clear(self) -> None:
        while self._tabs:
            self.removeTab(len(self._tabs) - 1)

    def count(self) -> int:
        return len(self._tabs)

    def widget(self, index: int):
        return self._tabs[index][0] if 0 <= index < len(self._tabs) else None

    def indexOf(self, widget) -> int:
        return next((i for i, t in enumerate(self._tabs) if t[0] is widget), -1)

    def currentIndex(self) -> int:
        return self._index

    def currentWidget(self):
        return self.widget(self._index)

    def setCurrentIndex(self, index: int) -> None:
        if 0 <= index < len(self._tabs):
            self._set_index(index)

    def setCurrentWidget(self, widget) -> None:
        self.setCurrentIndex(self.indexOf(widget))

    def tabText(self, index: int) -> str:
        return self._tabs[index][1]

    def setTabText(self, index: int, label: str) -> None:
        widget, _old, button = self._tabs[index]
        self._tabs[index] = (widget, label, button)
        button.set_text(strip_mnemonic(label))

    def _set_index(self, index: int) -> None:
        if index == self._index:
            return
        self._index = index
        self._sync()
        self.currentChanged.emit(index)

    def _sync(self) -> None:
        for i, (widget, _label, button) in enumerate(self._tabs):
            current = i == self._index
            button.toggle_class("qcurrent", current)
            # Only the current page is visible (Qt hides the others, which
            # is what makes isVisible() false on background tabs).
            widget._explicitly_hidden = not current
            widget._node.toggle_class("qhidden", not current)

    def setTabPosition(self, *_args) -> None: ...
    def setDocumentMode(self, *_args) -> None: ...
    def setTabsClosable(self, *_args) -> None: ...
    def setMovable(self, *_args) -> None: ...


class QStatusBar(QWidget):
    messageChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._message = ""

    def showMessage(self, message: str, _timeout: int = 0) -> None:
        self._message = message
        self._node.set_text(message)
        self.messageChanged.emit(message)

    def clearMessage(self) -> None:
        self.showMessage("")

    def currentMessage(self) -> str:
        return self._message


class QMenu(QWidget):
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self._title = title
        self._actions: list = []

    def addAction(self, action, *args):
        if isinstance(action, str):
            from PyQt6.QtGui import QAction
            action = QAction(action, self)
        self._actions.append(action)
        return action

    def addSeparator(self) -> None:
        self._actions.append(None)

    def addMenu(self, title: str) -> "QMenu":
        menu = QMenu(title, self)
        self._actions.append(menu)
        return menu

    def actions(self) -> list:
        return [a for a in self._actions if a is not None]


class QMenuBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._menus: list[QMenu] = []

    def addMenu(self, title: str) -> QMenu:
        menu = QMenu(title, self)
        self._menus.append(menu)
        return menu


class QMainWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._central: QWidget | None = None
        self._central_slot = make_node("div", "qcentral")
        self._node.append(self._central_slot)
        self._menu_bar: QMenuBar | None = None
        self._status_bar: QStatusBar | None = None

    def setCentralWidget(self, widget: QWidget) -> None:
        if self._central is not None:
            self._central_slot.remove_child(self._central._node)
        self._central = widget
        widget._set_parent_widget(self)
        widget._owner_container = self
        self._central_slot.append(widget._node)

    def _release_child(self, widget: QWidget) -> None:
        if widget is self._central:
            self._central_slot.remove_child(widget._node)
            self._central = None

    def centralWidget(self):
        return self._central

    def menuBar(self) -> QMenuBar:
        # The desktop menus are placeholders apart from File → Exit, which
        # has no meaning in a browser tab, so the bar is not rendered.
        if self._menu_bar is None:
            self._menu_bar = QMenuBar(self)
        return self._menu_bar

    def setStatusBar(self, bar: QStatusBar) -> None:
        self._status_bar = bar
        bar._set_parent_widget(self)
        self._node.append(bar._node)

    def statusBar(self) -> QStatusBar:
        if self._status_bar is None:
            self.setStatusBar(QStatusBar())
        return self._status_bar


class QDialog(QWidget):
    accepted = pyqtSignal()
    rejected = pyqtSignal()
    finished = pyqtSignal(int)

    def __init__(self, parent=None, *args):
        super().__init__(None)  # dialogs are top-level windows
        self._node.toggle_class("qhidden", True)
        self._explicitly_hidden = True

    def show(self) -> None:
        nodes.show_dialog(self)
        self._explicitly_hidden = False
        self._shown_window = True
        self._node.toggle_class("qhidden", False)

    def exec(self) -> int:
        # A browser can't block for a modal result; the dialog stays open
        # and the caller continues (the app only uses exec() to display).
        self.show()
        return 0

    exec_ = exec

    def done(self, result: int) -> None:
        self.close()
        self.finished.emit(result)

    def accept(self) -> None:
        self.done(1)
        self.accepted.emit()

    def reject(self) -> None:
        self.done(0)
        self.rejected.emit()

    def close(self) -> bool:
        nodes.hide_dialog(self)
        self._explicitly_hidden = True
        self._node.toggle_class("qhidden", True)
        return True

    def setModal(self, *_args) -> None: ...


# ── Layouts ───────────────────────────────────────────────────────────

class _LayoutItem:
    def __init__(self, kind: str, obj=None, stretch: int = 0, node=None,
                 alignment=None, grid=None):
        self.kind, self.obj, self.stretch = kind, obj, stretch
        self.node, self.alignment, self.grid = node, alignment, grid

    def widget(self):
        return self.obj if self.kind == "widget" else None

    def layout(self):
        return self.obj if self.kind == "layout" else None

    def spacerItem(self):
        return self if self.kind in ("stretch", "spacing") else None


class QLayout(QObject):
    _direction = "column"

    def __init__(self, parent=None):
        super().__init__(parent if isinstance(parent, QWidget) else None)
        self._node = make_node("div", "qlayout " + type(self).__name__)
        self._items: list[_LayoutItem] = []
        self._parent_widget: QWidget | None = None
        self._nested = False
        self._margins_set = False
        self.setSpacing(6)
        if isinstance(parent, QWidget):
            parent.setLayout(self)

    # ── attachment ──
    def _attach_to_widget(self, widget: QWidget) -> None:
        self._parent_widget = widget
        if not self._margins_set and not self._nested:
            self._node.set_style(padding="9px")
        for item in self._items:
            self._adopt(item)

    def _adopt(self, item: _LayoutItem) -> None:
        if self._parent_widget is None:
            return
        if item.kind == "widget":
            item.obj._set_parent_widget(self._parent_widget)
        elif item.kind == "layout":
            item.obj._attach_to_widget(self._parent_widget)

    def parentWidget(self):
        return self._parent_widget

    def _all_widgets(self) -> list[QWidget]:
        out = []
        for item in self._items:
            if item.kind == "widget":
                out.append(item.obj)
            elif item.kind == "layout":
                out.extend(item.obj._all_widgets())
        return out

    # ── adding ──
    def _add_item(self, item: _LayoutItem, index: int | None = None) -> None:
        if index is None or index < 0 or index >= len(self._items):
            self._items.append(item)
            self._node.append(item.node)
        else:
            self._items.insert(index, item)
            self._node.insert(index, item.node)
        self._apply_item_style(item)
        self._adopt(item)

    def addWidget(self, widget: QWidget, stretch: int = 0, alignment=None) -> None:
        self.insertWidget(-1, widget, stretch, alignment)

    def insertWidget(self, index: int, widget: QWidget, stretch: int = 0,
                     alignment=None) -> None:
        if not isinstance(stretch, int):  # addWidget(w, alignment=…) positional
            stretch, alignment = 0, stretch
        widget._detach()
        widget._owner_layout = self
        self._add_item(_LayoutItem("widget", widget, stretch, widget._node,
                                   alignment), index)

    def addLayout(self, layout: "QLayout", stretch: int = 0) -> None:
        self.insertLayout(-1, layout, stretch)

    def insertLayout(self, index: int, layout: "QLayout", stretch: int = 0) -> None:
        layout._nested = True
        if not layout._margins_set:
            layout._node.set_style(padding="0")
        self._add_item(_LayoutItem("layout", layout, stretch, layout._node), index)

    def addStretch(self, stretch: int = 0) -> None:
        self.insertStretch(-1, stretch)

    def insertStretch(self, index: int, stretch: int = 0) -> None:
        node = make_node("div", "qstretch")
        node.set_style(flex=f"{max(stretch, 1)} 1 0px")
        self._add_item(_LayoutItem("stretch", None, stretch, node), index)

    def addSpacing(self, size: int) -> None:
        node = make_node("div", "qspacing")
        node.set_style(flex=f"0 0 {int(size)}px")
        self._add_item(_LayoutItem("spacing", None, 0, node))

    def addSpacerItem(self, _spacer) -> None:
        self.addStretch()

    def addItem(self, _item) -> None:
        self.addStretch()

    # ── removing ──
    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int):
        if not 0 <= index < len(self._items):
            return None
        item = self._items.pop(index)
        self._node.remove_child(item.node)
        if item.kind == "widget":
            item.obj._owner_layout = None
        return item

    def removeWidget(self, widget: QWidget) -> None:
        for i, item in enumerate(self._items):
            if item.obj is widget:
                self.takeAt(i)
                return

    def indexOf(self, widget) -> int:
        return next((i for i, item in enumerate(self._items)
                     if item.obj is widget), -1)

    def _grows(self) -> tuple[bool, bool]:
        grows_h = grows_v = False
        for item in self._items:
            if item.kind == "widget":
                h, v = item.obj._grows()
            elif item.kind == "layout":
                h, v = item.obj._grows()
            else:
                continue
            grows_h, grows_v = grows_h or h, grows_v or v
        return grows_h, grows_v

    def _item_for(self, widget):
        return next((item for item in self._items if item.obj is widget), None)

    # ── appearance ──
    def setContentsMargins(self, left, top=None, right=None, bottom=None) -> None:
        if top is None:  # QMargins
            left, top, right, bottom = (left.left(), left.top(),
                                        left.right(), left.bottom())
        self._margins_set = True
        self._node.set_style(padding=f"{top}px {right}px {bottom}px {left}px")

    def setSpacing(self, spacing: int) -> None:
        self._node.set_style(gap=f"{max(int(spacing), 0)}px")

    def spacing(self) -> int:
        return 6

    def setStretch(self, index: int, stretch: int) -> None:
        if 0 <= index < len(self._items):
            self._items[index].stretch = stretch
            self._apply_item_style(self._items[index])

    def setAlignment(self, *args) -> None:
        if len(args) == 1:
            alignment = args[0]
            if "AlignTop" in alignment:
                self._node.set_style(justify_content="flex-start")
            elif "AlignCenter" in alignment or "AlignHCenter" in alignment:
                self._node.set_style(align_items="center")
        elif len(args) == 2 and isinstance(args[0], QWidget):
            item = self._item_for(args[0])
            if item is not None:
                item.alignment = args[1]
                self._apply_item_style(item)

    def setSizeConstraint(self, *_args) -> None: ...

    def _apply_item_style(self, item: _LayoutItem) -> None:
        """Flex sizing for one child: Qt stretch factor / size policy → CSS."""
        if item.kind in ("stretch", "spacing"):
            return
        horizontal = self._direction == "row"
        grows_h, grows_v = item.obj._grows()
        grows_main = grows_h if horizontal else grows_v
        if item.stretch > 0:
            # Stretch factors set the proportions; the flex basis comes
            # from qtshim.css (.qstretched), which differs inside scroll
            # areas, where Qt gives each item its full size hint.
            item.node.set_style(flex=None, flex_grow=str(item.stretch),
                                flex_shrink="1")
        else:
            item.node.set_style(flex_grow=None, flex_shrink=None,
                                flex="1 1 auto" if grows_main else "0 1 auto")
        item.node.toggle_class("qstretched", item.stretch > 0)
        align = None
        if item.alignment is not None:
            names = item.alignment.names
            if names & {"AlignCenter", "AlignHCenter" if not horizontal else "AlignVCenter"}:
                align = "center"
            elif names & ({"AlignLeft"} if not horizontal else {"AlignTop"}):
                align = "flex-start"
            elif names & ({"AlignRight"} if not horizontal else {"AlignBottom"}):
                align = "flex-end"
        item.node.set_style(align_self=align)


class QBoxLayout(QLayout):
    pass


class QVBoxLayout(QBoxLayout):
    _direction = "column"


class QHBoxLayout(QBoxLayout):
    _direction = "row"


class QGridLayout(QLayout):
    _direction = "grid"

    def addWidget(self, widget: QWidget, row: int = 0, column: int = 0,
                  row_span: int = 1, column_span: int = 1, alignment=None) -> None:
        widget._detach()
        widget._owner_layout = self
        item = _LayoutItem("widget", widget, 0, widget._node, alignment,
                           grid=(row, column, row_span, column_span))
        self._add_item(item)

    def addLayout(self, layout: QLayout, row: int = 0, column: int = 0,
                  row_span: int = 1, column_span: int = 1, alignment=None) -> None:
        layout._nested = True
        if not layout._margins_set:
            layout._node.set_style(padding="0")
        self._add_item(_LayoutItem("layout", layout, 0, layout._node,
                                   grid=(row, column, row_span, column_span)))

    def _apply_item_style(self, item: _LayoutItem) -> None:
        if item.grid is None:
            return
        row, column, row_span, column_span = item.grid
        item.node.set_style(
            grid_row=f"{row + 1} / span {max(row_span, 1)}",
            grid_column=f"{column + 1} / span {max(column_span, 1)}")

    def setHorizontalSpacing(self, spacing: int) -> None:
        self._node.set_style(column_gap=f"{spacing}px")

    def setVerticalSpacing(self, spacing: int) -> None:
        self._node.set_style(row_gap=f"{spacing}px")

    def setColumnStretch(self, *_args) -> None: ...
    def setRowStretch(self, *_args) -> None: ...


class QFormLayout(QGridLayout):
    def addRow(self, label, field=None) -> None:
        row = len({item.grid[0] for item in self._items if item.grid})
        if isinstance(label, str):
            label = QLabel(label)
        if field is None:
            self.addWidget(label, row, 0, 1, 2)
            return
        self.addWidget(label, row, 0)
        if isinstance(field, QLayout):
            self.addLayout(field, row, 1)
        else:
            self.addWidget(field, row, 1)


class QSpacerItem:
    def __init__(self, *_args):
        pass


class QLineEdit(QWidget):
    textChanged = pyqtSignal(str)
    editingFinished = pyqtSignal()
    returnPressed = pyqtSignal()

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._node = make_node("input", "qw QLineEdit")
        self._text = ""
        self._node.on("change", self._user_edit)
        self.setText(text)

    def setText(self, text: str) -> None:
        changed = text != self._text
        self._text = text or ""
        self._node.set_prop("value", self._text)
        if changed:
            self.textChanged.emit(self._text)

    def text(self) -> str:
        return self._text

    def _user_edit(self) -> None:
        self.setText(str(self._node.get_prop("value") or ""))
        self.editingFinished.emit()

    def setPlaceholderText(self, text: str) -> None:
        self._node.set_attr("placeholder", text)

    def setReadOnly(self, on: bool) -> None:
        self._node.set_prop("readOnly", bool(on))

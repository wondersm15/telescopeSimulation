"""Display nodes behind the Qt stand-in widgets.

Every shim widget owns one `Node` per visible element and pushes its state
into it (text, style, enabled, …). The widget, not the node, holds the
state that the application reads back, so the same widget code runs:

* natively, with the do-nothing `Node` below (tests: drive the real
  telescope_gui code with the shim and compare against real Qt), and
* in the browser, with `qtshim.dom.DomNode`, which mirrors each call onto a
  real HTML element.

`make_node` is the single factory every widget calls; `qtshim.dom.install`
swaps it for the DOM implementation.
"""

from __future__ import annotations

from typing import Callable


class Node:
    """Headless node: accepts every call, renders nothing."""

    def __init__(self, tag: str = "div", class_name: str = ""):
        self.tag = tag
        self.class_name = class_name

    # Content
    def set_text(self, text: str) -> None: ...
    def set_html(self, html: str) -> None: ...
    def set_image_png(self, png: bytes | None) -> None: ...

    # Appearance
    def set_style(self, **styles: str | None) -> None: ...
    def set_css_text(self, css: str) -> None: ...
    def set_attr(self, name: str, value: str | None) -> None: ...
    def set_prop(self, name: str, value) -> None: ...
    def toggle_class(self, name: str, on: bool) -> None: ...

    # Tree
    def append(self, child: "Node") -> None: ...
    def insert(self, index: int, child: "Node") -> None: ...
    def remove_child(self, child: "Node") -> None: ...
    def clear(self) -> None: ...

    # Events. `on` calls fn() when the DOM event fires; the widget then reads
    # what it needs with get_prop. `on_link` calls fn(href) for a click on
    # an <a> inside the node (Qt's QLabel.linkActivated).
    def on(self, event: str, fn: Callable[[], None]) -> None: ...
    def on_link(self, fn: Callable[[str], None]) -> None: ...

    def get_prop(self, name: str):
        return None

    # Geometry (meaningful only in a browser)
    def offset_top_in(self, ancestor: "Node") -> int:
        return 0

    def scroll_top(self, value: int | None = None) -> int:
        return 0

    def scroll_height(self) -> int:
        return 0

    def client_width(self) -> int:
        return 0


_factory: Callable[..., Node] = Node


def make_node(tag: str = "div", class_name: str = "") -> Node:
    return _factory(tag, class_name)


def set_node_factory(factory: Callable[..., Node]) -> None:
    global _factory
    _factory = factory


# Deferred calls (QTimer). Headless runs queue them for `run_pending`;
# the browser backend replaces `call_later` with setTimeout.
_pending: list[Callable] = []


def _queue_call(_ms: int, fn: Callable) -> None:
    _pending.append(fn)


call_later: Callable[[int, Callable], None] = _queue_call


def set_call_later(fn: Callable[[int, Callable], None]) -> None:
    global call_later
    call_later = fn


def copy_to_clipboard(text: str) -> None:
    """Headless: nothing to copy to. The browser backend replaces this."""


def open_url(url: str) -> None:
    """Headless: no browser. The DOM backend opens a new tab."""


def show_dialog(dialog) -> None:
    """Headless: dialogs have nowhere to appear. DOM backend: modal overlay."""


def hide_dialog(dialog) -> None:
    """Counterpart of show_dialog."""


def run_pending() -> None:
    """Run queued QTimer callbacks (headless event-loop turn)."""
    while _pending:
        _pending.pop(0)()

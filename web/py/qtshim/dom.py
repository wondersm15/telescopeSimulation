"""Browser backend for the Qt stand-in: widgets become HTML elements.

Only importable under Pyodide (uses the `js` module). `install()` makes
every widget created afterwards render into the page, and routes QTimer,
the clipboard, external links and dialogs to their browser equivalents.

Pyodide runs on the page's main thread, so while Python computes (a
simulation can take a few seconds) the page cannot repaint. Event handlers
therefore show a "Working…" indicator first and run the Python code on the
next frame, so the user sees that their click registered.
"""

from __future__ import annotations

import base64
import traceback

import js
from pyodide.ffi import create_once_callable, create_proxy

from qtshim import nodes

_listeners: list = []  # keep JS proxies alive for the lifetime of the page


def _report(exc: BaseException) -> None:
    js.console.error("".join(traceback.format_exception(exc)))


class DomNode(nodes.Node):
    renders = True

    def __init__(self, tag: str = "div", class_name: str = ""):
        super().__init__(tag, class_name)
        self.el = js.document.createElement(tag)
        if class_name:
            self.el.className = class_name
        self._styles: dict[str, str] = {}
        self._css_text = ""
        self._img = None
        self._image_url = None

    # Content
    def set_text(self, text: str) -> None:
        self.el.textContent = text

    def set_html(self, html: str) -> None:
        self.el.innerHTML = html

    def set_image_png(self, png: bytes | None) -> None:
        img = self.el if self.tag == "img" else self._image_child()
        if png is None:
            img.removeAttribute("src")
            img.hidden = True
            return
        img.hidden = False
        img.src = "data:image/png;base64," + base64.b64encode(png).decode("ascii")

    def _image_child(self):
        if self._img is None:
            self._img = js.document.createElement("img")
            self.el.replaceChildren(self._img)
        return self._img

    # Appearance. Structural styles (set_style) are kept apart from the
    # widget's style sheet (set_css_text) so replacing one keeps the other.
    def set_style(self, **styles: str | None) -> None:
        for key, value in styles.items():
            prop = key.replace("_", "-")
            if value is None:
                self._styles.pop(prop, None)
                self.el.style.removeProperty(prop)
            else:
                self._styles[prop] = value
                self.el.style.setProperty(prop, value)

    def set_css_text(self, css: str) -> None:
        self._css_text = css
        self.el.style.cssText = css
        for prop, value in self._styles.items():
            self.el.style.setProperty(prop, value)

    def set_attr(self, name: str, value: str | None) -> None:
        if value is None:
            self.el.removeAttribute(name)
        else:
            self.el.setAttribute(name, value)

    def set_prop(self, name: str, value) -> None:
        setattr(self.el, name, value)

    def toggle_class(self, name: str, on: bool) -> None:
        self.el.classList.toggle(name, bool(on))

    # Tree
    def append(self, child: "DomNode") -> None:
        self.el.appendChild(child.el)

    def insert(self, index: int, child: "DomNode") -> None:
        ref = self.el.children.item(index)
        self.el.insertBefore(child.el, ref)

    def remove_child(self, child: "DomNode") -> None:
        if child.el.parentNode == self.el:
            self.el.removeChild(child.el)

    def clear(self) -> None:
        self.el.replaceChildren()
        self._img = None

    # Events
    def on(self, event: str, fn) -> None:
        proxy = create_proxy(lambda _e: run_busy(fn))
        _listeners.append(proxy)
        self.el.addEventListener(event, proxy)

    def on_link(self, fn) -> None:
        def handler(e):
            anchor = e.target.closest("a")
            if anchor is None:
                return
            e.preventDefault()
            href = anchor.getAttribute("href")
            run_busy(lambda: fn(href))
        proxy = create_proxy(handler)
        _listeners.append(proxy)
        self.el.addEventListener("click", proxy)

    def get_prop(self, name: str):
        return getattr(self.el, name)

    # Geometry
    def offset_top_in(self, ancestor: "DomNode") -> int:
        here = self.el.getBoundingClientRect().top
        there = ancestor.el.getBoundingClientRect().top
        return int(here - there + ancestor.el.scrollTop)

    def scroll_top(self, value: int | None = None) -> int:
        if value is not None:
            self.el.scrollTop = value
        return int(self.el.scrollTop)

    def scroll_height(self) -> int:
        return int(self.el.scrollHeight - self.el.clientHeight)

    def client_width(self) -> int:
        return int(self.el.clientWidth)


# ── Busy indicator + deferred work ────────────────────────────────────

_busy_depth = 0


def run_busy(fn) -> None:
    """Show "Working…", let the browser paint it, then run fn."""
    global _busy_depth
    _busy_depth += 1
    js.document.body.classList.add("qbusy")

    def run(*_args):
        global _busy_depth
        try:
            fn()
        except Exception as exc:  # keep the page alive; report like Qt does
            _report(exc)
        finally:
            _busy_depth -= 1
            if _busy_depth == 0:
                js.document.body.classList.remove("qbusy")

    # Two animation frames: the first schedules after the next paint.
    js.requestAnimationFrame(create_once_callable(
        lambda _t: js.setTimeout(create_once_callable(run), 0)))


def _call_later(ms: int, fn) -> None:
    def run(*_args):
        try:
            fn()
        except Exception as exc:
            _report(exc)
    js.setTimeout(create_once_callable(run), ms)


def _copy_to_clipboard(text: str) -> None:
    js.navigator.clipboard.writeText(text)


def _open_url(url: str) -> None:
    js.window.open(url, "_blank", "noopener")


# ── Dialogs: a modal overlay with a title bar and close button ────────

_overlays: dict[int, object] = {}


def _show_dialog(dialog) -> None:
    if id(dialog) in _overlays:
        return
    overlay = js.document.createElement("div")
    overlay.className = "qdialog-overlay"
    frame = js.document.createElement("div")
    frame.className = "qdialog-frame"
    bar = js.document.createElement("div")
    bar.className = "qdialog-title"
    title = js.document.createElement("span")
    title.textContent = dialog.windowTitle()
    close = js.document.createElement("button")
    close.textContent = "×"
    close.title = "Close"
    proxy = create_proxy(lambda _e: dialog.reject())
    _listeners.append(proxy)
    close.addEventListener("click", proxy)
    bar.append(title, close)
    frame.append(bar, dialog._node.el)
    overlay.appendChild(frame)
    js.document.body.appendChild(overlay)
    _overlays[id(dialog)] = overlay


def _hide_dialog(dialog) -> None:
    overlay = _overlays.pop(id(dialog), None)
    if overlay is not None:
        overlay.remove()


def install() -> None:
    nodes.set_node_factory(DomNode)
    nodes.set_call_later(_call_later)
    nodes.copy_to_clipboard = _copy_to_clipboard
    nodes.open_url = _open_url
    nodes.show_dialog = _show_dialog
    nodes.hide_dialog = _hide_dialog


def mount(widget, container) -> None:
    """Show a top-level widget inside the page element `container`."""
    container.replaceChildren(widget._node.el)

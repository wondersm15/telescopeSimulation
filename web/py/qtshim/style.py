"""Qt style sheets → inline CSS, and Qt text conventions → HTML.

Qt style sheets are close to CSS. A sheet is either bare declarations
("color: red; font-size: 9pt") that apply to the widget itself, or rule
blocks ("QGroupBox { … } QGroupBox::title { … }"). Blocks whose selector
names one of the widget's Qt classes apply; sub-controls (::title) and
pseudo-states (:hover) are dropped — they are cosmetic.
"""

from __future__ import annotations

import re
from html import escape

_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")
_RICH_TEXT = re.compile(r"<\s*[a-zA-Z!/][^>]*>")


def qss_to_css(sheet: str, class_names: tuple[str, ...]) -> str:
    sheet = re.sub(r"/\*.*?\*/", "", sheet or "", flags=re.S)
    if "{" not in sheet:
        return _clean_declarations(sheet)
    css = []
    for selectors, body in _RULE.findall(sheet):
        for selector in selectors.split(","):
            selector = selector.strip()
            if ":" in selector or " " in selector or ">" in selector:
                continue
            name = selector.split("#")[0].split(".")[0]
            if name in ("", "*") or name in class_names:
                css.append(_clean_declarations(body))
                break
    return ";".join(c for c in css if c)


def _clean_declarations(body: str) -> str:
    keep = []
    for decl in body.split(";"):
        if ":" not in decl:
            continue
        prop, value = (part.strip() for part in decl.split(":", 1))
        # qproperty-* and Qt-only extensions have no CSS meaning.
        if prop.startswith(("qproperty-", "subcontrol-", "selection-")):
            continue
        keep.append(f"{prop}: {value}")
    return ";".join(keep)


def might_be_rich_text(text: str) -> bool:
    """Qt::mightBeRichText — labels in AutoText format render tags as HTML."""
    return bool(_RICH_TEXT.search(text or ""))


def strip_mnemonic(text: str) -> str:
    """'&File' → 'File', 'A && B' → 'A & B' (Qt keyboard-mnemonic markup)."""
    return re.sub(r"&(&?)", lambda m: m.group(1), text or "")


def plain_to_html(text: str) -> str:
    return escape(text or "")

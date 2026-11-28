"""Bridge to the exam engine (engine/reader/index.html) as a Streamlit custom component.

No build step: the component is a static folder that speaks Streamlit's
postMessage protocol directly."""
from pathlib import Path

import streamlit.components.v1 as components

_ENGINE = Path(__file__).resolve().parent.parent / "engine"
_reader = components.declare_component("memora_reader", path=str(_ENGINE / "reader"))
_cookie = components.declare_component("memora_cookie", path=str(_ENGINE / "cookie_bridge"))


def reader(test: dict, meta: dict, saved: dict | None, prefs: dict, session_key: str,
           scope: str = "full", theme: str | None = None,
           nav: dict | None = None, reveal: dict | None = None, height: int = 800, key: str | None = None):
    """Render the exam. Returns the latest event dict from the browser (or None).
    `reveal` (đáp án + lời giải) chỉ truyền sau khi bài đã nộp; khi làm bài `test` không chứa đáp án."""
    return _reader(test=test, meta=meta, saved=saved or {}, prefs=prefs or {},
                   sessionKey=session_key, scope=scope, theme=theme, nav=nav or {}, reveal=reveal,
                   height=height, key=key, default=None)


def cookie_bridge(action: str, name: str, value: str = "", days: int = 14, key: str = "cookie_bridge"):
    """Invisible component that sets/clears a browser cookie (Streamlit cannot do this itself)."""
    return _cookie(action=action, name=name, value=value, days=days, key=key, default=None)

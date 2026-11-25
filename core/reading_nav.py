import streamlit as st

from core import catalog as cat_mod


def current_category(catalog: dict) -> dict:
    """Mục đang xem trong Reading: theo lựa chọn ở sidebar, mặc định là mục đầu tiên đã có đề."""
    cats = catalog["categories"]
    wanted = st.session_state.get("reading_cat")
    for c in cats:
        if c["id"] == wanted:
            return c
    for c in cats:
        if c["series"]:
            return c
    return cats[0]


def open_test(test_id: str, scope: str = "full") -> None:
    """Mở đề. scope = "full" (cả đề) hoặc "p1".."pN" (chỉ làm passage đó)."""
    st.session_state["reading_test"] = test_id
    st.session_state["reading_scope"] = scope
    st.session_state["reading_opens"] = st.session_state.get("reading_opens", 0) + 1
    entry = cat_mod.find_test_entry(cat_mod.load_catalog(), test_id)
    if entry:
        st.session_state["reading_cat"] = entry["category"]      # thoát ra thì về đúng mục chứa đề này


def close_test() -> None:
    st.session_state["reading_test"] = None

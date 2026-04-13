"""
Shop form components for the Shop Management app.
"""

import streamlit as st
from db_handler import add_shop, update_shop, remove_shop


def render_add_shop_form() -> None:
    """Render add shop form."""
    shop_col1, shop_col2 = st.columns([2, 1])
    with shop_col1:
        new_shop_name = st.text_input("Enter shop name:", key="add_shop_input")
    with shop_col2:
        st.space(size='small')
        if st.button("Add Shop", key="add_shop_button"):
            if new_shop_name.strip():
                try:
                    new_id = add_shop(new_shop_name.strip())
                    st.success(f"Shop '{new_shop_name}' added with ID: {new_id}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding shop: {e}")
            else:
                st.warning("Please enter a shop name.")


def render_edit_shop_form(shop_id: int, current_name: str) -> None:
    """
    Render edit shop form.
    
    Parameters:
        shop_id: ID of the shop to edit
        current_name: Current shop name
    """
    new_name = st.text_input(
        f"Edit shop name for ID {shop_id}",
        value=current_name,
        key=f"edit_input_{shop_id}"
    )
    save_col, cancel_col = st.columns([1, 1])
    with save_col:
        if st.button("💾 Save", key=f"save_btn_{shop_id}"):
            try:
                if update_shop(shop_id, new_name):
                    st.success(f"Shop name updated to '{new_name}'")
                    st.session_state[f"editing_{shop_id}"] = False
                    st.rerun()
                else:
                    st.error("Shop not found")
            except Exception as e:
                st.error(f"Error updating shop: {e}")
    with cancel_col:
        if st.button("❌ Cancel", key=f"cancel_btn_{shop_id}"):
            st.session_state[f"editing_{shop_id}"] = False
            st.rerun()


def render_remove_shop_form(shop_id: int, shop_name: str) -> None:
    """
    Render remove shop button.
    
    Parameters:
        shop_id: ID of the shop to remove
        shop_name: Name of the shop
    """
    if st.button("🗑️", key=f"remove_btn_{shop_id}"):
        try:
            if remove_shop(shop_id):
                st.success(f"Shop '{shop_name}' removed")
                st.rerun()
            else:
                st.error("Shop not found")
        except Exception as e:
            st.error(f"Error removing shop: {e}")

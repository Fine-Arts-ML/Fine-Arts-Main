"""
Centralized session state management for the Shop Management app.
"""

import streamlit as st


def get_files_loaded(shop_id: int) -> int:
    """Get the number of files loaded for a shop."""
    if f"loaded_{shop_id}" not in st.session_state:
        st.session_state[f"loaded_{shop_id}"] = 0
    return st.session_state[f"loaded_{shop_id}"]


def set_files_loaded(shop_id: int, count: int) -> None:
    """Set the number of files loaded for a shop."""
    st.session_state[f"loaded_{shop_id}"] = count


def get_files_list(shop_id: int) -> list:
    """Get the list of files for a shop."""
    if f"files_{shop_id}" not in st.session_state:
        st.session_state[f"files_{shop_id}"] = []
    return st.session_state[f"files_{shop_id}"]


def set_files_list(shop_id: int, files: list) -> None:
    """Set the list of files for a shop."""
    st.session_state[f"files_{shop_id}"] = files


def get_editing_state(key: str, default: bool = False) -> bool:
    """Get the editing state for a given key."""
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


def set_editing_state(key: str, value: bool) -> None:
    """Set the editing state for a given key."""
    st.session_state[key] = value


def get_selected_file(shop_id: int) -> dict | None:
    """Get the currently selected file for a shop."""
    key = f"selected_file_{shop_id}"
    return st.session_state.get(key, None)


def set_selected_file(shop_id: int, file_data: dict) -> None:
    """Set the currently selected file for a shop."""
    st.session_state[f"selected_file_{shop_id}"] = file_data


def clear_selected_file(shop_id: int) -> None:
    """Clear the currently selected file for a shop."""
    key = f"selected_file_{shop_id}"
    if key in st.session_state:
        del st.session_state[key]


def get_account_files_loaded(account_id: int) -> int:
    """Get the number of account files loaded."""
    if f"files_loaded_{account_id}" not in st.session_state:
        st.session_state[f"files_loaded_{account_id}"] = 0
    return st.session_state[f"files_loaded_{account_id}"]


def set_account_files_loaded(account_id: int, count: int) -> None:
    """Set the number of account files loaded."""
    st.session_state[f"files_loaded_{account_id}"] = count


def get_account_total_files(account_id: int) -> int:
    """Get the total number of account files."""
    if f"total_files_{account_id}" not in st.session_state:
        st.session_state[f"total_files_{account_id}"] = 0
    return st.session_state[f"total_files_{account_id}"]


def set_account_total_files(account_id: int, count: int) -> None:
    """Set the total number of account files."""
    st.session_state[f"total_files_{account_id}"] = count

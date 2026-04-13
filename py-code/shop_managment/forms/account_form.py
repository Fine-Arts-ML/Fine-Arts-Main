"""
Account form components for the Shop Management app.
"""

import streamlit as st
from db_handler import add_account, update_entity, remove_entity


def render_add_account_form() -> None:
    """Render add account form."""
    acc_col1, acc_col2 = st.columns([2, 1])
    with acc_col1:
        new_account_name = st.text_input("Enter new account name:", key="add_account_input")
    with acc_col2:
        st.space(size='small')
        if st.button("Add Account", key="add_account_button"):
            if new_account_name.strip():
                try:
                    new_id = add_account(new_account_name.strip())
                    st.success(f"Account '{new_account_name}' added with ID: {new_id}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding account: {e}")
            else:
                st.warning("Please enter an account name.")


def render_edit_account_form(account_id: int, current_name: str) -> None:
    """
    Render edit account form.
    
    Parameters:
        account_id: ID of the account to edit
        current_name: Current account name
    """
    new_name = st.text_input(
        f"Edit account name for ID {account_id}",
        value=current_name,
        key=f"edit_acc_input_{account_id}"
    )
    save_col, cancel_col = st.columns([1, 1])
    with save_col:
        if st.button("💾 Save", key=f"save_acc_btn_{account_id}"):
            try:
                if update_entity('bre_shop_account', 'account_id', 'account_name',
                                 account_id, new_name):
                    st.success(f"Account name updated to '{new_name}'")
                    st.session_state[f"editing_acc_{account_id}"] = False
                    st.rerun()
                else:
                    st.error("Account not found")
            except Exception as e:
                st.error(f"Error updating account: {e}")
    with cancel_col:
        if st.button("❌ Cancel", key=f"cancel_acc_btn_{account_id}"):
            st.session_state[f"editing_acc_{account_id}"] = False
            st.rerun()


def render_remove_account_form(account_id: int, account_name: str) -> None:
    """
    Render remove account button.
    
    Parameters:
        account_id: ID of the account to remove
        account_name: Name of the account
    """
    if st.button("🗑️", key=f"remove_acc_btn_{account_id}"):
        try:
            if remove_entity('bre_shop_account', 'account_id', account_id):
                st.success(f"Account '{account_name}' removed")
                st.rerun()
            else:
                st.error("Account not found")
        except Exception as e:
            st.error(f"Error removing account: {e}")

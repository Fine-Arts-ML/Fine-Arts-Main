"""
Account table components for the Shop Management app.
"""

import streamlit as st
import pandas as pd
from db_handler import (
    get_accounts_for_shop, get_all_accounts, link_account_to_shop,
    remove_account_from_shop, remove_entity, update_entity
)
from forms.account_form import render_add_account_form, render_edit_account_form, render_remove_account_form
from utils.helpers import render_info_table


def render_accounts_table(accounts_df: pd.DataFrame) -> None:
    """
    Render an interactive table for managing all accounts with add/edit/remove functionality.
    
    Parameters:
        accounts_df: DataFrame with account_id and account_name columns
    """
    try:
        # Display accounts table
        if not accounts_df.empty:
            # Add new account section
            render_add_account_form()
            
            # Handle actions
            head_col1, head_col2, head_col3 = st.columns([1, 1, 1])
            with head_col1:
                st.markdown(f"**<div style='text-align: left;'>Account Name</div>**", unsafe_allow_html=True)
            with head_col2:
                st.markdown(f"**<div style='text-align: left;'>Account ID</div>**", unsafe_allow_html=True)
            with head_col3:
                st.markdown(f"**<div style='text-align: right;'>Actions</div>**", unsafe_allow_html=True)
            
            for _, row in accounts_df.iterrows():
                col1, col2, col3 = st.columns([1, 1, 1])
                with col1:
                    st.markdown(f"**<div style='text-align: left;'>{row['account_name']}</div>**", unsafe_allow_html=True)
                with col2:
                    st.markdown(f"**<div style='text-align: left;'>ID: {row['account_id']}</div>**", unsafe_allow_html=True)
                with col3:
                    subcol1, subcol2 = st.columns([1, 1])
                    with subcol1:
                        if st.button("✏️", key=f"edit_acc_global_{row['account_id']}"):
                            st.session_state[f"editing_acc_global_{row['account_id']}"] = True
                    with subcol2:
                        if st.button("🗑️", key=f"remove_acc_global_{row['account_id']}"):
                            try:
                                if remove_entity('bre_shop_account', 'account_id', row['account_id']):
                                    st.success(f"Account '{row['account_name']}' removed")
                                    st.rerun()
                                else:
                                    st.error("Account not found")
                            except Exception as e:
                                st.error(f"Error removing account: {e}")
                
                # Edit mode for this account
                if st.session_state.get(f"editing_acc_global_{row['account_id']}"):
                    new_name = st.text_input(
                        f"Edit account name for ID {row['account_id']}",
                        value=row['account_name'],
                        key=f"edit_acc_global_input_{row['account_id']}"
                    )
                    save_col, cancel_col = st.columns([1, 1])
                    with save_col:
                        if st.button("💾 Save", key=f"save_acc_global_btn_{row['account_id']}"):
                            try:
                                if update_entity('bre_shop_account', 'account_id', 'account_name',
                                       row['account_id'], new_name):
                                    st.success(f"Account name updated to '{new_name}'")
                                    st.session_state[f"editing_acc_global_{row['account_id']}"] = False
                                    st.rerun()
                                else:
                                    st.error("Account not found")
                            except Exception as e:
                                st.error(f"Error updating account: {e}")
                    with cancel_col:
                        if st.button("❌ Cancel", key=f"cancel_acc_global_btn_{row['account_id']}"):
                            st.session_state[f"editing_acc_global_{row['account_id']}"] = False
                            st.rerun()
        else:
            st.info("No accounts found. Add a new account above.")
            
    except Exception as e:
        st.error(f"Error loading accounts: {e}")


def render_account_table(shop_id: int, shops_df: pd.DataFrame) -> None:
    """
    Render an interactive table for managing accounts linked to a shop.
    
    Parameters:
        shop_id: ID of the shop
        shops_df: DataFrame with shop_id and shop_name columns
    """
    try:
        # Get accounts linked to this shop
        linked_df = get_accounts_for_shop(shop_id)
        
        # Fetch all shops for the dropdown
        all_shops = get_all_shops()
        
        with st.container(border=True):
            # Link account to shop section with account dropdown only
            with st.container():
                st.markdown("---")
                st.subheader("🔗 Link Account to Shop")
                
                # Get all accounts for dropdown, filter out already linked accounts
                all_accounts = get_all_accounts()
                linked_ids = set(linked_df['account_id'].tolist()) if not linked_df.empty else set()
                available_accounts = all_accounts[~all_accounts['account_id'].isin(linked_ids)]
                
                if not available_accounts.empty:
                    acc_col1, acc_col2 = st.columns([2, 1])
                    with acc_col1:
                        account_options = {
                            f"{row['account_name']} (ID: {row['account_id']})": row['account_id']
                            for _, row in available_accounts.iterrows()
                        }
                        selected_account = st.selectbox(
                            "Select Account:",
                            options=list(account_options.keys()),
                            format_func=lambda x: x,
                            key=f"link_account_to_shop_{shop_id}"
                        )
                    with acc_col2:
                        st.space('small')
                        if st.button("Link Account to Shop", key=f"link_account_to_shop_btn_{shop_id}"):
                            if selected_account:
                                try:
                                    if link_account_to_shop(shop_id, account_options[selected_account]):
                                        st.success(f"Account linked to shop")
                                        st.rerun()
                                    else:
                                        st.warning("Account already linked to shop")
                                except Exception as e:
                                    st.error(f"Error linking account: {e}")
                else:
                    # Show info message and hide button when all accounts are linked
                    st.info("All accounts are already linked to this shop.")
            
            # Display accounts table
            if not linked_df.empty:
                # Handle remove actions
                head_col1, head_col2, head_col3 = st.columns([1, 1, 1])
                with head_col1:
                    st.markdown(f"**<div style='text-align: left;'>Account Name</div>**", unsafe_allow_html=True)
                with head_col2:
                    st.markdown(f"**<div style='text-align: left;'>Account ID</div>**", unsafe_allow_html=True)
                with head_col3:
                    st.markdown(f"**<div style='text-align: right;'>Remove Link</div>**", unsafe_allow_html=True)
                
                for _, row in linked_df.iterrows():
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        st.markdown(f"**<div style='text-align: left;'>{row['account_name']}</div>**", unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"**<div style='text-align: left;'>ID: {row['account_id']}</div>**", unsafe_allow_html=True)
                    with col3:
                        subcol1, subcol2 = st.columns([3, 1])
                        with subcol1:
                            st.space('small')
                        with subcol2:
                            if st.button("🗑️", key=f"remove_acc_btn_{shop_id}_{row['account_id']}"):
                                try:
                                    if remove_account_from_shop(shop_id, row['account_id']):
                                        st.success(f"Account '{row['account_name']}' removed from shop")
                                        st.rerun()
                                    else:
                                        st.error("Account not found")
                                except Exception as e:
                                    st.error(f"Error removing account: {e}")
                            
                            # Edit mode for this account
                            if st.session_state.get(f"editing_acc_{row['account_id']}"):
                                new_name = st.text_input(
                                    f"Edit account name for ID {row['account_id']}",
                                    value=row['account_name'],
                                    key=f"edit_acc_input_{row['account_id']}"
                                )
                                save_col, cancel_col = st.columns([1, 1])
                                with save_col:
                                    if st.button("💾 Save", key=f"save_acc_btn_{row['account_id']}"):
                                        try:
                                            if update_entity('bre_shop_account', 'account_id', 'account_name',
                                                   row['account_id'], new_name):
                                                st.success(f"Account name updated to '{new_name}'")
                                                st.session_state[f"editing_acc_{row['account_id']}"] = False
                                                st.rerun()
                                            else:
                                                st.error("Account not found")
                                        except Exception as e:
                                            st.error(f"Error updating account: {e}")
                                with cancel_col:
                                    if st.button("❌ Cancel", key=f"cancel_acc_btn_{row['account_id']}"):
                                        st.session_state[f"editing_acc_{row['account_id']}"] = False
                                        st.rerun()
            else:
                # Show message when no accounts linked
                st.info("No accounts linked to this shop yet. Use the dropdown above to link an account.")
            
    except Exception as e:
        st.error(f"Error loading accounts: {e}")

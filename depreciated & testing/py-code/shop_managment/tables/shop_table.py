"""
Shop table components for the Shop Management app.
"""

import streamlit as st
import pandas as pd
from db_handler import get_accounts_for_shop, get_file_count_for_shop, remove_shop, update_shop
from forms.shop_form import render_add_shop_form, render_edit_shop_form, render_remove_shop_form
from utils.helpers import render_info_table


def render_shops_table(shops_df: pd.DataFrame) -> None:
    """
    Render an interactive table for managing shops with add/remove functionality.
    
    Parameters:
        shops_df: DataFrame with shop_id and shop_name columns
    """
    
    # Display shops table
    if not shops_df.empty:
        # Add new shop section
        render_add_shop_form()
        
        # Handle remove actions
        head_col1, head_spacer = st.columns([1, 5])
        with head_col1:
            st.markdown(f"**<div style='text-align: left;'>Shop-Website</div>**", unsafe_allow_html=True)

        for _, row in shops_df.iterrows():
            # Wrap shop row and accounts in a bordered container when accounts are shown
            with st.container(border=st.session_state.get(f"showing_accounts_{row['shop_id']}", False)):
                
                with st.expander(row['shop_name']):
                    sub_head1, sub_head2, sub_head3 = st.columns([1, 1, 1])
    
                    with sub_head1:
                        st.markdown(f"**<div style='text-align: left;'>__Shop Details__</div>**", unsafe_allow_html=True)

                        # Get account count for this shop
                        try:
                            accounts_df = get_accounts_for_shop(row['shop_id'])
                            account_count = len(accounts_df)
                            file_count = get_file_count_for_shop(row['shop_id'])
                        except Exception as e:
                            account_count = 0
                            file_count = 0
                        
                        # Create info table
                        df_info_table = pd.DataFrame({
                            'Metric': ['Shop ID', 'Accounts', 'Files'],
                            'Value': [row['shop_id'], account_count, file_count]
                        })
                        render_info_table({
                            'Shop ID': row['shop_id'],
                            'Accounts': account_count,
                            'Files': file_count
                        })
                    with sub_head2:
                        st.markdown(f"**<div style='text-align: left;'>Accounts</div>**", unsafe_allow_html=True)
                        if account_count > 0:
                            accounts_display = accounts_df[['account_name', 'account_id']].rename(columns={'account_name': 'Name', 'account_id': 'ID'})
                            st.dataframe(accounts_display, hide_index=True, use_container_width=True)
                        else:
                            st.markdown("*No accounts*")

                    with sub_head3:
                        col1, col2, col3 = st.columns([1, 1, 1])
                        with col3:
                            st.markdown(f"**<div style='text-align: right;'>Actions</div>**", unsafe_allow_html=True)
                            with st.container(horizontal_alignment="right", horizontal=True):
                                if st.session_state.get(f"showing_accounts_{row['shop_id']}", False):
                                    if st.button("❌", key=f"close_accounts_{row['shop_id']}"):
                                        st.session_state[f"showing_accounts_{row['shop_id']}"] = False
                                        st.rerun()
                                else:
                                    if st.button("👤", key=f"account_btn_{row['shop_id']}"):
                                        st.session_state[f"showing_accounts_{row['shop_id']}"] = True
                                        st.rerun()
                                if st.button("✏️", key=f"edit_btn_{row['shop_id']}"):
                                    st.session_state[f"editing_{row['shop_id']}"] = True
                                if st.button("🗑️", key=f"remove_btn_{row['shop_id']}"):
                                    render_remove_shop_form(row['shop_id'], row['shop_name'])
                        
                        # Edit mode for this shop
                        if st.session_state.get(f"editing_{row['shop_id']}"):
                            render_edit_shop_form(row['shop_id'], row['shop_name'])
                    
                    # Account management for this shop - in same row, indented
                    if st.session_state.get(f"showing_accounts_{row['shop_id']}"):
                        st.markdown("")  # Empty spacer for indentation
                        from tables.account_table import render_account_table
                        render_account_table(row['shop_id'], shops_df)

    else:
        st.info("No shops found. Add a new shop above.")

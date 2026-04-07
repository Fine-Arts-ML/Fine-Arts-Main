"""
Streamlit App for Shop Management

This app allows users to manage shops and their linked files from the database.
"""

import streamlit as st
import pandas as pd

from db_handler import get_all_shops, get_file_count_for_shop, get_all_accounts, get_files_for_shop_account, get_files_for_shop_account_paginated
from ui_components import (
    render_shops_table,
    render_files_table,
    render_infinite_scroll_file_list,
    render_shop_selector,
    render_account_table,
    render_accounts_table
)


def main():
    """Main Streamlit application function."""
    st.set_page_config(
        layout="wide"
    )
    
    st.markdown("Manage shops and their linked files.")
    
    # Fetch all shops
    try:
        shops_df = get_all_shops()
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return
    
    # Fetch all accounts for Account Management tab
    try:
        accounts_df = get_all_accounts()
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return
    
    # Create main tabs
    Shop_Accounts_tab, Files_tab, Owl_tab = st.tabs(["Shops & Accounts", "Files", "Owl"])
    
    # Sidebar for shop selection
    with st.sidebar:
        st.header("Navigation")
    
    # Shop Management Tab
    with Shop_Accounts_tab:
        # Main content area - render shops table
        shop_mngt, acc_mngt,perf = st.tabs(['Shop Managment','Account Managment','Performance'])
        with shop_mngt:
            render_shops_table(shops_df)
        with acc_mngt:
           render_accounts_table(accounts_df)
        with perf:
            st.markdown('TBD')
    
    # Files Tab
    with Files_tab:
        # Shop selector - returns list of (shop_name, shop_id) tuples and tabs object
        shop_list, tabs = render_shop_selector(shops_df)
        if shop_list:
            print('a')
        else:
            # No shops available
            st.info("No shops available. Add a shop first in the 'Shops & Accounts' tab.")


if __name__ == "__main__":
    main()

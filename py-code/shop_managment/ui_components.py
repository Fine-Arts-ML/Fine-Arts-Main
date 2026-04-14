"""
UI Components for the Shop Management app.
Provides reusable components for the Streamlit interface.
"""

import streamlit as st
import pandas as pd
from db_handler import (
    get_all_shops, get_accounts_for_shop, link_file_to_shop, link_account_to_shop,
    get_files_for_shop, get_all_file_ids_with_info, get_files_for_shop_account,
    unlink_file_from_account, get_preview_image, get_file_count_for_shop,
    get_accounts_for_file
)
from forms.file_form import render_add_file_form, show_file_selection_modal
from tables.file_table import render_file_row
from utils.constants import HASH_TYPES


def render_files_view(shop_id: int, tab_context: str = None, show_files: bool = True) -> None:
    """
    Render the files view for a shop.
    
    Parameters:
        shop_id: ID of the shop
        tab_context: Optional unique context identifier for the tab (e.g., tab index)
        show_files: Whether to show the file listing (default True). Set to False for "Add files" tab.
    """
    from tables import render_files_table, render_infinite_scroll_file_list

    # Display files container (only search form, no file listing)
    if show_files:
        # Get file count
        try:
            file_count = get_file_count_for_shop(shop_id)
        except Exception:
            file_count = 0
        
        st.subheader(f"📁 Files for Shop ID: {shop_id}")
        st.markdown(f"**Total files linked:** {file_count}")
        
        with st.container(border=True):
            # Header row
            head_col1, head_col2, head_col3 = st.columns([3, 5, 1])
            with head_col1:
                st.markdown(f"**<div style='text-align: left;'>Preview</div>**", unsafe_allow_html=True)
            with head_col2:
                st.markdown(f"**<div style='text-align: left;'>Filename</div>**", unsafe_allow_html=True)
            with head_col3:
                st.markdown(f"**<div style='text-align: right;'>Actions</div>**", unsafe_allow_html=True)
            
            # Get files for this shop
            try:
                files_df = get_files_for_shop(shop_id)
                
                if not files_df.empty:
                    for _, row in files_df.iterrows():
                        file_data = {
                            'file_id': row['file_id'],
                            'filename': row['filename'],
                            'preview_url': row.get('preview_url', '')
                        }
                        render_file_row(file_data, shop_id, is_infinite_scroll=False)
                else:
                    st.info(f"No files linked to this shop yet.")
            except Exception as e:
                st.error(f"Error loading files: {e}")


def render_overview_tab(shop_id: int, account_tabs, tab_index: int, shops_df: pd.DataFrame) -> None:
    """
    Render the Overview tab for a shop.
    
    Parameters:
        shop_id: ID of the shop
        account_tabs: The Streamlit tabs object for account tabs
        tab_index: The index of this tab in the account_tabs list
        shops_df: DataFrame with shop_id and shop_name columns
    """
    with account_tabs[tab_index]:
        st.markdown("## Overview - All Files for Selected Shop")
        
        # Get all files for the selected shop (shop_id is already known from the shop tab)
        try:
            files_df = get_files_for_shop(shop_id)
            
            if not files_df.empty:
                st.markdown(f"**Total files:** {len(files_df)}")
                
                # Display files in a dataframe table
                display_df = files_df[['file_id', 'filename', 'account_name', 'preview_url']].copy()
                st.dataframe(display_df, use_container_width=True)
                
                # Add remove functionality
                st.markdown("### Remove Files")
                
                # Create a selectbox to choose which file to remove
                file_options = {f"{row['filename']} (ID: {row['file_id']})": row['file_id']
                                for _, row in files_df.iterrows()}
                
                selected_file_key = st.selectbox("Select file to remove", list(file_options.keys()), key=f"remove_{shop_id}")
                
                if selected_file_key:
                    file_id = file_options[selected_file_key]
                    
                    # Get account info for this file
                    file_info = files_df[files_df['file_id'] == file_id].iloc[0]
                    account_name = file_info['account_name']
                    
                    # Get all accounts linked to this file
                    try:
                        accounts_df = get_accounts_for_file(file_id)
                        other_accounts = accounts_df[accounts_df['account_id'] != file_info['account_id']]
                    except Exception:
                        other_accounts = pd.DataFrame(columns=['account_id', 'account_name'])
                    
                    # Check if file is linked to this shop
                    from db_handler import get_shop_for_file
                    is_linked_to_shop = get_shop_for_file(file_id, shop_id)
                    
                    # Get shop name for display
                    shop_name = ""
                    if not shops_df.empty:
                        shop_row = shops_df[shops_df['shop_id'] == shop_id]
                        if not shop_row.empty:
                            shop_name = shop_row['shop_name'].values[0]
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.info(f"Removing file '{selected_file_key}' from account '{account_name}'")
                        if is_linked_to_shop and shop_name:
                            delete_shop_link = st.checkbox(
                                f"Also remove shop link (delete from {shop_name})",
                                key=f"delete_shop_{file_id}_{shop_id}"
                            )
                    with col2:
                        if st.button("Remove", key=f"remove_{file_id}_{shop_id}"):
                            try:
                                # Unlink file from account
                                success = unlink_file_from_account(file_id, account_id=file_id)
                                if success:
                                    # Check if file is still linked to other accounts
                                    if not other_accounts.empty:
                                        st.success(f"File '{selected_file_key}' removed from account '{account_name}'")
                                        st.info(f"File is still linked to {len(other_accounts)} other account(s)")
                                    else:
                                        st.success(f"File '{selected_file_key}' removed from account '{account_name}'")
                                    
                                    # Remove shop link if checkbox was checked
                                    if is_linked_to_shop and delete_shop_link:
                                        from db_handler import unlink_file_from_shop
                                        shop_link_removed = unlink_file_from_shop(file_id, shop_id)
                                        if shop_link_removed:
                                            st.success(f"File '{selected_file_key}' also removed from shop link")
                                    
                                    # Refresh the dataframe
                                    files_df = get_files_for_shop(shop_id)
                                    st.rerun()
                                else:
                                    st.error("Failed to remove file")
                            except Exception as e:
                                st.error(f"Error removing file: {e}")
            else:
                st.markdown("No files found for this shop.")
        except Exception as e:
            st.error(f"Error loading files: {e}")


def render_file_row(file_data: dict, shop_id: int, is_infinite_scroll: bool = False, files_list: list = None) -> None:
    """
    Render a single file row with preview, filename, and delete button.
    
    Parameters:
        file_data: File data containing file_id, filename, and preview_url
        shop_id: ID of the shop
        is_infinite_scroll: If True, use infinite scroll delete logic
        files_list: Current files list for infinite scroll mode (for removal)
    """
    from db_handler import unlink_file_from_shop
    
    col1, col2, col3 = st.columns([3, 5, 1])
    
    with col1:
        # Try to display preview
        preview_url = file_data.get('preview_url', '')
        if preview_url:
            full_preview_url = f"http://{{DB_HOST}}:8080{preview_url.replace('{prevsize}', 'x=100&y=100')}"
            st.image(full_preview_url, width='stretch')
        else:
            st.write("📄")
    
    with col2:
        st.markdown(f"**{file_data['filename']}**")
    
    with col3:
        key_suffix = "inf_" if is_infinite_scroll else "_"
        if st.button("🗑️", key=f"remove_file{key_suffix}{file_data['file_id']}_{shop_id}"):
            try:
                if unlink_file_from_shop(file_data['file_id'], shop_id):
                    if is_infinite_scroll and files_list is not None:
                        # Remove from session state
                        st.session_state[f"files_{shop_id}"] = [
                            f for f in files_list if f['file_id'] != file_data['file_id']
                        ]
                        st.session_state[f"loaded_{shop_id}"] -= 1
                    st.success("File removed")
                    st.rerun()
                else:
                    st.error("Failed to remove file")
            except Exception as e:
                st.error(f"Error: {e}")


def render_add_files_tab(shop_id: int, account_tabs, tab_index: int = 1) -> None:
    """
    Render the Add Files tab for a shop.
    
    Parameters:
        shop_id: ID of the shop
        account_tabs: The Streamlit tabs object for account tabs
        tab_index: The index of this tab in the account_tabs list (default: 1)
    """
    with account_tabs[tab_index]:
        st.markdown('**Add Files to Shop**')
        with st.container():
            render_add_file_form(shop_id)


def render_account_tab(shop_id: int, account_id: int, account_name: str, account_tabs, tab_index: int) -> None:
    """
    Render an account tab for a shop with table and grid views.
    
    Parameters:
        shop_id: ID of the shop
        account_id: ID of the account
        account_name: Name of the account
        account_tabs: The Streamlit tabs object for account tabs
        tab_index: The index of this account tab in the account_tabs list
    """
    with account_tabs[tab_index]:
        # Create sub-tabs for view options
        table_view, grid_view = st.tabs(["📋 Table View", "🖼️ Grid View"])
        
        with table_view:
            render_account_files_table(shop_id, account_id, account_name)
        
        with grid_view:
            # Display all files without pagination (no session state)
            files_per_row = 2
            files_df = get_files_for_shop_account(shop_id, account_id)
            
            # Display image previews - 2 files per row
            if not files_df.empty:
                for file_idx in range(0, len(files_df), files_per_row):
                    chunk = files_df.iloc[file_idx:file_idx + files_per_row]
                    
                    # Create columns for this row
                    cols = st.columns(files_per_row)
                    
                    # Track actual column index within this chunk
                    local_col_idx = 0
                    for col_idx, row in chunk.iterrows():
                        with cols[local_col_idx]:
                            local_col_idx += 1
                            if local_col_idx >= files_per_row:
                                break
                            with st.container(border=True):
                                st.markdown(f"**{row['filename']}**")
                                st.caption(account_name)
                                if row['preview_url'] and pd.notna(row['preview_url']):
                                    img = get_preview_image(
                                        file_id=row['file_id'],
                                        preview_url=row['preview_url']
                                    )
                                    if img is not None:
                                        st.image(img, width=1080)  # Grid view: 1080x1080
                                    else:
                                        st.write("Image not available")
                                else:
                                    st.write("No preview available")
            else:
                st.info("No files linked to this account yet.")
            
            st.caption(f"Total: {len(files_df)} files")


def render_account_files_table(shop_id: int, account_id: int, account_name: str) -> None:
    """
    Render a table view of files linked to an account for a specific shop.
    
    Parameters:
        shop_id: ID of the shop
        account_id: ID of the account
        account_name: Name of the account
    """
    st.subheader(f"📋 Files for Account '{account_name}'")
    
    # Search input for file names
    search_query = st.text_input("🔍 Search files by name:", key=f"search_{account_id}_{shop_id}")
    
    # Get files for this shop-account combination
    files_df = get_files_for_shop_account(shop_id, account_id)
    
    # Filter files by search query
    if search_query:
        filtered_df = files_df[files_df['filename'].str.lower().str.contains(search_query.lower(), na=False)]
    else:
        filtered_df = files_df
    
    if not filtered_df.empty:
        st.markdown(f"**Total files linked:** {len(files_df)} | **Showing:** {len(filtered_df)}")
        
        # Display table with columns: Preview, Filename, File ID, Actions
        for _, row in filtered_df.iterrows():
            render_account_file_row(row, shop_id, account_id)
        
    else:
        st.info(f"No files linked to account '{account_name}' for this shop." if not search_query else f"No files matching '{search_query}' found.")


def render_account_file_row(file_data: dict, shop_id: int, account_id: int) -> None:
    """
    Render a single file row in the account table.
    
    Parameters:
        file_data: File data containing file_id, filename, preview_url
        shop_id: ID of the shop
        account_id: ID of the account
    """
    col1, col2, col3, col4 = st.columns([3, 5, 2, 1])
    
    with col1:
        # Preview image
        if file_data.get('preview_url') and pd.notna(file_data.get('preview_url')):
            img = get_preview_image(
                file_id=file_data['file_id'],
                preview_url=file_data['preview_url']
            )
            if img is not None:
                st.image(img, width=540)  # Table view: 540x540
            else:
                st.write("📄")
        else:
            st.write("📄")
    
    with col2:
        st.markdown(f"**{file_data['filename']}**")
    
    with col3:
        st.write(f"ID: {file_data['file_id']}")
    
    with col4:
        # Remove from account button (include shop_id for uniqueness across shops)
        if st.button("🗑️", key=f"remove_from_acc_{shop_id}_{file_data['file_id']}_{account_id}"):
            try:
                if unlink_file_from_account(file_data['file_id'], account_id):
                    st.success(f"File removed from account")
                    st.rerun()
                else:
                    st.error("Failed to remove file from account")
            except Exception as e:
                st.error(f"Error: {e}")


def render_shop_selector(shops_df: pd.DataFrame):
    """
    Render tabs to choose a shop with nested account tabs.
    
    Parameters:
        shops_df: DataFrame with shop_id and shop_name columns
        
    Returns:
        tuple: (shop_list, tabs) - List of (shop_name, shop_id) tuples and tabs object
    """
    # Create tabs for each shop
    shop_tabs = st.tabs([f"🏪 {row['shop_name']}" for _, row in shops_df.iterrows()])
    
    shop_list = []
    account_tabs_list = []
    
    for idx, (_, row) in enumerate(shops_df.iterrows()):
        shop_id = row['shop_id']
        shop_name = row['shop_name']
        shop_list.append((shop_name, shop_id))
        
        with shop_tabs[idx]:
            # Get accounts for this shop
            accounts_df = get_accounts_for_shop(shop_id)
            
            # Create account tabs with Overview as first tab
            if not accounts_df.empty:
                account_tab_names = [f"👤 {row['account_name']}" for _, row in accounts_df.iterrows()]
                account_tab_names.insert(0, "📁 Add Files")
                account_tab_names.insert(0, "📊 Overview")
                account_tabs = st.tabs(account_tab_names)
            else:
                account_tabs = st.tabs(["📊 Overview", "📁 Add Files"])
            
            account_tabs_list.append(account_tabs)
            
            # Render Overview tab
            render_overview_tab(shop_id, account_tabs, tab_index=0, shops_df=shops_df)
            
            # Render Add Files tab
            render_add_files_tab(shop_id, account_tabs, tab_index=1)
            
            # Render account tabs (shifted by 2 indices)
            for acc_idx, (_, acc_row) in enumerate(accounts_df.iterrows()):
                acc_id = acc_row['account_id']
                acc_name = acc_row['account_name']
                render_account_tab(shop_id, acc_id, acc_name, account_tabs, tab_index=acc_idx + 2)
    
    return shop_list, account_tabs_list

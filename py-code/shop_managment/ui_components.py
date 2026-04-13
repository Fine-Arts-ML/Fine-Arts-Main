"""
UI Components for the Shop Management app.
Provides reusable components for the Streamlit interface.
"""

import streamlit as st
import pandas as pd
from db_handler import (
    get_all_shops, get_accounts_for_shop, link_file_to_shop, link_account_to_shop,
    get_files_for_shop, get_all_file_ids_with_info, get_files_for_shop_account_paginated,
    unlink_file_from_account, get_preview_image
)
from forms.file_form import render_add_file_form, show_file_selection_modal
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
                files_df, _ = get_files_for_shop(shop_id, page_size=10000, offset=0)
                
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


def get_file_count_for_shop(shop_id: int) -> int:
    """
    Get the total number of files linked to a specific shop.
    
    Parameters:
        shop_id: ID of the shop
        
    Returns:
        int: Number of files linked to the shop
    """
    from db_handler import create_db_connection
    from sqlalchemy import create_engine, MetaData, Table, select, func
    
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the table
    bre_shops_index = Table('bre_shops_index', metadata, autoload_with=engine)
    
    # Count files for shop
    query = select(func.count()).select_from(
        select(bre_shops_index.c.id).where(bre_shops_index.c.shop_id == shop_id).subquery()
    )
    
    with engine.begin() as connection:
        result = connection.execute(query).fetchone()
        return result[0] if result else 0


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
        # VISUAL DEBUG MARKER: Add a visible marker at the start
        st.markdown(
            f"**[UI COMPONENTS DEBUG] START of render_add_files_tab for shop_id={shop_id}**",
            unsafe_allow_html=True
        )
        st.markdown('**Add Files to Shop**')
        with st.container():
            render_add_file_form(shop_id)
        
        # VISUAL DEBUG MARKER: Add a visible marker at the end
        st.markdown(
            f"**[UI COMPONENTS DEBUG] END of render_add_files_tab for shop_id={shop_id}**",
            unsafe_allow_html=True
        )


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
            files_df, total_count = get_files_for_shop_account_paginated(
                shop_id, account_id, page_size=1000, offset=0
            )
            
            # Display image previews - 2 files per row
            if not files_df.empty:
                for file_idx in range(0, len(files_df), files_per_row):
                    chunk = files_df.iloc[file_idx:file_idx + files_per_row]
                    
                    # Create columns for this row
                    cols = st.columns(files_per_row)
                    
                    for col_idx, row in chunk.iterrows():
                        with cols[col_idx]:
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
            
            st.caption(f"Total: {total_count} files")


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
    files_df, total_count = get_files_for_shop_account_paginated(
        shop_id, account_id, page_size=1000, offset=0
    )
    
    # Filter files by search query
    if search_query:
        filtered_df = files_df[files_df['filename'].str.lower().str.contains(search_query.lower(), na=False)]
    else:
        filtered_df = files_df
    
    if not filtered_df.empty:
        st.markdown(f"**Total files linked:** {total_count} | **Showing:** {len(filtered_df)}")
        
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


def render_shop_selector(shops_df: pd.DataFrame) -> tuple:
    """
    Render tabs to choose a shop with nested account tabs for each shop.
    
    Parameters:
        shops_df: DataFrame with shop_id and shop_name columns
        
    Returns:
        tuple: (shop_list, shop_tabs) where shop_list is a list of (shop_name, shop_id) tuples
               and shop_tabs is the Streamlit tabs object for shops
    """
    if shops_df.empty:
        st.warning("No shops available. Add a shop first.")
        return [], None
    
    # Create list of (shop_name, shop_id) tuples
    shop_list = [
        (row['shop_name'], row['shop_id'])
        for _, row in shops_df.iterrows()
    ]
    
    # Create tabs for each shop dynamically
    tab_labels = [shop_name for shop_name, _ in shop_list]
    shop_tabs = st.tabs(tab_labels)
    
    if shop_list:
        # Iterate through each shop tab
        for idx, (shop_name, shop_id) in enumerate(shop_list):
            with shop_tabs[idx]:
                # Get accounts for this shop
                accounts_df = get_accounts_for_shop(shop_id)
                
                # Display accounts table
                if not accounts_df.empty:
                    
                    # Create sub-tabs for each account + "All files" tab + "Add Files" tab
                    account_tab_names = accounts_df['account_name'].to_list()
                    all_account_tab_names = ['All files', 'Add Files'] + account_tab_names
                    account_tabs = st.tabs(all_account_tab_names)
                    
                    # First tab: All files for this shop
                    with account_tabs[0]:
                        st.markdown(f'**All Files from {shop_name}**')
                        files_df, _ = get_files_for_shop(shop_id, page_size=10000, offset=0)
                        if not files_df.empty:
                            # Get account names for display
                            account_ids = files_df['account_id'].dropna().unique().tolist()
                            account_names_df = get_accounts_for_shop(shop_id)
                            account_id_to_name = dict(zip(account_names_df['account_id'], account_names_df['account_name']))
                            
                            # Add account name column
                            files_df_display = files_df.copy()
                            files_df_display['account_name'] = files_df_display['account_id'].map(
                                lambda x: account_id_to_name.get(x, 'N/A') if pd.notna(x) else 'N/A'
                            )
                            
                            # Display table with file_id, filename, and account_name
                            st.table(files_df_display[['file_id', 'filename', 'account_name']])
                        else:
                            st.info("No files linked to this shop yet.")
                    
                    # Second tab: Add Files for this shop
                    with account_tabs[1]:
                        st.markdown(f'**Add Files to {shop_name}**')
                        render_add_file_form(shop_id)
                    
                    # Create sub-tabs for each account linked to the shop
                    # Always render account tabs - Streamlit handles visibility
                    # Note: account_tabs[0] = 'All files', account_tabs[1] = 'Add Files'
                    # So accounts start at index 2
                    for acc_idx, account_name in enumerate(account_tab_names):
                        account_id = accounts_df.iloc[acc_idx]['account_id']
                        render_account_tab(shop_id, account_id, account_name, account_tabs, tab_index=acc_idx + 2)
                else:
                    st.info("No accounts linked to this shop yet.")
    
    return shop_list, shop_tabs


# Note: show_file_selection_modal is now imported from forms.file_form

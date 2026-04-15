"""
UI Components for the Shop Management app.
Provides reusable components for the Streamlit interface.
"""

import base64
import io
import os
import streamlit as st
import pandas as pd
from db_handler import (
    get_all_shops, get_accounts_for_shop, link_file_to_shop, link_account_to_shop,
    get_files_for_shop, get_all_file_ids_with_info, get_files_for_shop_account,
    unlink_file_from_account, get_preview_image, get_file_count_for_shop,
    get_accounts_for_file, get_display_name_for_file
)
from forms.file_form import render_add_file_form
# from tables.file_table import render_file_row  # Removed - using inline render_account_file_row
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
    # Get shop name for display
    shop_name = ""
    if not shops_df.empty:
        shop_row = shops_df[shops_df['shop_id'] == shop_id]
        if not shop_row.empty:
            shop_name = shop_row['shop_name'].values[0]
    
    with account_tabs[tab_index]:
        st.markdown(f'''## Table View for all Files linked to {shop_name}''')
        
        # Get all files for the selected shop (shop_id is already known from the shop tab)
        try:
            files_df = get_files_for_shop(shop_id)
            
            if not files_df.empty:
                st.markdown(f"**Total files:** {len(files_df)}")
                
                # Display files in a dataframe table
                # Reorder columns: preview_url (leftmost), filename, display_name, account_name, file_id
                display_df = files_df[['preview_url', 'filename', 'display_name', 'account_name', 'file_id']].copy()
                
                # Convert preview URLs to base64-encoded images for display
                def url_to_base64(preview_url):
                    """Convert preview URL to base64 data URI for display in dataframe."""
                    if not preview_url:
                        return ""
                    
                    db_host = os.getenv("DB_HOST", "192.168.0.150")
                    nc_acc = os.getenv("NC_ACC")
                    nc_pass = os.getenv("NC_PASS")
                    
                    # Construct full preview URL with authentication
                    full_url = f"http://{db_host}:8080{preview_url.replace('{prevsize}', 'x=100&y=100')}"
                    
                    try:
                        response = requests.get(full_url, auth=HTTPBasicAuth(nc_acc, nc_pass))
                        if response.status_code == 200:
                            img_bytes = io.BytesIO(response.content)
                            img_bytes.seek(0)
                            img_base64 = base64.b64encode(img_bytes.read()).decode('utf-8')
                            return f"data:image/jpeg;base64,{img_base64}"
                        else:
                            return ""
                    except Exception:
                        return ""
                
                # Import required modules
                import requests
                from requests.auth import HTTPBasicAuth
                
                # Convert URLs to base64 data URIs
                display_df['preview_url'] = display_df['preview_url'].apply(url_to_base64)
                
                # Display with ImageColumn config for preview images
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    column_config={
                        "preview_url": st.column_config.ImageColumn(
                            "Preview",
                            help="File preview",
                            width="100"
                        )
                    }
                )
                
                # Add remove functionality
                st.markdown("### Remove Files")
                
                # Create a selectbox to choose which file to remove
                file_options = {f"{row['filename']} (ID: {row['file_id']})": row['file_id']
                                for _, row in files_df.iterrows()}
                colm1 ,colm2 = st.columns([2,1])
                with colm1:
                    selected_file_key = st.selectbox("Select file to remove", list(file_options.keys()), key=f"remove_{shop_id}")
                
                    if selected_file_key:
                        file_id = file_options[selected_file_key]
                        
                        # Get all accounts linked to this file
                        try:
                            accounts_df = get_accounts_for_file(file_id)
                        except Exception:
                            accounts_df = pd.DataFrame(columns=['account_id', 'account_name'])
                        
                        # Check if file is linked to this shop
                        from db_handler import get_shop_for_file
                        is_linked_to_shop = get_shop_for_file(file_id, shop_id)
                        
                        # Display accounts linked to this file
                        if not accounts_df.empty:
                            # Create account selection options for multiselect
                            account_options = {f"{row['account_name']} (ID: {row['account_id']})": row['account_id']
                                            for _, row in accounts_df.iterrows()}
                            
                            # Use multiselect to allow multiple account selection
                            selected_account_keys = st.multiselect(
                                "Select account(s) to unlink file from:",
                                options=list(account_options.keys()),
                                key=f"remove_account_{file_id}_{shop_id}"
                            )
                            
                            selected_account_ids = [account_options[key] for key in selected_account_keys]
                            
                            # Determine if shop link should be removed
                            # If all accounts are being removed, auto-remove shop link
                            auto_remove_shop_link = (len(selected_account_ids) == len(accounts_df) and len(accounts_df) > 0)
                            

                            if is_linked_to_shop and shop_name:
                                if auto_remove_shop_link:
                                    st.caption(f"Shop link will be automatically removed (all {len(accounts_df)} account(s) selected)")
                                    delete_shop_link = True

                    with colm2:
                            st.space('small')
                            if len(selected_account_ids) > 0 and st.button("Remove", key=f"remove_{file_id}_{shop_id}"):
                                try:
                                    # Unlink file from selected account(s)
                                    for acc_id in selected_account_ids:
                                        unlink_file_from_account(file_id, acc_id)
                                    
                                    st.success(f"File '{selected_file_key}' removed from {len(selected_account_ids)} account(s)")
                                    
                                    # Remove shop link if checkbox was checked or auto-removed
                                    if is_linked_to_shop and delete_shop_link:
                                        from db_handler import unlink_file_from_shop
                                        shop_link_removed = unlink_file_from_shop(file_id, shop_id)
                                        if shop_link_removed:
                                            if auto_remove_shop_link:
                                                st.success(f"File '{selected_file_key}' also removed from shop link (auto-removed)")
                                            else:
                                                st.success(f"File '{selected_file_key}' also removed from shop link")
                                    
                                    # Refresh the dataframe
                                    files_df = get_files_for_shop(shop_id)
                                    st.rerun()
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


def render_account_tab(shop_id: int, shop_name: str, account_id: int, account_name: str, account_tabs, tab_index: int) -> None:
    """
    Render an account tab for a shop with table and grid views.
    
    Parameters:
        shop_id: ID of the shop
        shop_name: Name of the shop
        account_id: ID of the account
        account_name: Name of the account
        account_tabs: The Streamlit tabs object for account tabs
        tab_index: The index of this account tab in the account_tabs list
    """
    # Initialize pagination in session state
    if f"page_{shop_id}_{account_id}" not in st.session_state:
        st.session_state[f"page_{shop_id}_{account_id}"] = 0
    
    # Get total files
    files_df = get_files_for_shop_account(shop_id, account_id)
    total_files = len(files_df)
    files_per_page = 20
    
    # Calculate total pages
    total_pages = (total_files + files_per_page - 1) // files_per_page if total_files > 0 else 1
    
    # Ensure current page is within bounds
    if st.session_state[f"page_{shop_id}_{account_id}"] >= total_pages:
        st.session_state[f"page_{shop_id}_{account_id}"] = total_pages - 1
    
    with account_tabs[tab_index]:
        # Create sub-tabs for view options
      
        
   
        render_account_files_table(shop_id, shop_name, account_id, account_name, files_df, total_files, files_per_page)
        
      
        st.caption(f"Total: {total_files} files")
            
        # Pagination controls
        if total_pages > 1:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if st.button("◀️ Previous", key=f"prev_{shop_id}_{account_id}"):
                    st.session_state[f"page_{shop_id}_{account_id}"] = max(0, st.session_state[f"page_{shop_id}_{account_id}"] - 1)
                    st.rerun()
            with col2:
                st.caption(f"Page {st.session_state[f'page_{shop_id}_{account_id}'] + 1} of {total_pages}")
            with col3:
                if st.button("Next ▶️", key=f"next_{shop_id}_{account_id}"):
                    st.session_state[f"page_{shop_id}_{account_id}"] = min(total_pages - 1, st.session_state[f"page_{shop_id}_{account_id}"] + 1)
                    st.rerun()


def render_account_files_table(shop_id: int, shop_name: str, account_id: int, account_name: str, files_df: pd.DataFrame, total_files: int, files_per_page: int = 20) -> None:
    """
    Render a table view of files linked to an account for a specific shop with pagination.
    
    Parameters:
        shop_id: ID of the shop
        shop_name: Name of the shop
        account_id: ID of the account
        account_name: Name of the account
        files_df: DataFrame with all files for this shop-account combination
        total_files: Total number of files
        files_per_page: Number of files per page (default: 20)
    """
  
  
    # Search input for file names
    search_query = st.text_input("🔍 Search files by name:", key=f"search_{account_id}_{shop_id}")
    
    # Filter files by search query
    if search_query:
        filtered_df = files_df[files_df['filename'].str.lower().str.contains(search_query.lower(), na=False)]
    else:
        filtered_df = files_df
    
    # Calculate pagination for filtered results
    filtered_total = len(filtered_df)
    filtered_pages = (filtered_total + files_per_page - 1) // files_per_page if filtered_total > 0 else 1
    
    # Initialize pagination in session state for filtered view
    if f"filtered_page_{shop_id}_{account_id}" not in st.session_state:
        st.session_state[f"filtered_page_{shop_id}_{account_id}"] = 0
    
    # Ensure current page is within bounds
    if filtered_pages > 0 and st.session_state[f"filtered_page_{shop_id}_{account_id}"] >= filtered_pages:
        st.session_state[f"filtered_page_{shop_id}_{account_id}"] = filtered_pages - 1
    
    # Get paginated filtered files
    if search_query and filtered_total > 0:
        start_idx = st.session_state[f"filtered_page_{shop_id}_{account_id}"] * files_per_page
        end_idx = start_idx + files_per_page
        paginated_filtered_df = filtered_df.iloc[start_idx:end_idx]
    else:
        paginated_filtered_df = filtered_df
    
    if not paginated_filtered_df.empty:
        st.markdown(f"**Total files linked:** {total_files} | **Showing:** {filtered_total} | **Page:** {st.session_state.get(f'filtered_page_{shop_id}_{account_id}', 0) + 1 if search_query else 1} | **Shop:** {shop_name}")
        
        # Display table with columns: Preview, Filename, File ID, Actions
        for _, row in paginated_filtered_df.iterrows():
            render_account_file_row(row, shop_id, account_id)
        
        # Pagination controls for filtered view
        if search_query and filtered_pages > 1:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if st.button("◀️ Previous", key=f"prev_filtered_{shop_id}_{account_id}"):
                    st.session_state[f"filtered_page_{shop_id}_{account_id}"] = max(0, st.session_state[f"filtered_page_{shop_id}_{account_id}"] - 1)
                    st.rerun()
            with col2:
                st.caption(f"Page {st.session_state[f'filtered_page_{shop_id}_{account_id}'] + 1} of {filtered_pages}")
            with col3:
                if st.button("Next ▶️", key=f"next_filtered_{shop_id}_{account_id}"):
                    st.session_state[f"filtered_page_{shop_id}_{account_id}"] = min(filtered_pages - 1, st.session_state[f"filtered_page_{shop_id}_{account_id}"] + 1)
                    st.rerun()
        
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
    col1, col2, col3 = st.columns([1, 1, 1])
    
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
        st.markdown(f"File Name: **{file_data['filename']}**")
        # Get display name for this file in this shop/account
        display_name = get_display_name_for_file(
            file_id=file_data['file_id'],
            shop_id=shop_id,
            account_id=account_id
        )

        st.markdown(f"Display Name: **{display_name if display_name else '**NaN**'}**")
        st.markdown(f"ID: **{file_data['file_id']}**")
    
    with col3:
        # Remove from account button (include shop_id for uniqueness across shops)
        if st.button("🗑️", key=f"remove_from_acc_{shop_id}_{file_data['file_id']}_{account_id}"):
            try:
                from db_handler import unlink_file_from_account_with_shop_check
                success, removed_from_shop, message = unlink_file_from_account_with_shop_check(
                    file_data['file_id'], account_id, shop_id
                )
                
                if success:
                    st.success(f"File removed from account")
                    if removed_from_shop:
                        st.success(f"File also removed from shop (no other accounts linked)")
                    else:
                        st.info(f"File still linked to other accounts in this shop")
                    st.rerun()
                else:
                    st.error(message)
            except Exception as e:
                st.error(f"Error: {e}")

        with st.expander("✏️ Edit Display Name", expanded=False):
            from forms.file_form import render_edit_display_name_form
            render_edit_display_name_form(shop_id=shop_id, file_id=file_data['file_id'], account_id=account_id)


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
                render_account_tab(shop_id, shop_name, acc_id, acc_name, account_tabs, tab_index=acc_idx + 2)
    
    return shop_list, account_tabs_list

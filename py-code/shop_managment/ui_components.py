"""
UI Components for the Shop Management app.
Provides reusable components for the Streamlit interface.
"""

import streamlit as st
import pandas as pd
import os
from sqlalchemy import create_engine, MetaData, Table, select, insert, delete, update, func


def render_shops_table(shops_df: pd.DataFrame) -> None:
    """
    Render an interactive table for managing shops with add/remove functionality.
    
    Parameters:
        shops_df (pd.DataFrame): DataFrame with shop_id and shop_name columns
    """
    

    # Display shops table
    if not shops_df.empty:
        # Create a copy for display with index
        display_df = shops_df.copy()
        display_df['Index'] = range(1, len(display_df) + 1)
        
        # Reorder columns for display
        display_df = display_df[['Index', 'shop_id', 'shop_name']]
        with st.container(border=True):
            # Add new shop section
            with st.container():
                shop_col1,shop_col2 = st.columns([2,1])
                with shop_col1:
                    new_shop_name = st.text_input("Enter shop name:")
                with shop_col2:
                    st.space(size='small')
                    if st.button("Add Shop", key="add_shop_button"):
                        if new_shop_name.strip():
                            try:
                                from db_handler import add_shop
                                new_id = add_shop(new_shop_name.strip())
                                st.success(f"Shop '{new_shop_name}' added with ID: {new_id}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error adding shop: {e}")
                        else:
                            st.warning("Please enter a shop name.")
            
        # Handle remove actions
            head_col1, head_spacer = st.columns([1, 5])
            with head_col1:
                st.markdown(f"**<div style='text-align: left;'>Shop-Website</div>**", unsafe_allow_html=True)

            for _, row in shops_df.iterrows():
                # Wrap shop row and accounts in a bordered container when accounts are shown
                with st.container(border=st.session_state.get(f"showing_accounts_{row['shop_id']}", False)):
                    
                    with st.expander(row['shop_name']):
                        sub_head1, sub_head2, sub_head3 = st.columns([1,1,1])
  
                        with sub_head1:
                            st.markdown(f"**<div style='text-align: left;'>__Shop Details__</div>**", unsafe_allow_html=True)

                            # Get account count for this shop
                            try:
                                from db_handler import get_accounts_for_shop, get_file_count_for_shop
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
                            st.dataframe(df_info_table, hide_index=True, use_container_width=True)
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
                                with st.container(horizontal_alignment="right",horizontal=True,):
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
                                        try:
                                            from db_handler import remove_shop
                                            if remove_shop(row['shop_id']):
                                                st.success(f"Shop '{row['shop_name']}' removed")
                                                st.rerun()
                                            else:
                                                st.error("Shop not found")
                                        except Exception as e:
                                            st.error(f"Error removing shop: {e}")
                        
                            # Edit mode for this shop
                            if st.session_state.get(f"editing_{row['shop_id']}"):
                                new_name = st.text_input(
                                    f"Edit shop name for ID {row['shop_id']}",
                                    value=row['shop_name'],
                                    key=f"edit_input_{row['shop_id']}"
                                )
                                save_col, cancel_col = st.columns([1, 1])
                                with save_col:
                                    if st.button("💾 Save", key=f"save_btn_{row['shop_id']}"):
                                        try:
                                            from db_handler import update_shop
                                            if update_shop(row['shop_id'], new_name):
                                                st.success(f"Shop name updated to '{new_name}'")
                                                st.session_state[f"editing_{row['shop_id']}"] = False
                                                st.rerun()
                                            else:
                                                st.error("Shop not found")
                                        except Exception as e:
                                            st.error(f"Error updating shop: {e}")
                                with cancel_col:
                                    if st.button("❌ Cancel", key=f"cancel_btn_{row['shop_id']}"):
                                        st.session_state[f"editing_{row['shop_id']}"] = False
                                        st.rerun()
                        # Account management for this shop - in same row, indented
                        if st.session_state.get(f"showing_accounts_{row['shop_id']}"):
                            st.markdown("")  # Empty spacer for indentation
                            render_account_table(row['shop_id'], shops_df)

    else:
        st.info("No shops found. Add a new shop above.")


def render_files_table(shop_id: int, total_files: int) -> None:
    """
    Render an interactive table for managing files linked to a shop.
    
    Parameters:
        shop_id (int): ID of the shop
        total_files (int): Total number of files linked to the shop
    """
    st.subheader(f"📁 Files for Shop ID: {shop_id}")
    st.markdown(f"**Total files linked:** {total_files}")
    
    # Add file section
    with st.expander("➕ Add Files to Shop", expanded=False):
        render_add_files_section(shop_id)
    
    # Display files table
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
            from db_handler import get_files_for_shop
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


def render_file_overview(shop_id: int, total_files: int) -> None:
    """
    Render an overview of files linked to a shop.
    
    Parameters:
        shop_id (int): ID of the shop
        total_files (int): Total number of files linked to the shop
    """
    st.subheader(f"📁 Files for Shop ID: {shop_id}")
    st.markdown(f"**Total files linked:** {total_files}")
    
    # Add file section
    with st.expander("➕ Add Files to Shop", expanded=False):
        render_add_files_section(shop_id)


def render_add_files_section(shop_id: int) -> None:
    """
    Render a section to add files to a shop with chunked loading.
    
    Parameters:
        shop_id (int): ID of the shop to add files to
    """

    try:
        from db_handler import get_all_file_ids, get_file_info, get_files_for_shop
        
        # Get already linked file IDs for this shop
        linked_df, _ = get_files_for_shop(shop_id, page_size=10000, offset=0)
        linked_ids = set(linked_df['file_id'].tolist()) if not linked_df.empty else set()
        
        # Get all available file IDs
        all_file_ids = get_all_file_ids()
        
        # Filter out already linked files
        available_ids = [fid for fid in all_file_ids if fid not in linked_ids]
        
        # Chunk size for loading file info
        chunk_size = 100
        
        if available_ids:
            # Initialize session state for file options
            if f"file_options_{shop_id}" not in st.session_state:
                st.session_state[f"file_options_{shop_id}"] = {}
                st.session_state[f"file_options_loaded_{shop_id}"] = 0
            
            # Load file info in chunks
            loaded_count = st.session_state[f"file_options_loaded_{shop_id}"]
            current_options = st.session_state[f"file_options_{shop_id}"]
            
            # Load next chunk if needed
            if loaded_count < len(available_ids):
                chunk_end = min(loaded_count + chunk_size, len(available_ids))
                chunk_ids = available_ids[loaded_count:chunk_end]
                
                for fid in chunk_ids:
                    file_info = get_file_info(fid)
                    if file_info:
                        current_options[fid] = file_info['filename']
                
                st.session_state[f"file_options_loaded_{shop_id}"] = chunk_end
            
            # Create dropdown options from loaded file info
            file_options = st.session_state[f"file_options_{shop_id}"]
            
            if file_options:
                selected_file = st.selectbox(
                    "Select a file to add:",
                    options=list(file_options.keys()),
                    format_func=lambda x: file_options[x],
                    key=f"add_file_{shop_id}"
                )
                
                # Show progress if not all files loaded
                if loaded_count < len(available_ids):
                    st.write(f"Loaded {loaded_count} of {len(available_ids)} available files")
                    if st.button("Load More Files", key=f"load_more_files_{shop_id}"):
                        st.rerun()
                
                if st.button("Add File to Shop", key=f"add_file_btn_{shop_id}"):
                    if selected_file:
                        try:
                            from db_handler import link_file_to_shop
                            if link_file_to_shop(selected_file, shop_id):
                                st.success(f"File '{file_options[selected_file]}' added to shop")
                                st.rerun()
                            else:
                                st.warning("File already linked to shop")
                        except Exception as e:
                            st.error(f"Error adding file: {e}")
            else:
                st.info("Loading file options...")
        else:
            st.info("All files are already linked to this shop.")
            
    except Exception as e:
        st.error(f"Error loading files: {e}")


def render_file_row(file_data: dict, shop_id: int, is_infinite_scroll: bool = False, files_list: list = None) -> None:
    """
    Render a single file row with preview, filename, and delete button.
    
    Parameters:
        file_data (dict): File data containing file_id, filename, and preview_url
        shop_id (int): ID of the shop
        is_infinite_scroll (bool): If True, use infinite scroll delete logic
        files_list (list): Current files list for infinite scroll mode (for removal)
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
        

def render_infinite_scroll_file_list(shop_id: int, total_files: int) -> None:
    """
    Render an infinite scroll file list for a shop.
    
    Parameters:
        shop_id (int): ID of the shop
        total_files (int): Total number of files
    """
    # Get batch size
    batch_size = st.selectbox(
        "Files per load:",
        options=[10, 20, 50, 100],
        index=1,  # Default to 20
        key=f"batch_size_{shop_id}"
    )
    
    # Initialize loaded count in session state
    if f"loaded_{shop_id}" not in st.session_state:
        st.session_state[f"loaded_{shop_id}"] = 0
    
    # Get current loaded count
    loaded_count = st.session_state[f"loaded_{shop_id}"]
    
    # Fetch more files
    if st.button("Load More Files", key=f"load_more_{shop_id}"):
        from db_handler import get_files_for_shop
        files_df, _ = get_files_for_shop(shop_id, page_size=batch_size, offset=loaded_count)
        
        if not files_df.empty:
            # Store files in session state
            if f"files_{shop_id}" not in st.session_state:
                st.session_state[f"files_{shop_id}"] = []
            st.session_state[f"files_{shop_id}"].extend(files_df.to_dict('records'))
            st.session_state[f"loaded_{shop_id}"] += len(files_df)
        
        st.rerun()
    
    # Display loaded files
    if f"files_{shop_id}" in st.session_state and st.session_state[f"files_{shop_id}"]:
        files_list = st.session_state[f"files_{shop_id}"]
        
        for file_data in files_list:
            render_file_row(file_data, shop_id, is_infinite_scroll=True, files_list=files_list)
        
        # Show progress
        st.write(f"Loaded {loaded_count} of {total_files} files")
        
        if loaded_count < total_files:
            st.info("Click 'Load More' to load additional files...")
        else:
            st.success("All files loaded!")
    else:
        if total_files == 0:
            st.info(f"No files linked to this shop yet.")
        else:
            st.info(f"Click 'Load More' to load files (total: {total_files})")


def render_shop_selector(shops_df: pd.DataFrame) -> tuple:
    """
    Render tabs to choose a shop with nested account tabs for each shop.
    
    Parameters:
        shops_df (pd.DataFrame): DataFrame with shop_id and shop_name columns
        
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
        from db_handler import get_accounts_for_shop
        
        # Iterate through each shop tab
        for idx, (shop_name, shop_id) in enumerate(shop_list):
            with shop_tabs[idx]:
                print(f"Shop: {shop_name} (ID: {shop_id})")
                # Get accounts for this shop
                accounts_df = get_accounts_for_shop(shop_id)
                
                # Display accounts table
                if not accounts_df.empty:
                    
                    # Create sub-tabs for each account + "All files" tab
                    account_tab_names = accounts_df['account_name'].to_list()
                    all_account_tab_names = ['All files'] + account_tab_names
                    account_tabs = st.tabs(all_account_tab_names)
                    
                    # First tab: All files for this shop
                    with account_tabs[0]:
                        st.markdown('**All Files for Shop**')
                        from db_handler import get_files_for_shop
                        files_df, _ = get_files_for_shop(shop_id, page_size=10000, offset=0)
                        if not files_df.empty:
                            st.table(files_df[['file_id', 'filename']])
                        else:
                            st.info("No files linked to this shop yet.")
                    
                    # Create sub-tabs for each account linked to the shop
                    for acc_idx, account_name in enumerate(account_tab_names):
                        account_id = accounts_df.iloc[acc_idx]['account_id']
                        with account_tabs[acc_idx + 1]:
                            st.markdown(f'**Account: {account_name}**')
                            st.write(f"Account ID: {account_id}")
                            
                            # Initialize session state for pagination
                            if f'files_loaded_{account_id}' not in st.session_state:
                                st.session_state[f'files_loaded_{account_id}'] = 0
                            if f'total_files_{account_id}' not in st.session_state:
                                st.session_state[f'total_files_{account_id}'] = 0
                            
                            # Get files linked to this specific account and shop with pagination
                            from db_handler import get_files_for_shop_account_paginated
                            
                            # Display files
                            files_per_row = 2
                            files_per_chunk = 20
                            loaded_count = st.session_state[f'files_loaded_{account_id}']
                            
                            # Load more button (show after initial load)
                            if loaded_count > 0:
                                if st.button("Load More", key=f"load_more_{account_id}"):
                                    st.session_state[f'files_loaded_{account_id}'] += 20
                                    st.rerun()
                            
                            # Get files for current chunk (load 20 at a time)
                            files_df, total_count = get_files_for_shop_account_paginated(
                                shop_id, account_id, page_size=files_per_chunk, offset=loaded_count
                            )
                            
                            # Store total count for first load
                            if st.session_state[f'total_files_{account_id}'] == 0:
                                st.session_state[f'total_files_{account_id}'] = total_count
                            
                            if not files_df.empty:
                                # Display image previews - 2 files per row
                                for idx in range(0, len(files_df), files_per_row):
                                    chunk = files_df.iloc[idx:idx + files_per_row]
                                    
                                    # Create columns for this row
                                    cols = st.columns(files_per_row)
                                    
                                    for col_idx, row in chunk.iterrows():
                                        with cols[col_idx]:
                                            # Each file gets its own container that spans only that tile
                                            with st.container(border=True):
                                                # File info on left
                                                st.markdown(f"**{row['filename']}**")
                                                st.caption("Shop Display Name (placeholder)")
                                                # Image preview on right
                                                if row['preview_url'] and pd.notna(row['preview_url']):
                                                    from db_handler import get_preview_image
                                                    img = get_preview_image(
                                                        file_id=row['file_id'],
                                                        preview_url=row['preview_url']
                                                    )
                                                    if img is not None:
                                                        st.image(img, width=200)
                                                    else:
                                                        st.write("Image not available")
                                                else:
                                                    st.write("No preview available")
                            
                            # Show total count and load more status
                            total = st.session_state[f'total_files_{account_id}']
                            if loaded_count < total:
                                st.caption(f"Loaded {loaded_count} of {total} files. Click 'Load More' for more.")
                            else:
                                st.caption(f"All {total} files loaded.")
                else:
                    st.info("No accounts linked to this shop yet.")
    
    return shop_list, shop_tabs


def render_account_table(shop_id: int, shops_df: pd.DataFrame) -> None:
    """
    Render an interactive table for managing accounts linked to a shop.
    
    Parameters:
        shop_id (int): ID of the shop
        shops_df (pd.DataFrame): DataFrame with shop_id and shop_name columns
    """
    try:
        from db_handler import get_accounts_for_shop, get_all_accounts, add_account, link_account_to_shop, remove_account_from_shop, get_all_shops
        
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
                # Create a copy for display with index
                display_df = linked_df.copy()
                display_df['Index'] = range(1, len(display_df) + 1)
                
                # Reorder columns for display
                display_df = display_df[['Index', 'account_id', 'account_name']]
                
                
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
                                        # Update account name
                                        engine = create_db_connection()
                                        metadata = MetaData()
                                        bre_accounts = Table('bre_accounts', metadata, autoload_with=engine)
                                        with engine.begin() as connection:
                                            result = connection.execute(
                                                update(bre_accounts).where(bre_accounts.c.account_id == row['account_id']).values(account_name=new_name)
                                            )
                                        if result.rowcount > 0:
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


def render_accounts_table(accounts_df: pd.DataFrame) -> None:
    """
    Render an interactive table for managing all accounts with add/edit/remove functionality.
    
    Parameters:
        accounts_df (pd.DataFrame): DataFrame with account_id and account_name columns
    """
    try:
        from db_handler import add_account, remove_entity, update_entity
        
        # Display accounts table
        if not accounts_df.empty:
            # Create a copy for display with index
            display_df = accounts_df.copy()
            display_df['Index'] = range(1, len(display_df) + 1)
            
            # Reorder columns for display
            display_df = display_df[['Index', 'account_id', 'account_name']]
            
            with st.container(border=True):
                # Add new account section
                with st.container():
                    acc_col1, acc_col2 = st.columns([2, 1])
                    with acc_col1:
                        new_account_name = st.text_input("Enter new account name:")
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


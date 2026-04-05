"""
UI Components for the Shop Management app.
Provides reusable components for the Streamlit interface.
"""

import streamlit as st
import pandas as pd


def render_shop_table(shops_df: pd.DataFrame) -> None:
    """
    Render an interactive table for managing shops with add/remove functionality.
    
    Parameters:
        shops_df (pd.DataFrame): DataFrame with shop_id and shop_name columns
    """
    
    # Add new shop section
    with st.expander("➕ Add New Shop", expanded=False):
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
    
    # Display shops table
    if not shops_df.empty:
        # Create a copy for display with index
        display_df = shops_df.copy()
        display_df['Index'] = range(1, len(display_df) + 1)
        
        # Reorder columns for display
        display_df = display_df[['Index', 'shop_id', 'shop_name']]
        with st.container(border=True):
        # Handle remove actions
            head_col1, head_col2, head_col3 = st.columns([1, 1, 1])
            with head_col1:
                st.markdown(f"**<div style='text-align: left;'>Shop-Website</div>**", unsafe_allow_html=True)
            with head_col2:
                st.markdown(f"**<div style='text-align: right;'>Shop ID</div>**", unsafe_allow_html=True)
            with head_col3:
                st.markdown(f"**<div style='text-align: right;'>Actions</div>**", unsafe_allow_html=True)
            for _, row in shops_df.iterrows():
                # Wrap shop row and accounts in a bordered container when accounts are shown
                with st.container(border=st.session_state.get(f"showing_accounts_{row['shop_id']}", False)):
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        st.markdown(f"**<div style='text-align: left;'>{row['shop_name']}</div>**", unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"**<div style='text-align: right;'>{row['shop_id']}</div>**", unsafe_allow_html=True)
                    with col3:
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


def render_file_list(shop_id: int, use_pagination: bool = True) -> None:
    """
    Render an expandable file list for a shop with pagination or infinite scroll.
    
    Parameters:
        shop_id (int): ID of the shop
        use_pagination (bool): If True, use pagination; if False, use infinite scroll
    """
    try:
        from db_handler import get_file_count_for_shop, get_files_for_shop
        
        # Get total file count
        total_files = get_file_count_for_shop(shop_id)
        
        if total_files == 0:
            st.info("No files linked to this shop yet.")
            return
        
        # Pagination mode
        if use_pagination:
            render_paginated_file_list(shop_id, total_files)
        else:
            render_infinite_scroll_file_list(shop_id, total_files)
            
    except Exception as e:
        st.error(f"Error loading files: {e}")


def render_paginated_file_list(shop_id: int, total_files: int) -> None:
    """
    Render a paginated file list for a shop.
    
    Parameters:
        shop_id (int): ID of the shop
        total_files (int): Total number of files
    """
    # Get page size
    page_size = st.selectbox(
        "Files per page:",
        options=[10, 20, 50, 100],
        index=1,  # Default to 20
        key=f"page_size_{shop_id}"
    )
    
    # Calculate total pages
    total_pages = (total_files + page_size - 1) // page_size
    
    # Get current page
    current_page = st.number_input(
        "Page",
        min_value=1,
        max_value=total_pages,
        value=1,
        key=f"current_page_{shop_id}"
    )
    
    # Calculate offset
    offset = (current_page - 1) * page_size
    
    # Fetch files for current page
    from db_handler import get_files_for_shop
    files_df, _ = get_files_for_shop(shop_id, page_size=page_size, offset=offset)
    
    # Display pagination controls
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if current_page > 1:
            if st.button("⬅️ Previous", key=f"prev_{shop_id}"):
                st.session_state[f"page_{shop_id}"] = current_page - 1
                st.rerun()
    
    with col2:
        st.write(f"Page {current_page} of {total_pages} ({total_files} total files)")
    
    with col3:
        if current_page < total_pages:
            if st.button("Next ➡️", key=f"next_{shop_id}"):
                st.session_state[f"page_{shop_id}"] = current_page + 1
                st.rerun()
    
    # Display files
    if not files_df.empty:
        for _, row in files_df.iterrows():
            col1, col2, col3 = st.columns([3, 5, 1])
            
            with col1:
                # Try to display preview
                preview_url = row['preview_url']
                if preview_url:
                    full_preview_url = f"http://{{DB_HOST}}:8080{preview_url.replace('{prevsize}', 'x=100&y=100')}"
                    st.image(full_preview_url, width='stretch')
                else:
                    st.write("📄")
            
            with col2:
                st.markdown(f"**{row['filename']}**")
            
            with col3:
                if st.button("🗑️", key=f"remove_file_{row['file_id']}_{shop_id}"):
                    try:
                        from db_handler import unlink_file_from_shop
                        if unlink_file_from_shop(row['file_id'], shop_id):
                            st.success("File removed")
                            st.rerun()
                        else:
                            st.error("Failed to remove file")
                    except Exception as e:
                        st.error(f"Error: {e}")
    else:
        st.info("No files on this page.")


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
                if st.button("🗑️", key=f"remove_file_inf_{file_data['file_id']}_{shop_id}"):
                    try:
                        from db_handler import unlink_file_from_shop
                        if unlink_file_from_shop(file_data['file_id'], shop_id):
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


def render_shop_selector(shops_df: pd.DataFrame) -> int:
    """
    Render a selector to choose a shop.
    
    Parameters:
        shops_df (pd.DataFrame): DataFrame with shop_id and shop_name columns
        
    Returns:
        int: Selected shop_id
    """
    if shops_df.empty:
        st.warning("No shops available. Add a shop first.")
        return None
    
    # Create options dictionary
    shop_options = {
        f"{row['shop_name']} (ID: {row['shop_id']})": row['shop_id']
        for _, row in shops_df.iterrows()
    }
    
    selected = st.selectbox(
        "Select a shop:",
        options=list(shop_options.keys()),
        format_func=lambda x: x,
        key="shop_selector"
    )
    
    return shop_options[selected]


def render_account_table(shop_id: int, shops_df: pd.DataFrame) -> None:
    """
    Render an interactive table for managing accounts linked to a shop.
    
    Parameters:
        shop_id (int): ID of the shop
        shops_df (pd.DataFrame): DataFrame with shop_id and shop_name columns
    """
    try:
        from db_handler import get_accounts_for_shop, get_all_accounts, add_account, link_account_to_shop, remove_account_from_shop
        
        # Get accounts linked to this shop
        linked_df = get_accounts_for_shop(shop_id)
        with st.container(border=True):
                
            # Add new account section
            new_account_name = st.text_input("Enter account name:", key=f"new_account_input_{shop_id}")
            with st.expander("➕ Add New Account", expanded=False):
                if st.button("Add Account", key=f"add_account_{shop_id}"):
                    if new_account_name.strip():
                        try:
                            new_id = add_account(new_account_name.strip())
                            st.success(f"Account '{new_account_name}' added with ID: {new_id}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error adding account: {e}")
                    else:
                        st.warning("Please enter an account name.")
            
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
                    st.markdown(f"**<div style='text-align: right;'>Action</div>**", unsafe_allow_html=True)
                
                for _, row in linked_df.iterrows():
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        st.markdown(f"**<div style='text-align: left;'>{row['account_name']}</div>**", unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"**<div style='text-align: left;'>ID: {row['account_id']}</div>**", unsafe_allow_html=True)
                    with col3:
                        subcol1, subcol2 = st.columns([1, 1])
                        with subcol1:
                            if st.button("✏️", key=f"edit_acc_btn_{row['account_id']}"):
                                st.session_state[f"editing_acc_{row['account_id']}"] = True
                        with subcol2:
                            if st.button("🗑️", key=f"remove_acc_btn_{row['account_id']}"):
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
                # Add account to shop section
                with st.expander("🔗 Link Existing Account to Shop", expanded=False):
                    all_accounts = get_all_accounts()
                    if not all_accounts.empty:
                        # Get already linked account IDs
                        linked_ids = set(linked_df['account_id'].tolist())
                        available_ids = [aid for aid in all_accounts['account_id'] if aid not in linked_ids]
                        
                        if available_ids:
                            account_options = {
                                f"{row['account_name']} (ID: {row['account_id']})": row['account_id']
                                for _, row in all_accounts[all_accounts['account_id'].isin(available_ids)].iterrows()
                            }
                            
                            selected_account = st.selectbox(
                                "Select an account to link:",
                                options=list(account_options.keys()),
                                format_func=lambda x: x,
                                key=f"link_account_{shop_id}"
                            )
                            
                            if st.button("Link Account", key=f"link_account_btn_{shop_id}"):
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
                            st.info("All accounts are already linked to this shop.")
                    else:
                        st.info("No accounts available. Add an account first.")

            
    except Exception as e:
        st.error(f"Error loading accounts: {e}")


def create_db_connection():
    """
    Create a database connection using environment variables.
    
    Returns:
        sqlalchemy.engine.Engine: Database engine connection
    """
    import os
    from dotenv import load_dotenv
    from sqlalchemy import create_engine
    
    load_dotenv()
    DB_HOST = os.getenv("DB_HOST")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    engine = create_engine(
        f'postgresql+pg8000://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}'
    )
    return engine


from sqlalchemy import MetaData, Table, update

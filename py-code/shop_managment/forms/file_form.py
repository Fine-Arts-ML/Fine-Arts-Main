"""
File form components for the Shop Management app.
"""

import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from io import BytesIO
from PIL import Image
from db_handler import (
    get_files_for_shop, get_all_file_ids_with_info, get_all_hashes_from_db,
    get_preview_image, link_file_to_account, link_file_to_shop, link_account_to_shop,
    get_all_shops, get_accounts_for_shop, get_accounts_for_file,
    get_display_names_for_file, add_display_name, add_display_name_to_file,
    link_display_name_to_shop_account
)
from utils.constants import HASH_TYPES, IMAGE_RESIZE_1080

# Load environment variables
load_dotenv()
DB_HOST = os.getenv("DB_HOST", "192.168.0.150")


def render_file_select_expander(
    shop_id: int,
    selected_file: dict,
    idx: int,
    col_idx: int,
    unique_key_suffix: str = ""
) -> None:
    """
    Render a reusable select expander modal for file selection.
    The shop is pre-selected from the tab context, only account selection is shown.
    Simplified version: only links file to shop and account, no display name management.
    
    Parameters:
        shop_id: ID of the shop to add files to (pre-selected from tab context)
        selected_file: Dictionary containing file information (file_id, filename, preview_url, etc.)
        idx: Row index in the chunk (for unique keys)
        col_idx: Column index in the chunk (for unique keys)
        unique_key_suffix: Optional suffix for unique session state keys
    """
    # Set selected file in session state
    st.session_state[f"selected_file_{shop_id}"] = selected_file
    
    selected_file_data = st.session_state[f"selected_file_{shop_id}"]
    
    st.markdown(f"**Add File to Shop & Account**")
    st.markdown(f"File: {selected_file_data['filename']}")
    
    # Show file preview if available
    if selected_file_data.get('preview_url'):
        full_preview_url = f"http://{{DB_HOST}}:8080{selected_file_data['preview_url'].replace('{prevsize}', 'x=200&y=200')}"
        st.image(full_preview_url, use_container_width=True)
    
    # Get accounts for the pre-selected shop
    accounts_df = get_accounts_for_shop(shop_id)
    
    if not accounts_df.empty:
        account_options = {f"{row['account_name']} (ID: {row['account_id']})": row['account_id']
                          for _, row in accounts_df.iterrows()}
        
        session_key_account = f"selected_account_{shop_id}_{idx}_{col_idx}{unique_key_suffix}"
        if session_key_account not in st.session_state:
            st.session_state[session_key_account] = []
        
        selected_account_keys = st.multiselect(
            "Select Account(s):",
            options=list(account_options.keys()),
            default=st.session_state.get(session_key_account, []),
            key=f"modal_account_{shop_id}_{idx}_{col_idx}{unique_key_suffix}",
            on_change=None
        )
        
        # Update session state if selection changed
        if selected_account_keys != st.session_state.get(session_key_account, []):
            st.session_state[session_key_account] = selected_account_keys
        
        selected_account_ids = [account_options[key] for key in selected_account_keys]
    else:
        st.warning("No accounts linked to this shop yet.")
        selected_account_ids = []
    
    # Single Confirm button for linking file to shop and account
    if st.button("Confirm Link", key=f"confirm_add_{shop_id}_{idx}_{col_idx}{unique_key_suffix}", type="primary"):
        # Link file to shop (using pre-selected shop_id)
        shop_link_result = link_file_to_shop(selected_file_data['file_id'], shop_id)
        
        if shop_link_result:
            st.success(f"File linked to shop ID: {shop_id}")
        else:
            st.info(f"File already linked to shop ID: {shop_id}")
        
        # Link file to selected accounts
        if len(selected_account_ids) > 0:
            for acc_id in selected_account_ids:
                # Get account name
                acc_name = [k for k, v in account_options.items() if v == acc_id][0]
                
                # Link account to shop
                link_account_to_shop(shop_id, acc_id)
                st.success(f"Account linked to shop")
                
                # Link file to account
                account_link_result = link_file_to_account(selected_file_data['file_id'], acc_id)
                
                if account_link_result:
                    st.success(f"File also linked to account '{acc_name}'")
                else:
                    st.info(f"File already linked to account '{acc_name}'")
        else:
            st.info("No accounts selected")
    
    # Second expander: Add Display Name (only shows after file is linked)
    # Check if file is already linked to this shop
    from db_handler import get_accounts_for_file_in_shop
    file_linked_accounts_df = get_accounts_for_file_in_shop(selected_file_data['file_id'], shop_id)
    file_linked_account_ids = set(file_linked_accounts_df['account_id'].tolist()) if not file_linked_accounts_df.empty else set()
    
    # Only show display name expander if file is linked to at least one account
    if len(file_linked_account_ids) > 0:
        with st.expander("🏷️ Add Display Name to File", expanded=True):
            st.markdown(f"**Add Display Name to File**")
            st.markdown(f"File: {selected_file_data['filename']}")
            
            # Get accounts for the shop
            accounts_df_dn = get_accounts_for_shop(shop_id)
            
            if not accounts_df_dn.empty:
                account_options_dn = {f"{row['account_name']} (ID: {row['account_id']})": row['account_id']
                                      for _, row in accounts_df_dn.iterrows()}
                
                # Determine which accounts to show in multiselect
                # Show only accounts that file is already linked to
                available_accounts = {
                    key: acc_id for key, acc_id in account_options_dn.items()
                    if acc_id in file_linked_account_ids
                }
                default_accounts = [
                    key for key in available_accounts.keys()
                ]
                
                selected_account_keys_dn = st.multiselect(
                    "Select Account(s) to link display name to:",
                    options=list(available_accounts.keys()),
                    default=default_accounts,
                    key=f"add_dn_account_{shop_id}_{idx}_{col_idx}{unique_key_suffix}"
                )
                
                selected_account_ids_dn = [account_options_dn[key] for key in selected_account_keys_dn]
            else:
                st.warning("No accounts linked to this shop yet.")
                selected_account_ids_dn = []
            
            # Text input for new display name
            new_display_name_input = st.text_input(
                "Enter new display name:",
                key=f"add_dn_input_{shop_id}_{idx}_{col_idx}{unique_key_suffix}"
            )
            
            # Confirm button for display name
            if st.button("Confirm Display Name", key=f"confirm_add_dn_{shop_id}_{idx}_{col_idx}{unique_key_suffix}", type="primary"):
                if new_display_name_input.strip() and len(selected_account_ids_dn) > 0:
                    # Create display name (without file_id linkage)
                    display_name_id = add_display_name(new_display_name_input.strip())
                    
                    # Link to selected accounts
                    for acc_id in selected_account_ids_dn:
                        acc_name = [k for k, v in account_options_dn.items() if v == acc_id][0]
                        link_display_name_to_shop_account(
                            display_name_id=display_name_id,
                            shop_id=shop_id,
                            account_id=acc_id,
                            file_id=str(selected_file_data['file_id'])
                        )
                        st.success(f"Display name '{new_display_name_input}' linked to account '{acc_name}'")
                elif not new_display_name_input.strip():
                    st.info("Enter a display name")
                elif len(selected_account_ids_dn) == 0:
                    st.info("Select at least one account")


def render_assign_display_name_form(shop_id: int, file_id: int) -> None:
    """
    Render a form to assign a display name to an already-linked file.
    
    Parameters:
        shop_id: ID of the shop
        file_id: ID of the file
    """
    st.markdown("---")
    st.markdown("**Assign Display Name to Linked File**")
    
    # Get file info
    from db_handler import get_file_info
    file_info = get_file_info(file_id)
    st.markdown(f"File: {file_info.get('filename', 'Unknown')}")
    
    # Get accounts for shop
    accounts_df = get_accounts_for_shop(shop_id)
    
    if not accounts_df.empty:
        account_options = {
            f"{row['account_name']} (ID: {row['account_id']})": row['account_id']
            for _, row in accounts_df.iterrows()
        }
        
        selected_account_key = f"assign_dn_account_{shop_id}_{file_id}"
        if selected_account_key not in st.session_state:
            st.session_state[selected_account_key] = []
        
        selected_account_keys = st.multiselect(
            "Select Account(s):",
            options=list(account_options.keys()),
            default=st.session_state.get(selected_account_key, []),
            key=f"assign_dn_account_select_{shop_id}_{file_id}"
        )
        
        # Update session state if selection changed
        if selected_account_keys != st.session_state.get(selected_account_key, []):
            st.session_state[selected_account_key] = selected_account_keys
        
        selected_account_ids = [account_options[key] for key in selected_account_keys]
    else:
        st.warning("No accounts linked to this shop yet.")
        selected_account_ids = []
    
    # Get existing display names for this file
    existing_display_names_df = get_display_names_for_file(str(file_id))
    
    # Option 1: Select existing display name
    st.subheader("Link Existing Display Name")
    if not existing_display_names_df.empty:
        existing_name_options = {
            f"{row['display_name']} (ID: {row['display_name_id']})": row['display_name_id']
            for _, row in existing_display_names_df.iterrows()
        }
        
        existing_dn_key = f"assign_existing_dn_{shop_id}_{file_id}"
        if existing_dn_key not in st.session_state:
            st.session_state[existing_dn_key] = []
        
        selected_existing_keys = st.multiselect(
            "Select existing display name(s) to link:",
            options=list(existing_name_options.keys()),
            default=st.session_state.get(existing_dn_key, []),
            key=f"assign_existing_dn_select_{shop_id}_{file_id}"
        )
        
        # Update session state if selection changed
        if selected_existing_keys != st.session_state.get(existing_dn_key, []):
            st.session_state[existing_dn_key] = selected_existing_keys
        
        selected_existing_ids = [existing_name_options[key] for key in selected_existing_keys]
    else:
        st.info("No existing display names for this file")
        selected_existing_ids = []
    
    # Option 2: Create new display name
    st.subheader("Create New Display Name")
    new_display_name_input = st.text_input(
        "Enter new display name:",
        key=f"assign_new_dn_input_{shop_id}_{file_id}"
    )
    
    # Action buttons
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("Assign Display Name", key=f"assign_dn_{shop_id}_{file_id}", type="primary"):
            # Link existing display names to selected accounts
            if len(selected_existing_ids) > 0:
                for acc_id in selected_account_ids:
                    acc_name = [k for k, v in account_options.items() if v == acc_id][0]
                    for dn_id in selected_existing_ids:
                        link_display_name_to_shop_account(dn_id, shop_id, acc_id, str(file_id))
                        st.success(f"Display name linked to account '{acc_name}'")
            
            # Create and link new display name if provided
            if new_display_name_input.strip() and len(selected_account_ids) > 0:
                new_display_name_id = add_display_name(
                    str(file_id),
                    new_display_name_input.strip()
                )
                for acc_id in selected_account_ids:
                    acc_name = [k for k, v in account_options.items() if v == acc_id][0]
                    link_display_name_to_shop_account(new_display_name_id, shop_id, acc_id, str(file_id))
                    st.success(f"Created and linked display name: '{new_display_name_input}'")
            
            if not selected_existing_ids and not new_display_name_input.strip():
                st.info("No display names to assign")
    
    with btn_col2:
        if st.button("Cancel", key=f"cancel_assign_dn_{shop_id}_{file_id}"):
            if f"assign_dn_account_{shop_id}_{file_id}" in st.session_state:
                del st.session_state[f"assign_dn_account_{shop_id}_{file_id}"]
            if f"assign_existing_dn_{shop_id}_{file_id}" in st.session_state:
                del st.session_state[f"assign_existing_dn_{shop_id}_{file_id}"]
    


def render_add_file_form(shop_id: int, tab_context: str = None) -> None:
    """
    Render add file form for a shop.
    
    Parameters:
        shop_id: ID of the shop
        tab_context: Optional unique context identifier for the tab (e.g., tab index)
    """
    # Create unique key with tab context to avoid duplicate element keys
    unique_key_suffix = f"_{tab_context}" if tab_context else ""
    
    # Search method dropdown
    search_method = st.selectbox(
        "Search Method:",
        options=["Text Search (by filename)", "Reverse Image Search"],
        key=f"add_files_search_method_{shop_id}{unique_key_suffix}"
    )
    
    if search_method == "Text Search (by filename)":
        render_text_search_files(shop_id, tab_context=tab_context)
    else:
        render_reverse_image_search(shop_id)


def render_text_search_files(shop_id: int, tab_context: str = None) -> None:
    """
    Render text-based file search by filename.
    
    Parameters:
        shop_id: ID of the shop to add files to
        tab_context: Optional unique context identifier for the tab (e.g., tab index)
    """

    
    # Create unique key with tab context to avoid duplicate element keys
    unique_key_suffix = f"_{tab_context}" if tab_context else ""
    
    # Get already linked file IDs for this shop
    linked_df = get_files_for_shop(shop_id)
    linked_ids = set(linked_df['file_id'].tolist()) if not linked_df.empty else set()
    
    # Text input for filename search
    search_query = st.text_input("Enter filename to search:", key=f"text_search_{shop_id}{unique_key_suffix}")
    
    if search_query:
        # Get all files with info
        all_files_df = get_all_file_ids_with_info()
        

        
        # Filter by search query (case-insensitive)
        filtered_df = all_files_df[
            all_files_df['filename'].str.lower().str.contains(search_query.lower(), na=False)
        ]


        if not filtered_df.empty:
            # Limit to first 24 results
            MAX_RESULTS = 24
            if len(filtered_df) > MAX_RESULTS:
                st.warning(f"Found {len(filtered_df)} matching files. Showing first {MAX_RESULTS}. Make your search more specific.")
                filtered_df = filtered_df.head(MAX_RESULTS)
            else:
                st.write(f"Found {len(filtered_df)} matching files")
            
            # Get all accounts for this shop
            accounts_df = get_accounts_for_shop(shop_id)
            total_accounts = len(accounts_df)
            
            # Display files in rows
            for idx in range(0, len(filtered_df), 3):
                chunk = filtered_df.iloc[idx:idx + 3]
                num_files = len(chunk)
                cols = st.columns(num_files)
                
                for col_idx, (_, row) in enumerate(chunk.iterrows()):
                    with cols[col_idx]:
                        with st.container(border=True):
                            # Preview
                            if row['preview_url'] and pd.notna(row['preview_url']):
                                img = get_preview_image(
                                    file_id=row['file_id'],
                                    preview_url=row['preview_url']
                                )
                                if img is not None:
                                    st.image(img, use_container_width=True)
                                else:
                                    st.write("📄")
                            else:
                                st.write("📄")
                            
                            # Filename
                            filename_display = row['filename'].split(' - ')[0] if ' - ' in row['filename'] else row['filename']
                            st.caption(filename_display)
                            
                            # Check if file is already linked to all accounts for this shop
                            file_id = row['file_id']
                            linked_accounts_df = get_accounts_for_file(file_id)
                            linked_account_ids = set(linked_accounts_df['account_id'].tolist()) if not linked_accounts_df.empty else set()
                            shop_account_ids = set(accounts_df['account_id'].tolist())
                            
                            # Check if file is linked to all accounts in this shop
                            is_linked_to_all = shop_account_ids.issubset(linked_account_ids)
                            
                            if is_linked_to_all and total_accounts > 0:
                                st.info(f"✅ Already linked to all {total_accounts} account(s)")
                            else:
                                # Select expander
                                with st.expander("Select"):
                                    selected_file_data = {
                                        'file_id': row['file_id'],
                                        'filename': row['filename'],
                                        'preview_url': row.get('preview_url', '')
                                    }
                                    render_file_select_expander(
                                        shop_id=shop_id,
                                        selected_file=selected_file_data,
                                        idx=idx,
                                        col_idx=col_idx,
                                        unique_key_suffix=unique_key_suffix
                                    )
        else:
            st.info("No matching files found.")
    else:
        st.info("Enter a filename to search.")


def render_reverse_image_search(shop_id: int) -> None:
    """
    Render reverse image search using perceptual hashing.
    
    Parameters:
        shop_id: ID of the shop to add files to
    """
    # Import fingerprinting module
    try:
        from fingerprinting.hash_calc import compute_hashes, find_closest_matches
    except ImportError:
        import sys
        sys.path.insert(0, '/Users/tom/Fine-arts-ML/Fine-Arts-Main/py-code')
        from fingerprinting.hash_calc import compute_hashes, find_closest_matches
    
    # Get already linked file IDs for this shop
    linked_df = get_files_for_shop(shop_id)
    linked_ids = set(linked_df['file_id'].tolist()) if not linked_df.empty else set()
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Upload an image for reverse search",
        type=['jpg', 'jpeg', 'png', 'tif', 'tiff'],
        key=f"image_upload_{shop_id}"
    )
    
    if uploaded_file is not None:
        # Display uploaded image
        img_bytes = BytesIO(uploaded_file.read())
        img = Image.open(img_bytes)
        
        # Resize to 1080x1080 to match database hashes
        img_resized = img.resize(IMAGE_RESIZE_1080)
        
        # Compute hashes
        with st.spinner("Computing hashes..."):
            query_whash, query_ahash, query_phash = compute_hashes(img_resized)
        
        st.markdown("**Uploaded Image**")
        st.image(img, use_container_width=True)
        
        # Fetch all hashes from database
        with st.spinner("Fetching hashes from database..."):
            df_hashes = get_all_hashes_from_db()
        
        # Find closest matches
        with st.spinner("Finding closest matches..."):
            results = find_closest_matches(df_hashes, query_whash, query_ahash, query_phash, top_n=20)
        
        if len(results) > 0:
            # Hash type selector
            hash_type = st.radio(
                "Select hash type to view:",
                options=HASH_TYPES,
                horizontal=True,
                index=2,  # Default to PHASH
                key=f"hash_type_radio_{shop_id}"
            )
            
            # Map hash type to column name
            hash_col_map = {"WHASH": "whash_distance", "AHASH": "ahash_distance", "PHASH": "phash_distance"}
            selected_hash_col = hash_col_map[hash_type]
            
            # Re-fetch results with selected hash type
            results = find_closest_matches(df_hashes, query_whash, query_ahash, query_phash, top_n=10)
            results_sorted = results.sort_values(selected_hash_col).head(10)
            
            # Filter out already linked files
            results_sorted = results_sorted[~results_sorted['fileid'].isin(linked_ids)]
            
            if len(results_sorted) > 0:
                st.subheader(f"Top {len(results_sorted)} Closest Matches")
                
                # Display results in rows
                for idx in range(0, len(results_sorted), 2):
                    chunk = results_sorted.iloc[idx:idx + 2]
                    cols = st.columns(2)
                    
                    for col_idx, row in enumerate(chunk.itertuples()):
                        with cols[col_idx]:
                            with st.container(border=True):
                                # Preview
                                file_id = getattr(row, 'fileid', None)
                                preview_url = getattr(row, 'preview_url', None)
                                if pd.notna(preview_url) and file_id:
                                    img = get_preview_image(file_id, preview_url, DB_HOST)
                                    if img:
                                        st.image(img, use_container_width=True)
                                    else:
                                        st.write("📄")
                                else:
                                    st.write("📄")
                                
                                # Filename and distance
                                st.caption(row.filename)
                                st.caption(f"{hash_type} Distance: {getattr(row, selected_hash_col)}")
                                
                                # Select expander
                                with st.expander("Select"):
                                    selected_file_data = {
                                        'file_id': row.fileid,
                                        'filename': row.filename,
                                        'preview_url': preview_url,
                                        'distance': getattr(row, selected_hash_col),
                                        'hash_type': hash_type
                                    }
                                    render_file_select_expander(
                                        shop_id=shop_id,
                                        selected_file=selected_file_data,
                                        idx=idx,
                                        col_idx=col_idx
                                    )
            else:
                st.info("All matching files are already linked to this shop.")
        else:
            st.info("No matches found.")
    else:
        st.info("Upload an image to start reverse search.")



def render_add_display_name_modal(file_id: int, shop_id: int) -> None:
    """
    Render a modal for adding a new display name to a file.
    
    Parameters:
        file_id: ID of the file
        shop_id: ID of the shop
    """
    modal_key = f"show_add_dn_{file_id}_{shop_id}"
    
    if st.session_state.get(modal_key, False):
        with st.container(border=True):
            st.markdown("**Add New Display Name**")
            
            # Get file info
            from db_handler import get_file_info
            file_info = get_file_info(file_id)
            st.markdown(f"File: {file_info.get('filename', 'Unknown')}")
            
            # Display name input
            new_display_name = st.text_input(
                "Display Name:",
                key=f"modal_new_dn_input_{file_id}_{shop_id}"
            )
            
            # Get accounts for shop
            accounts_df = get_accounts_for_shop(shop_id)
            if not accounts_df.empty:
                account_options = {
                    f"{row['account_name']} (ID: {row['account_id']})": row['account_id']
                    for _, row in accounts_df.iterrows()
                }
                selected_account = st.selectbox(
                    "Select Account:",
                    options=list(account_options.keys()),
                    key=f"modal_account_select_{file_id}_{shop_id}"
                )
                account_id = account_options[selected_account]
            else:
                st.warning("No accounts linked to this shop yet.")
                account_id = None
            
            # Buttons
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("Add", key=f"modal_add_dn_{file_id}_{shop_id}", type="primary"):
                    if new_display_name.strip() and account_id:
                        # Create display name
                        display_name_id = add_display_name(
                            str(file_id),
                            new_display_name.strip()
                        )
                        
                        # Link to shop and account
                        link_display_name_to_shop_account(
                            display_name_id=display_name_id,
                            shop_id=shop_id,
                            account_id=account_id,
                            file_id=str(file_id)
                        )
                        
                        st.success(f"Display name '{new_display_name}' added successfully")
                        del st.session_state[modal_key]
                        st.rerun()
            
            with btn_col2:
                if st.button("Cancel", key=f"modal_cancel_dn_{file_id}_{shop_id}"):
                    del st.session_state[modal_key]
                    st.rerun()


def render_add_display_name_form(shop_id: int, file_id: int) -> None:
    """
    Render a form to create and link a display name to a file, account, and shop.
    
    Parameters:
        shop_id: ID of the shop
        file_id: ID of the file
    """
    st.markdown("---")
    st.markdown("**Add Display Name to File**")
    
    # Get file info
    from db_handler import get_file_info
    file_info = get_file_info(file_id)
    st.markdown(f"File: {file_info.get('filename', 'Unknown')}")
    
    # Get accounts for shop
    accounts_df = get_accounts_for_shop(shop_id)
    
    # Get accounts the file is already linked to in this shop
    from db_handler import get_accounts_for_file_in_shop
    file_linked_accounts_df = get_accounts_for_file_in_shop(file_id, shop_id)
    file_linked_account_ids = set(file_linked_accounts_df['account_id'].tolist()) if not file_linked_accounts_df.empty else set()
    
    if not accounts_df.empty:
        account_options = {
            f"{row['account_name']} (ID: {row['account_id']})": row['account_id']
            for _, row in accounts_df.iterrows()
        }
        
        # Determine which accounts to show in multiselect
        if len(file_linked_account_ids) == 0:
            # File not linked to any account - show all accounts
            available_accounts = account_options
            default_accounts = []
            if len(account_options) == 1:
                # Auto-select if only one account
                default_accounts = list(account_options.keys())
        else:
            # File already linked to some accounts - show only those
            available_accounts = {
                key: acc_id for key, acc_id in account_options.items()
                if acc_id in file_linked_account_ids
            }
            default_accounts = [
                key for key in available_accounts.keys()
            ]
        
        selected_account_keys = st.multiselect(
            "Select Account(s) to link display name to:",
            options=list(available_accounts.keys()),
            default=default_accounts,
            key=f"add_dn_account_{shop_id}_{file_id}"
        )
        
        selected_account_ids = [account_options[key] for key in selected_account_keys]
    else:
        st.warning("No accounts linked to this shop yet.")
        selected_account_ids = []
    
    # Text input for new display name
    new_display_name_input = st.text_input(
        "Enter new display name:",
        key=f"add_dn_input_{shop_id}_{file_id}"
    )
    
    # Confirm button
    if st.button("Confirm", key=f"confirm_add_dn_{shop_id}_{file_id}", type="primary"):
        if new_display_name_input.strip() and len(selected_account_ids) > 0:
            # Create display name (without file_id linkage)
            display_name_id = add_display_name(new_display_name_input.strip())
            
            # Link to selected accounts
            for acc_id in selected_account_ids:
                acc_name = [k for k, v in account_options.items() if v == acc_id][0]
                link_display_name_to_shop_account(
                    display_name_id=display_name_id,
                    shop_id=shop_id,
                    account_id=acc_id,
                    file_id=str(file_id)
                )
                st.success(f"Display name '{new_display_name_input}' linked to account '{acc_name}'")
        elif not new_display_name_input.strip():
            st.info("Enter a display name")
        elif len(selected_account_ids) == 0:
            st.info("Select at least one account")


def render_edit_display_name_form(shop_id: int, file_id: int, account_id: int = None) -> None:
    """
    Render a form to edit display names for an already-linked file.
    Allows user to:
    - Add a new display name
    - Edit existing display names
    - Remove display name links
    
    Parameters:
        shop_id: ID of the shop
        file_id: ID of the file
        account_id: ID of the account (for unique keys)
    """
    st.markdown("**Edit Display Name**")
    
    # Get file info
    from db_handler import get_file_info
    try:
        file_info = get_file_info(file_id)
        st.markdown(f"File: {file_info.get('filename', 'Unknown')}")
    except Exception as e:
        st.error(f"Error getting file info: {e}")
        import traceback
        st.code(traceback.format_exc())
        return
    
    # Get existing display names for this file in this shop
    from db_handler import get_display_names_for_file_in_shop
    try:
        existing_display_names_df = get_display_names_for_file_in_shop(file_id, shop_id)
    except Exception as e:
        st.error(f"Error getting display names: {e}")
        import traceback
        st.code(traceback.format_exc())
        return
    
    # Get accounts for shop (moved outside the if block to avoid UnboundLocalError)
    accounts_df = get_accounts_for_shop(shop_id)
    account_options = {
        f"{row['account_name']} (ID: {row['account_id']})": row['account_id']
        for _, row in accounts_df.iterrows()
    }
    
    if not existing_display_names_df.empty:
        st.subheader("Existing Display Names")
        
        # Display each existing display name with edit/remove options
        for _, row in existing_display_names_df.iterrows():
            dn_id = row['display_name_id']
            dn_name = row['display_name']
            
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    # Edit display name text input
                    new_name = st.text_input(
                        "Edit name:",
                        value=dn_name,
                        key=f"edit_dn_name_{shop_id}_{file_id}_{dn_id}"
                    )
                
                with col2:
                    st.space('small')
                    # Save button
                    if st.button("💾", key=f"save_dn_{shop_id}_{file_id}_{dn_id}"):
                        if new_name.strip() and new_name != dn_name:
                            from db_handler import update_display_name
                            if update_display_name(dn_id, new_name.strip()):
                                st.success(f"Display name updated to '{new_name}'")
                                st.rerun()
                
                with col3:
                    st.space('small')
                    # Remove button
                    if st.button("🗑️", key=f"remove_dn_{shop_id}_{file_id}_{dn_id}"):
                        from db_handler import remove_display_name_from_shop_file
                        if remove_display_name_from_shop_file(dn_id, shop_id, file_id):
                            st.success(f"Display name removed")
                            st.rerun()
    else:
        st.info("No display names linked to this file in this shop")
    
    # Add new display name section
    st.subheader("Add New Display Name")
    
    # Get accounts for the shop
    if not accounts_df.empty:
        selected_account_keys = st.multiselect(
            "Select Account(s):",
            options=list(account_options.keys()),
            key=f"edit_dn_account_select_{shop_id}_{file_id}_{account_id}"
        )
        
        selected_account_ids = [account_options[key] for key in selected_account_keys]
    else:
        st.warning("No accounts linked to this shop yet.")
        selected_account_ids = []
    
    # Text input for new display name
    new_display_name_input = st.text_input(
        "Enter new display name:",
        key=f"edit_dn_input_{shop_id}_{file_id}_{account_id}"
    )
    
    # Confirm button
    if st.button("Add Display Name", key=f"confirm_edit_dn_{shop_id}_{file_id}_{account_id}", type="primary"):
        if new_display_name_input.strip() and len(selected_account_ids) > 0:
            # Create display name
            display_name_id = add_display_name(new_display_name_input.strip())
            
            # Link to selected accounts
            for acc_id in selected_account_ids:
                acc_name = [k for k, v in account_options.items() if v == acc_id][0]
                link_display_name_to_shop_account(
                    display_name_id=display_name_id,
                    shop_id=shop_id,
                    account_id=acc_id,
                    file_id=str(file_id)
                )
                st.success(f"Display name '{new_display_name_input}' linked to account '{acc_name}'")
        elif not new_display_name_input.strip():
            st.info("Enter a display name")
        elif len(selected_account_ids) == 0:
            st.info("Select at least one account")

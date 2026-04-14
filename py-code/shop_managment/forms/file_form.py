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
    get_all_shops, get_accounts_for_shop
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
    
    Parameters:
        shop_id: ID of the shop to add files to
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
    
    # Get all shops
    all_shops = get_all_shops()
    
    # Shop selector
    shop_options = {f"{row['shop_name']} (ID: {row['shop_id']})": row['shop_id']
                   for _, row in all_shops.iterrows()}
    
    # Use session state to persist selections
    session_key_shop = f"selected_shop_{shop_id}_{idx}_{col_idx}{unique_key_suffix}"
    if session_key_shop not in st.session_state:
        st.session_state[session_key_shop] = list(shop_options.keys())[0] if shop_options else None
    
    selected_shop_name = st.selectbox(
        "Select Shop:",
        options=list(shop_options.keys()),
        format_func=lambda x: x,
        key=f"modal_shop_{shop_id}_{idx}_{col_idx}{unique_key_suffix}"
    )
    
    # Update session state if selection changed
    if selected_shop_name != st.session_state[session_key_shop]:
        st.session_state[session_key_shop] = selected_shop_name
    
    selected_shop_id = shop_options[st.session_state[session_key_shop]]
    
    # Get accounts for selected shop
    accounts_df = get_accounts_for_shop(selected_shop_id)
    
    if not accounts_df.empty:
        account_options = {f"{row['account_name']} (ID: {row['account_id']})": row['account_id']
                          for _, row in accounts_df.iterrows()}
        
        session_key_account = f"selected_account_{shop_id}_{idx}_{col_idx}{unique_key_suffix}"
        if session_key_account not in st.session_state:
            st.session_state[session_key_account] = list(account_options.keys())[0] if account_options else None
        
        selected_account_name = st.selectbox(
            "Select Account:",
            options=list(account_options.keys()),
            format_func=lambda x: x,
            key=f"modal_account_{shop_id}_{idx}_{col_idx}{unique_key_suffix}"
        )
        
        # Update session state if selection changed
        if selected_account_name != st.session_state[session_key_account]:
            st.session_state[session_key_account] = selected_account_name
        
        selected_account_id = account_options[st.session_state[session_key_account]]
    else:
        st.warning("No accounts linked to this shop yet.")
        selected_account_id = None
    
    # Action buttons
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("Confirm", key=f"confirm_add_{shop_id}_{idx}_{col_idx}{unique_key_suffix}", type="primary"):
            try:
                # Link file to shop
                if link_file_to_shop(selected_file_data['file_id'], selected_shop_id):
                    st.success(f"File linked to shop '{st.session_state[session_key_shop]}'")
                    
                    # Link file to account if selected
                    if selected_account_id:
                        # Link account to shop
                        link_account_to_shop(selected_shop_id, selected_account_id)
                        st.success(f"Account linked to shop")
                        
                        # Link file to account
                        if link_file_to_account(selected_file_data['file_id'], selected_account_id):
                            st.success(f"File also linked to account '{st.session_state[session_key_account]}'")
                        else:
                            st.warning(f"File already linked to account")
                
                # Clear selected file and selections
                del st.session_state[f"selected_file_{shop_id}"]
                del st.session_state[session_key_shop]
                if session_key_account in st.session_state:
                    del st.session_state[session_key_account]
            except Exception as e:
                st.error(f"Error adding file: {e}")
    
    with btn_col2:
        if st.button("Cancel", key=f"cancel_add_{shop_id}_{idx}_{col_idx}{unique_key_suffix}"):
            # Clear selected file and selections
            if f"selected_file_{shop_id}" in st.session_state:
                del st.session_state[f"selected_file_{shop_id}"]
            if session_key_shop in st.session_state:
                del st.session_state[session_key_shop]
            if session_key_account in st.session_state:
                del st.session_state[session_key_account]


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
        
        # Filter out already linked files
        filtered_df = filtered_df[~filtered_df['file_id'].isin(linked_ids)]
        
        if not filtered_df.empty:
            # Limit to first 24 results
            MAX_RESULTS = 24
            if len(filtered_df) > MAX_RESULTS:
                st.warning(f"Found {len(filtered_df)} matching files. Showing first {MAX_RESULTS}. Make your search more specific.")
                filtered_df = filtered_df.head(MAX_RESULTS)
            else:
                st.write(f"Found {len(filtered_df)} matching files")
            
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
                            # Extract just the filename without shop name
                            filename_display = row['filename'].split(' - ')[0] if ' - ' in row['filename'] else row['filename']
                            st.caption(filename_display)
                            
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


def show_file_selection_modal(shop_id: int) -> None:
    """
    Show a modal/dialog for selecting shop and account for the selected file.
    
    Parameters:
        shop_id: ID of the current shop (context)
    """
    from db_handler import get_all_shops, get_accounts_for_shop, link_file_to_shop, link_account_to_shop
    
    # Check if a file was selected
    if f"selected_file_{shop_id}" not in st.session_state:
        return
    
    selected_file = st.session_state[f"selected_file_{shop_id}"]
    
    # Create a modal-like interface using a container
    with st.container(border=True):
        st.markdown(f"**Add File to Shop & Account**")
        st.markdown(f"File: {selected_file['filename']}")
        
        # Show file preview if available
        if selected_file.get('preview_url'):
            full_preview_url = f"http://{{DB_HOST}}:8080{selected_file['preview_url'].replace('{prevsize}', 'x=200&y=200')}"
            st.image(full_preview_url, use_container_width=True)
        
        # Get all shops
        all_shops = get_all_shops()
        
        # Shop selector
        shop_options = {f"{row['shop_name']} (ID: {row['shop_id']})": row['shop_id']
                       for _, row in all_shops.iterrows()}
        
        # Use session state to persist selections
        if f"selected_shop_{shop_id}_modal" not in st.session_state:
            st.session_state[f"selected_shop_{shop_id}_modal"] = list(shop_options.keys())[0] if shop_options else None
        
        selected_shop_name = st.selectbox(
            "Select Shop:",
            options=list(shop_options.keys()),
            format_func=lambda x: x,
            key=f"modal_shop_{shop_id}_modal"
        )
        
        # Update session state if selection changed
        if selected_shop_name != st.session_state[f"selected_shop_{shop_id}_modal"]:
            st.session_state[f"selected_shop_{shop_id}_modal"] = selected_shop_name
            # Clear account selection when shop changes
            if f"selected_account_{shop_id}_modal" in st.session_state:
                del st.session_state[f"selected_account_{shop_id}_modal"]
        
        selected_shop_id = shop_options[st.session_state[f"selected_shop_{shop_id}_modal"]]
        
        # Get accounts for selected shop
        accounts_df = get_accounts_for_shop(selected_shop_id)
        
        if not accounts_df.empty:
            account_options = {f"{row['account_name']} (ID: {row['account_id']})": row['account_id']
                              for _, row in accounts_df.iterrows()}
            
            # Only get account options if not already in session state
            if f"selected_account_{shop_id}_modal" not in st.session_state:
                st.session_state[f"selected_account_{shop_id}_modal"] = list(account_options.keys())[0] if account_options else None
            
            selected_account_name = st.selectbox(
                "Select Account:",
                options=list(account_options.keys()),
                format_func=lambda x: x,
                key=f"modal_account_{shop_id}_modal"
            )
            
            # Update session state if selection changed
            if selected_account_name != st.session_state[f"selected_account_{shop_id}_modal"]:
                st.session_state[f"selected_account_{shop_id}_modal"] = selected_account_name
            
            selected_account_id = account_options[st.session_state[f"selected_account_{shop_id}_modal"]]
        else:
            st.warning("No accounts linked to this shop yet.")
            selected_account_id = None
        
        # Action buttons
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("Confirm", key=f"confirm_add_{shop_id}_modal", type="primary"):
                try:
                    # Link file to shop
                    if link_file_to_shop(selected_file['file_id'], selected_shop_id):
                        st.success(f"File linked to shop '{st.session_state[f"selected_shop_{shop_id}_modal"]}'")
                        
                        # Link file to account if selected
                        if selected_account_id:
                            # Link account to shop
                            link_account_to_shop(selected_shop_id, selected_account_id)
                            st.success(f"Account linked to shop")
                            
                            # Link file to account
                            if link_file_to_account(selected_file['file_id'], selected_account_id):
                                st.success(f"File also linked to account '{st.session_state[f"selected_account_{shop_id}_modal"]}'")
                            else:
                                st.warning(f"File already linked to account")
                        
                        # Clear selected file and selections
                        del st.session_state[f"selected_file_{shop_id}"]
                        del st.session_state[f"selected_shop_{shop_id}_modal"]
                        del st.session_state[f"selected_account_{shop_id}_modal"]
                except Exception as e:
                    st.error(f"Error adding file: {e}")
        
        with btn_col2:
            if st.button("Cancel", key=f"cancel_add_{shop_id}_modal"):
                # Clear selected file and selections
                if f"selected_file_{shop_id}" in st.session_state:
                    del st.session_state[f"selected_file_{shop_id}"]
                if f"selected_shop_{shop_id}_modal" in st.session_state:
                    del st.session_state[f"selected_shop_{shop_id}_modal"]
                if f"selected_account_{shop_id}_modal" in st.session_state:
                    del st.session_state[f"selected_account_{shop_id}_modal"]

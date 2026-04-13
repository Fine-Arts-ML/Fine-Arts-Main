"""
File table components for the Shop Management app.
"""

import streamlit as st
import pandas as pd
from db_handler import unlink_file_from_shop, get_files_for_shop, get_preview_image


def render_files_table(shop_id: int, total_files: int) -> None:
    """
    Render an interactive table for managing files linked to a shop.
    
    Parameters:
        shop_id: ID of the shop
        total_files: Total number of files linked to the shop
    """
    st.subheader(f"📁 Files for Shop ID: {shop_id}")
    st.markdown(f"**Total files linked:** {total_files}")
    
    # Add file section
    from forms.file_form import render_add_file_form
    with st.expander("➕ Add Files to Shop", expanded=False):
        render_add_file_form(shop_id)
    
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
        shop_id: ID of the shop
        total_files: Total number of files linked to the shop
    """
    st.subheader(f"📁 Files for Shop ID: {shop_id}")
    st.markdown(f"**Total files linked:** {total_files}")
    
    # Add file section
    from forms.file_form import render_add_file_form
    with st.expander("➕ Add Files to Shop", expanded=False):
        render_add_file_form(shop_id)


def render_file_row(file_data: dict, shop_id: int, is_infinite_scroll: bool = False, files_list: list = None) -> None:
    """
    Render a single file row with preview, filename, and delete button.
    
    Parameters:
        file_data: File data containing file_id, filename, and preview_url
        shop_id: ID of the shop
        is_infinite_scroll: If True, use infinite scroll delete logic
        files_list: Current files list for infinite scroll mode (for removal)
    """
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
        shop_id: ID of the shop
        total_files: Total number of files
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

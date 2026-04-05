"""
Streamlit App for Shop Management

This app allows users to manage shops and their linked files from the database.
"""

import streamlit as st
import pandas as pd

from db_handler import get_all_shops, get_file_count_for_shop
from ui_components import (
    render_shop_table,
    render_file_overview,
    render_file_list,
    render_shop_selector,
    render_account_table
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
    
    # Sidebar for shop selection
    with st.sidebar:
        st.header("Navigation")
        
        # Shop selector
        selected_shop_id = render_shop_selector(shops_df)
        
        # View mode selector
        view_mode = st.radio(
            "View Mode:",
            ["Table View", "Shop Detail View"],
            index=1 if selected_shop_id else 0,
            key="view_mode"
        )
        
        # File list mode selector
        if selected_shop_id:
            file_list_mode = st.radio(
                "File List Mode:",
                ["Pagination", "Infinite Scroll"],
                index=0,
                key="file_list_mode"
            )
    
    # Main content area
    if view_mode == "Table View":
        render_shop_table(shops_df)
    
    elif view_mode == "Shop Detail View" and selected_shop_id:
        # Get file count for selected shop
      
        total_files = get_file_count_for_shop(selected_shop_id)
       
        # Render file overview
        render_file_overview(selected_shop_id, total_files)

        # Render account table
        render_account_table(selected_shop_id, shops_df)
        
        # Render expandable file list
        with st.expander("📂 View Linked Files", expanded=False):
            if file_list_mode == "Pagination":
                render_paginated_file_list(selected_shop_id, total_files)
            else:
                render_infinite_scroll_file_list(selected_shop_id, total_files)
    
    elif view_mode == "Shop Detail View" and not selected_shop_id:
        st.info("Select a shop from the sidebar to view its details.")


# Helper functions for the detail view
def render_paginated_file_list(shop_id: int, total_files: int) -> None:
    """
    Render a paginated file list for a shop.
    
    Parameters:
        shop_id (int): ID of the shop
        total_files (int): Total number of files
    """
    from db_handler import get_files_for_shop, unlink_file_from_shop
    
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
                    if unlink_file_from_shop(row['file_id'], shop_id):
                        st.success("File removed")
                        st.rerun()
                    else:
                        st.error("Failed to remove file")
    else:
        st.info("No files on this page.")


def render_infinite_scroll_file_list(shop_id: int, total_files: int) -> None:
    """
    Render an infinite scroll file list for a shop.
    
    Parameters:
        shop_id (int): ID of the shop
        total_files (int): Total number of files
    """
    from db_handler import get_files_for_shop, unlink_file_from_shop
    
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
            col1, col2, col3 = st.columns([3, 5, 1])
            
            with col1:
                # Try to display preview
                preview_url = file_data.get('preview_url', '')
                if preview_url:
                    full_preview_url = f"http://{{DB_HOST}}:8080{preview_url.replace('{prevsize}', 'x=100&y=100')}"
                    st.image(full_preview_url, use_container_width=True)
                else:
                    st.write("📄")
            
            with col2:
                st.markdown(f"**{file_data['filename']}**")
            
            with col3:
                if st.button("🗑️", key=f"remove_file_inf_{file_data['file_id']}_{shop_id}"):
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
        
        # Show progress
        st.write(f"Loaded {loaded_count} of {total_files} files")
        
        if loaded_count < total_files:
            st.info("Click 'Load More' to load additional files...")
        else:
            st.success("All files loaded!")
    else:
        st.info(f"Click 'Load More' to load files (total: {total_files})")


if __name__ == "__main__":
    main()

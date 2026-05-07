"""
Streamlit App for Image Fingerprinting

This app allows users to upload an image, compute its perceptual hashes,
and compare them against all hashes in the database to find the closest matches.
"""

import streamlit as st
from io import BytesIO

from db_handler import get_all_hashes_from_db, get_tags_for_file
from hash_calc import compute_hashes, find_closest_matches
from webdav_handler import load_image_from_bytesio, get_webdav_url, load_image_from_webdav
from ui_components import render_match_image, render_match_details


def main():
    """Main Streamlit application function."""
    st.set_page_config(
        page_title="Image Fingerprinting",
        page_icon="🔍",
        layout="wide"
    )
    
    st.title("🔍 Image Fingerprinting")
    st.markdown("Upload an image to find the closest matches in the database.")
    
    # File uploader
    uploaded_file = st.file_uploader("Choose an image", type=['jpg', 'jpeg', 'png', 'tif', 'tiff'])
    
    if uploaded_file is not None:
        # Display uploaded image
        img_bytes = BytesIO(uploaded_file.read())
        img = load_image_from_bytesio(img_bytes)
        img = img.resize((1080, 1080))
        
        # Compute hashes
        with st.spinner("Computing hashes..."):
            query_whash, query_ahash, query_phash = compute_hashes(img)
        
        # Define default top_n value
        top_n = 5
        
        # Fetch all hashes from database
        with st.spinner("Fetching hashes from database..."):
            df_hashes = get_all_hashes_from_db()
        
        # Find closest matches
        with st.spinner("Finding closest matches..."):
            results = find_closest_matches(df_hashes, query_whash, query_ahash, query_phash, top_n=top_n)
        
        # Display results
        if len(results) > 0:
            # Settings row with hash type selector and results slider
            settings_col, hash_col = st.columns([1, 3])
            with settings_col:
                top_n = st.slider("Number of results to display", min_value=5, max_value=15, value=top_n)
            with hash_col:
                hash_type = st.radio(
                    "Select hash type to view:",
                    ["WHASH", "AHASH", "PHASH"],
                    horizontal=True,
                    index=2  # Default to PHASH (third option, 0-indexed)
                )
            
            # Map hash type to column name
            hash_col_map = {"WHASH": "whash_distance", "AHASH": "ahash_distance", "PHASH": "phash_distance"}
            selected_hash_col = hash_col_map[hash_type]
            
            # Re-fetch results with new top_n value
            results = find_closest_matches(df_hashes, query_whash, query_ahash, query_phash, top_n=top_n)
            results_sorted = results.sort_values(selected_hash_col).head(top_n)
            
            st.subheader(f"Top {top_n} Closest Matches")
            
            # Get environment variables for WebDAV
            import os
            from dotenv import load_dotenv
            load_dotenv()
            DB_HOST = os.getenv("DB_HOST")
            NC_ACC = os.getenv("NC_ACC")
            NC_PASS = os.getenv("NC_PASS")
            
            # Display uploaded image and best match side by side
            best_match = results_sorted.iloc[0]
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**Uploaded Image**")
                st.image(img, use_container_width=True)
                
                render_match_details(best_match, DB_HOST, get_tags_func=get_tags_for_file)
            
            with col2:
                st.markdown(f"**Best Match: {best_match['filename']}**")
                
                # Try to display the best match image
                success, error_msg = render_match_image(
                    best_match, DB_HOST, NC_ACC, NC_PASS,
                    hash_type, selected_hash_col, preview_size=1080,
                    get_tags_func=get_tags_for_file, render_details=True
                )
                
                if not success and error_msg:
                    st.caption(error_msg)
            
            # Display other matches in a 3x3 grid
            if len(results_sorted) > 1:
                st.markdown("### Other Matches")
                other_matches = results_sorted.iloc[1:10]  # Get next 9 matches
                
                # Calculate number of rows needed
                num_rows = (len(other_matches) + 2) // 3
                
                for row_idx in range(num_rows):
                    cols = st.columns(3)
                    start_idx = row_idx * 3
                    
                    for col_idx in range(3):
                        idx = start_idx + col_idx
                        if idx < len(other_matches):
                            match = other_matches.iloc[idx]
                            with cols[col_idx]:
                                st.markdown(f"**{match['filename']}**")
                                
                                # Try to display the match image
                                success, error_msg = render_match_image(
                                    match, DB_HOST, NC_ACC, NC_PASS,
                                    hash_type, selected_hash_col, preview_size=1080,
                                    get_tags_func=get_tags_for_file, render_details=True
                                )
                                
                                if not success and error_msg:
                                    st.caption(error_msg)
                                elif not success:
                                    st.caption("No preview available")
        else:
            st.warning("No matches found!")
        
    
    else:
        st.info("👆 Upload an image to get started")


if __name__ == "__main__":
    main()

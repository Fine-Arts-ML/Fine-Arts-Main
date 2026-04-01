"""
Streamlit App for Image Fingerprinting

This app allows users to upload an image, compute its perceptual hashes,
and compare them against all hashes in the database to find the closest matches.
"""

import streamlit as st
from PIL import Image
import imagehash
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table, select
import pandas as pd
from io import BytesIO


def create_db_connection():
    """
    Create a database connection using environment variables.
    
    Returns:
        sqlalchemy.engine.Engine: Database engine connection
    """
    load_dotenv()
    DB_HOST = os.getenv("DB_HOST")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    engine = create_engine(
        f'postgresql+pg8000://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}'
    )
    return engine


def compute_hashes(img):
    """
    Compute perceptual hashes for an image.
    Images are resized to 1080x1080 to match the database hashes.
    
    Parameters:
        img (PIL.Image): Input image
    
    Returns:
        tuple: (whash, ahash, phash) hash strings
    """
    # Resize to 1080x1080 to match database hashes
    img = img.resize((1080, 1080))
    whash = imagehash.whash(img)
    ahash = imagehash.average_hash(img)
    phash = imagehash.phash(img)
    return str(whash), str(ahash), str(phash)


def hamming_distance(hash1, hash2):
    """
    Calculate the Hamming distance between two hash strings.
    
    Parameters:
        hash1 (str): First hash string
        hash2 (str): Second hash string
    
    Returns:
        int: Hamming distance (number of differing bits)
    """
    # Convert hex strings to integers and XOR, then count set bits
    int1 = int(hash1, 16)
    int2 = int(hash2, 16)
    xor_result = int1 ^ int2
    return bin(xor_result).count('1')


def get_all_hashes_from_db():
    """
    Fetch all hashes from the bre_hashes table along with file info.
    
    Returns:
        pandas.DataFrame: DataFrame with fileid, filename, and hash columns
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the tables
    Hash_table = Table('bre_hashes', metadata, autoload_with=engine)
    Index_table = Table('bre_advance_index', metadata, autoload_with=engine)
    
    # Query all data with file info using INNER JOIN on fileid = id
    query = select(
        Hash_table.c.id,
        Hash_table.c.w_hash,
        Hash_table.c.a_hash,
        Hash_table.c.p_hash,
        Index_table.c.name.label('filename'),
        Index_table.c.preview_url.label('preview_url'),
        Index_table.c.path.label('webdav_path')
    ).join(
        Index_table,
        Hash_table.c.id == Index_table.c.fileid
    )
    with engine.connect() as connection:
        df = pd.DataFrame(connection.execute(query).fetchall())
        df.columns = ['id', 'w_hash', 'a_hash', 'p_hash', 'filename', 'preview_url', 'webdav_path']
    
    return df


def find_closest_matches(df_hashes, query_whash, query_ahash, query_phash, top_n=10):
    """
    Find the closest matches based on hash similarity.
    
    Parameters:
        df_hashes (pandas.DataFrame): DataFrame with hash columns, filename, and preview_url
        query_whash (str): Query whash
        query_ahash (str): Query ahash
        query_phash (str): Query phash
        top_n (int): Number of top results to return
    
    Returns:
        pandas.DataFrame: Top N closest matches with distances
    """
    results = []
    
    for idx, row in df_hashes.iterrows():
        # Calculate Hamming distances for each hash type
        whash_dist = hamming_distance(query_whash, row['w_hash']) if pd.notna(row['w_hash']) else float('inf')
        ahash_dist = hamming_distance(query_ahash, row['a_hash']) if pd.notna(row['a_hash']) else float('inf')
        phash_dist = hamming_distance(query_phash, row['p_hash']) if pd.notna(row['p_hash']) else float('inf')
        
        # Use the minimum distance as the overall similarity score
        min_distance = min(whash_dist, ahash_dist, phash_dist)
        
        # Determine which hash type has the minimum distance
        distances = [whash_dist, ahash_dist, phash_dist]
        best_hash_type = distances.index(min_distance)
        hash_types = ['whash', 'ahash', 'phash']
        if min_distance == float('inf'):
            best_hash_type = 'none'
        else:
            best_hash_type = hash_types[best_hash_type]
        
        results.append({
            'fileid': row['id'],
            'filename': row['filename'],
            'preview_url': row['preview_url'],
            'w_hash': row['w_hash'],
            'a_hash': row['a_hash'],
            'p_hash': row['p_hash'],
            'whash_distance': whash_dist,
            'ahash_distance': ahash_dist,
            'phash_distance': phash_dist,
            'min_distance': min_distance,
            'best_hash_type': best_hash_type
        })
    
    # Convert to DataFrame and sort by minimum distance
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('min_distance').head(top_n)
    
    return results_df


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
    uploaded_file = st.file_uploader("Choose an image", type=['jpg', 'jpeg', 'png'])
    
    if uploaded_file is not None:
        # Display uploaded image
        img = Image.open(uploaded_file)
        img = img.resize((300, 300))
        
        # Compute hashes
        with st.spinner("Computing hashes..."):
            query_whash, query_ahash, query_phash = compute_hashes(img)
        
        # Define default top_n value
        top_n = 10
        
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
                    horizontal=True
                )
            
            # Map hash type to column name
            hash_col_map = {"WHASH": "whash_distance", "AHASH": "ahash_distance", "PHASH": "phash_distance"}
            selected_hash_col = hash_col_map[hash_type]
            
            # Re-fetch results with new top_n value
            results = find_closest_matches(df_hashes, query_whash, query_ahash, query_phash, top_n=top_n)
            results_sorted = results.sort_values(selected_hash_col).head(top_n)
            
            st.subheader(f"Top {top_n} Closest Matches")
            
            # Display uploaded image and best match side by side
            best_match = results_sorted.iloc[0]
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**Uploaded Image**")
                st.image(img, use_container_width=True)
                
                with st.expander("Details", expanded=False):
                    st.metric(f"{hash_type} Distance", best_match[selected_hash_col])
                    st.metric("Overall Distance", best_match['min_distance'])
                    st.metric("Best Hash Type", best_match['best_hash_type'])
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.code(f"WHASH: {best_match['w_hash']}")
                    with col_b:
                        st.code(f"AHASH: {best_match['a_hash']}")
                    with col_c:
                        st.code(f"PHASH: {best_match['p_hash']}")
            
            with col2:
                st.markdown(f"**Best Match: {best_match['filename']}**")
                
                # Try to display the best match image
                if pd.notna(best_match['preview_url']):
                    try:
                        import requests
                        from requests.auth import HTTPBasicAuth
                        
                        DB_HOST = os.getenv("DB_HOST")
                        NC_ACC = os.getenv("NC_ACC")
                        NC_PASS = os.getenv("NC_PASS")
                        
                        preview_url = best_match['preview_url']
                        preview_url = f'http://{DB_HOST}:8080{preview_url.replace("{prevsize}", "x=300&y=300")}'
                        
                        response = requests.get(preview_url, auth=HTTPBasicAuth(NC_ACC, NC_PASS), stream=True)
                        if response.status_code == 200:
                            file_in_memory = BytesIO()
                            for chunk in response.iter_content(chunk_size=1024):
                                if chunk:
                                    file_in_memory.write(chunk)
                            file_in_memory.seek(0)
                            match_img = Image.open(file_in_memory)
                            match_img = match_img.resize((1080, 1080))
                            st.image(match_img, use_container_width=True)
                            
                            with st.expander("Details", expanded=False):
                                st.metric(f"{hash_type} Distance", best_match[selected_hash_col])
                                st.metric("Overall Distance", best_match['min_distance'])
                                st.metric("Best Hash Type", best_match['best_hash_type'])
                                col_a, col_b, col_c = st.columns(3)
                                with col_a:
                                    st.code(f"WHASH: {best_match['w_hash']}")
                                with col_b:
                                    st.code(f"AHASH: {best_match['a_hash']}")
                                with col_c:
                                    st.code(f"PHASH: {best_match['p_hash']}")
                    except Exception as e:
                        st.caption(f"Could not load image: {e}")
            
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
                                if pd.notna(match['preview_url']):
                                    try:
                                        import requests
                                        from requests.auth import HTTPBasicAuth
                                        
                                        DB_HOST = os.getenv("DB_HOST")
                                        NC_ACC = os.getenv("NC_ACC")
                                        NC_PASS = os.getenv("NC_PASS")
                                        
                                        preview_url = match['preview_url']
                                        preview_url = f'http://{DB_HOST}:8080{preview_url.replace("{prevsize}", "x=150&y=150")}'
                                        
                                        response = requests.get(preview_url, auth=HTTPBasicAuth(NC_ACC, NC_PASS), stream=True)
                                        
                                        if response.status_code == 200:
                                            # Preview available, use it
                                            file_in_memory = BytesIO()
                                            for chunk in response.iter_content(chunk_size=1024):
                                                if chunk:
                                                    file_in_memory.write(chunk)
                                            file_in_memory.seek(0)
                                            match_img = Image.open(file_in_memory)
                                            match_img = match_img.resize((1080, 1080))
                                            st.image(match_img, use_container_width=True)
                                            
                                            with st.expander("Details", expanded=False):
                                                st.metric(f"{hash_type} Distance", match[selected_hash_col])
                                                st.metric("Overall Distance", match['min_distance'])
                                                st.metric("Best Hash Type", match['best_hash_type'])
                                                col_a, col_b, col_c = st.columns(3)
                                                with col_a:
                                                    st.code(f"WHASH: {match['w_hash']}")
                                                with col_b:
                                                    st.code(f"AHASH: {match['a_hash']}")
                                                with col_c:
                                                    st.code(f"PHASH: {match['p_hash']}")
                                        elif response.status_code == 404:
                                            # No preview available, fall back to direct HTTP GET from WebDAV
                                            # Use the webdav_path column from the database
                                            webdav_path = match.get('webdav_path')
                                            
                                            if webdav_path is not None and webdav_path != '':
                                                # webdav_path is like: /Bre/Artwork/AI_art/bearbeitet/klimt%20bruecke2.tiff
                                                # Full URL: http://{DB_HOST}:8080/remote.php/dav/files/{NC_ACC}{webdav_path}
                                                webdav_file_url = f'http://{DB_HOST}:8080/remote.php/dav/files/{NC_ACC}{webdav_path}'
                                            else:
                                                # Fallback: construct from preview_url
                                                preview_url = match['preview_url']
                                                # Remove the ?{prevsize} part if present
                                                webdav_path = preview_url.split('?')[0]
                                                webdav_file_url = f'http://{DB_HOST}:8080{webdav_path}'
                                            
                                            webdav_response = requests.get(
                                                webdav_file_url,
                                                auth=HTTPBasicAuth(NC_ACC, NC_PASS),
                                                stream=True
                                            )
                                            if webdav_response.status_code == 200:
                                                file_in_memory = BytesIO()
                                                for chunk in webdav_response.iter_content(chunk_size=1024):
                                                    if chunk:
                                                        file_in_memory.write(chunk)
                                                file_in_memory.seek(0)
                                                source_img = Image.open(file_in_memory)
                                                match_img = source_img.resize((1080, 1080))
                                                st.image(match_img, use_container_width=True)
                                                
                                                with st.expander("Details", expanded=False):
                                                    st.metric(f"{hash_type} Distance", match[selected_hash_col])
                                                    st.metric("Overall Distance", match['min_distance'])
                                                    st.metric("Best Hash Type", match['best_hash_type'])
                                                    col_a, col_b, col_c = st.columns(3)
                                                    with col_a:
                                                        st.code(f"WHASH: {match['w_hash']}")
                                                    with col_b:
                                                        st.code(f"AHASH: {match['a_hash']}")
                                                    with col_c:
                                                        st.code(f"PHASH: {match['p_hash']}")
                                            else:
                                                st.caption(f"Could not load image from WebDAV. Status code: {webdav_response.status_code}")
                                                st.caption(f"WebDAV URL: {webdav_file_url}")
                                    except Exception as e:
                                        st.caption(f"Could not load image: {e}")
                                else:
                                    st.caption("No preview available")
        else:
            st.warning("No matches found!")
        
        # Add a note about Hamming distance
        st.markdown("""
        ---
        **About Hamming Distance:**
        - Lower values indicate closer matches
        - Distance of 0 means identical hashes
        - Distance of 1-2 typically indicates very similar images
        - Distance of 3-5 may indicate similar but not identical images
        """)
    
    else:
        st.info("👆 Upload an image to get started")


if __name__ == "__main__":
    main()

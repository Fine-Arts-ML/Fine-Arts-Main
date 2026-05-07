"""
UI components module for the Image Fingerprinting app.
Provides helper functions for rendering UI elements.
"""

import streamlit as st
import pandas as pd
from db_handler import get_tags_for_file


def render_hash_details(match, hash_type, selected_hash_col):
    """
    Render hash details in an expander.
    
    Parameters:
        match (dict): Match data dictionary
        hash_type (str): Selected hash type (WHASH, AHASH, PHASH)
        selected_hash_col (str): Column name for the selected hash type
    """
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


def render_match_image(match, db_host, nc_acc, nc_pass, hash_type, selected_hash_col, preview_size=300, get_tags_func=None, render_details=True):
    """
    Render a match image with preview and WebDAV fallback.
    
    Parameters:
        match (dict): Match data dictionary
        db_host (str): Database host
        nc_acc (str): Nextcloud account username
        nc_pass (str): Nextcloud account password
        hash_type (str): Selected hash type (WHASH, AHASH, PHASH)
        selected_hash_col (str): Column name for the selected hash type
        preview_size (int): Preview size (default: 300)
        get_tags_func (callable): Optional function to fetch tags for a file
        render_details (bool): Whether to render the Details expander (default: True)
    
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    import requests
    from requests.auth import HTTPBasicAuth
    from io import BytesIO
    from urllib.parse import quote
    
    if pd.notna(match['preview_url']):
        try:
            preview_url = match['preview_url']
            preview_url = f'http://{db_host}:8080{preview_url.replace("{prevsize}", f"x={preview_size}&y={preview_size}")}'
            
            response = requests.get(preview_url, auth=HTTPBasicAuth(nc_acc, nc_pass), stream=True)
            
            if response.status_code == 200:
                # Preview available, use it
                file_in_memory = BytesIO()
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        file_in_memory.write(chunk)
                file_in_memory.seek(0)
                
                from PIL import Image
                match_img = Image.open(file_in_memory)
                
                # Handle multi-page TIFFs
                if hasattr(match_img, 'n_frames') and match_img.n_frames > 1:
                    match_img.seek(0)
                match_img.load()
                
                # Convert to RGB
                if match_img.mode in ('RGBA', 'P', 'LA', 'CMYK', 'L'):
                    match_img = match_img.convert('RGB')
                elif match_img.mode != 'RGB':
                    match_img = match_img.convert('RGB')
                
                match_img = match_img.resize((1080, 1080))
                st.image(match_img, use_container_width=True)
                if render_details:
                    render_match_details(match, db_host, get_tags_func)
                return True, None
            elif response.status_code == 404:
                # Fall back to WebDAV
                webdav_path = match.get('webdav_path')
                if webdav_path:
                    # Ensure webdav_path starts with /
                    if not webdav_path.startswith('/'):
                        webdav_path = '/' + webdav_path
                    
                    nc_acc = nc_acc if nc_acc else ''
                    webdav_base_url = f'http://{db_host}:8080/remote.php/dav/files/{nc_acc}/'
                    webdav_file_url = f'{webdav_base_url}{quote(webdav_path, safe="/")}'
                    
                    webdav_response = requests.get(
                        webdav_file_url,
                        auth=HTTPBasicAuth(nc_acc, nc_pass),
                        stream=True
                    )
                    
                    if webdav_response.status_code == 200:
                        file_in_memory = BytesIO()
                        for chunk in webdav_response.iter_content(chunk_size=1024):
                            if chunk:
                                file_in_memory.write(chunk)
                        file_in_memory.seek(0)
                        
                        source_img = Image.open(file_in_memory)
                        
                        # Handle multi-page TIFFs
                        if hasattr(source_img, 'n_frames') and source_img.n_frames > 1:
                            source_img.seek(0)
                        source_img.load()
                        
                        # Convert to RGB
                        if source_img.mode in ('RGBA', 'P', 'LA', 'CMYK', 'L'):
                            source_img = source_img.convert('RGB')
                        elif source_img.mode != 'RGB':
                            source_img = source_img.convert('RGB')
                        
                        match_img = source_img.resize((1080, 1080))
                        st.image(match_img, use_container_width=True)
                        if render_details:
                            render_match_details(match, db_host, get_tags_func)
                        return True, None
                    else:
                        return False, f"Could not load image from WebDAV. Status code: {webdav_response.status_code}"
        except Exception as e:
            return False, str(e)
    
    return False, "No preview available"


def render_match_details(match, db_host, get_tags_func=None):
    """
    Render the Details expander with Tags and Download button.
    
    Parameters:
        match (dict): Match data dictionary
        db_host (str): Database host
        get_tags_func (callable): Optional function to fetch tags for a file (default: get_tags_for_file)
    """
    import re
    if get_tags_func is None:
        get_tags_func = get_tags_for_file
    with st.expander("Details", expanded=False):
        with st.expander("Tags", icon=':material/crossword:'):
            tags = get_tags_func(match['fileid'])
            st.write(tags if tags else "No tags")
        file_path = re.sub(r'/[^/]*$', '', match['webdav_path'])
        download_url = f'http://{db_host}:8080/apps/files/files/{match["fileid"]}?dir={file_path}&editing=false&openfile=true'
        st.link_button(
            url=download_url,
            type="primary",
            icon=":material/document_search:",
            label="Download Image",
            use_container_width=True
        )

"""
WebDAV handler module for the Image Fingerprinting app.
Provides functions for loading images from WebDAV and BytesIO.
"""

from PIL import Image
from io import BytesIO
from urllib.parse import quote
import requests
from requests.auth import HTTPBasicAuth


# Enable TIFF support (both uppercase and lowercase extensions)
Image.registered_extensions()['.TIF'] = 'TIFF'
Image.registered_extensions()['.TIFF'] = 'TIFF'
Image.registered_extensions()['.tif'] = 'TIFF'
Image.registered_extensions()['.tiff'] = 'TIFF'


def load_image_from_bytesio(file_bytes):
    """
    Load an image from BytesIO, handling TIFF files properly.
    
    Parameters:
        file_bytes (BytesIO): BytesIO object containing image data
    
    Returns:
        PIL.Image: Loaded image
    """
    # Seek to beginning to ensure we read from start
    file_bytes.seek(0)
    
    # Read all data to ensure it's complete
    data = file_bytes.read()
    file_bytes = BytesIO(data)
    
    # Open image
    img = Image.open(file_bytes)
    
    # Handle multi-page TIFFs - load only the first frame
    if hasattr(img, 'n_frames') and img.n_frames > 1:
        img.seek(0)  # Go to first frame
    
    # Force load the image data
    img.load()
    
    # Convert to RGB if necessary (handles RGBA, P, LA, CMYK, etc.)
    if img.mode in ('RGBA', 'P', 'LA', 'CMYK', 'L'):
        img = img.convert('RGB')
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    return img


def get_preview_url(preview_url, db_host, size=300):
    """
    Construct a preview URL with the specified size.
    
    Parameters:
        preview_url (str): Original preview URL from database
        db_host (str): Database host
        size (int): Preview size (default: 300)
    
    Returns:
        str: Constructed preview URL
    """
    return f'http://{db_host}:8080{preview_url.replace("{prevsize}", f"x={size}&y={size}")}'


def get_webdav_url(db_host, nc_acc, webdav_path):
    """
    Construct a WebDAV URL from the database path.
    
    Parameters:
        db_host (str): Database host
        nc_acc (str): Nextcloud account username
        webdav_path (str): Path from database
    
    Returns:
        str: Constructed WebDAV URL
    """
    # Ensure webdav_path starts with / for proper URL construction
    if webdav_path and not webdav_path.startswith('/'):
        webdav_path = '/' + webdav_path
    
    # Ensure NC_ACC is not None
    nc_acc = nc_acc if nc_acc else ''
    webdav_base_url = f'http://{db_host}:8080/remote.php/dav/files/{nc_acc}/'
    
    # URL-encode the path to handle spaces and special characters
    webdav_file_url = f'{webdav_base_url}{quote(webdav_path, safe="/")}' if webdav_path else webdav_base_url
    
    return webdav_file_url


def load_image_from_webdav(webdav_url, nc_acc, nc_pass):
    """
    Load an image from a WebDAV URL.
    
    Parameters:
        webdav_url (str): WebDAV URL
        nc_acc (str): Nextcloud account username
        nc_pass (str): Nextcloud account password
    
    Returns:
        PIL.Image: Loaded image or None if failed
    """
    try:
        response = requests.get(
            webdav_url,
            auth=HTTPBasicAuth(nc_acc, nc_pass),
            stream=True
        )
        
        if response.status_code == 200:
            file_in_memory = BytesIO()
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file_in_memory.write(chunk)
            file_in_memory.seek(0)
            return load_image_from_bytesio(file_in_memory)
        else:
            return None, response.status_code
    except Exception as e:
        return None, str(e)

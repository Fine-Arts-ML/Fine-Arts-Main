"""
Image Hashing Script for Fingerprinting

This script processes images from a database, generates perceptual hashes (whash, ahash, phash),
and stores them in the bre_hashes table. It processes images in chunks of 10 and uploads
after each chunk is completed, with a progress bar using tqdm.
"""

from PIL import Image
import imagehash
import os
import requests
from requests.auth import HTTPBasicAuth
from io import BytesIO
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table, select, insert
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
from tqdm import tqdm


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


def get_preview_index(preview_size, db_host):
    """
    Get preview index from bre_advance_index, filtering out already-hashed files.
    
    Parameters:
        preview_size (int): Size for preview URL generation
        db_host (str): Database host for URL construction
    
    Returns:
        pandas.DataFrame: Filtered DataFrame with only new file_ids not in bre_hashes table
    """
    engine = create_db_connection()
    metadata = MetaData()

    # Reflect the tables
    Index_table = Table('bre_advance_index', metadata, autoload_with=engine)
    Hash_table = Table('bre_hashes', metadata, autoload_with=engine)
    
    # Get all existing file_ids from the bre_hashes table
    with engine.connect() as connection:
        existing_query = select(Hash_table.c.id)
        existing_ids = set(connection.execute(existing_query).fetchall())
        existing_ids = {row[0] for row in existing_ids}
    
    # Query the advance index table
    query = select(Index_table)
    with engine.connect() as connection:
        df_index = pd.DataFrame(connection.execute(query).fetchall())
        # Set column names
        df_index.columns = Index_table.columns.keys()
    
    # Filter to only include file_ids that don't exist in bre_hashes
    # Assuming 'fileid' column contains the file IDs
    df_index['fileid'] = df_index['fileid'].astype(str)
    df_index = df_index[~df_index['fileid'].isin(existing_ids)]
    
    # Update preview URLs
    for index, row in df_index.iterrows():
        prev_url = row['preview_url']
        prev_url = f'http://{db_host}:8080{prev_url.replace("{prevsize}", f"x={preview_size}&y={preview_size}")}'
        df_index.loc[index, 'preview_url'] = prev_url
    
    print(f"Filtered index: {len(df_index)} new files out of total")
    return df_index


def get_images(file_id, file_path, webdav_path=None, preview_size=1080):
    """
    Download an image from a preview URL or fall back to WebDAV.
    Uses an in-memory cache to avoid re-downloading the same image.
    
    Parameters:
        file_id (str): Unique identifier for the file
        file_path (str): URL to the preview image
        webdav_path (str, optional): Path to the original file via WebDAV
        preview_size (int): Target size for image resizing (default: 1080)
    
    Returns:
        tuple: (file_id, PIL.Image or None)
    """
    DB_HOST = os.getenv("DB_HOST")
    NC_ACC = os.getenv("NC_ACC")
    NC_PASS = os.getenv("NC_PASS")

    # Check cache first
    if file_id in image_cache:
        return file_id, image_cache[file_id]

    # Send a GET request to download the preview
    response = requests.get(file_path, auth=HTTPBasicAuth(NC_ACC, NC_PASS), stream=True)
  
    try:
        if response.status_code == 200:
            file_in_memory = BytesIO()
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file_in_memory.write(chunk)
            file_in_memory.seek(0)
            img = Image.open(file_in_memory)
            img = img.resize((preview_size, preview_size))
            image_cache[file_id] = img  # Cache the image
            return file_id, img
        elif response.status_code == 404:
            #  print(f"No preview available for file: {file_id}, loading original via WebDAV...")
            # Fall back to WebDAV if webdav_path is provided
            if webdav_path is not None:
                webdav_base_url = f'http://{DB_HOST}:8080/remote.php/dav/files/{NC_ACC}'
                webdav_file_url = f'{webdav_base_url}{webdav_path}'
                
                try:
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
                        img = source_img.resize((preview_size, preview_size))
                        image_cache[file_id] = img  # Cache the image
                        return file_id, img
                    else:
                        print(f"Failed to download via WebDAV. Status code: {webdav_response.status_code}")
                except Exception as e:
                    print(f"Error downloading via WebDAV for file {file_id}: {e}")
            return file_id, None
        else:
            print(f"Failed to download file. Status code: {response.status_code}")
            print(response.text)
            return file_id, None
    except Exception as e:
        print(f"Error downloading file {file_id}: {e}")
        return file_id, None


def push_index(df_index):
    """
    Push and append data from df_index to the bre_hashes table in PostgreSQL.
    
    Parameters:
        df_index (pandas.DataFrame): DataFrame with columns: 'fileid', 'w_hash', 'a_hash', 'p_hash'
    
    Returns:
        int: Number of rows inserted
    """
    engine = create_db_connection()
    metadata = MetaData()

    # Reflect the table
    Index_table = Table('bre_hashes', metadata, autoload_with=engine)
    
    # Rename DataFrame columns to match database columns
    df_mapped = df_index.rename(columns={'fileid': 'id'})
    
    # Convert DataFrame to list of dictionaries for bulk insert
    data_to_insert = df_mapped.to_dict('records')
    
    # Insert data into the database
    with engine.connect() as connection:
        if data_to_insert:  # Only insert if there's data
            connection.execute(insert(Index_table), data_to_insert)
            connection.commit()
    
    return len(data_to_insert)


def process_in_chunks(df, chunk_size=10, preview_size=1080):
    """
    Process the DataFrame in chunks, computing hashes and uploading after each chunk.
    
    Parameters:
        df (pandas.DataFrame): DataFrame containing file information
        chunk_size (int): Number of rows to process per chunk (default: 10)
        preview_size (int): Target size for image resizing (default: 540)
    
    Returns:
        int: Total number of rows successfully processed
    """
    global image_cache
    image_cache = {}  # Reset cache for new run
    
    total_rows = len(df)
    total_processed = 0
    
    # Create progress bar
    with tqdm(total=total_rows, desc="Processing images", unit="file") as pbar:
        # Process in chunks
        for start_idx in range(0, total_rows, chunk_size):
            end_idx = min(start_idx + chunk_size, total_rows)
            chunk_df = df.iloc[start_idx:end_idx].copy()
            
 
             
            # Process each row in the chunk
            for idx, row in chunk_df.iterrows():
                file_id = row['fileid']
                file_path = row['preview_url']
                webdav_path = row.get('path')  # WebDAV path to original file
                
                file_id, img = get_images(file_id, file_path, webdav_path, preview_size)
                
                if img is None:
                    print(f"Failed to download file: {file_id}")
                    # Keep NaN values for failed downloads
                    chunk_df.loc[idx, "w_hash"] = None
                    chunk_df.loc[idx, "a_hash"] = None
                    chunk_df.loc[idx, "p_hash"] = None
                else:
                    whash = imagehash.whash(img)
                    ahash = imagehash.average_hash(img)
                    phash = imagehash.phash(img)
                    chunk_df.loc[idx, "w_hash"] = str(whash)
                    chunk_df.loc[idx, "a_hash"] = str(ahash)
                    chunk_df.loc[idx, "p_hash"] = str(phash)
                
                pbar.update(1)
            
            # Drop columns before upload
            chunk_to_upload = chunk_df.drop(columns=['path', 'preview_url', 'id', 'name'], errors='ignore')
            
            # Upload chunk to database
            push_index(chunk_to_upload)
            total_processed += len(chunk_to_upload)
    
    return total_processed


def select_preview_size():
    """
    Prompt user to select preview size.
    
    Returns:
        int: Selected preview size (540 or 1080)
    """
    print("\n=== Image Hashing Script ===")
    print("Select preview size:")
    print("1. 540x540 (faster, lower resolution)")
    print("2. 1080x1080 (slower, higher resolution)")
    
    while True:
        choice = input("\nEnter your choice (1 or 2): ").strip()
        if choice == '1':
            return 540
        elif choice == '2':
            return 1080
        else:
            print("Invalid choice. Please enter 1 or 2.")


def main():
    """
    Main function to orchestrate the image hashing process.
    """
    load_dotenv()
    db_host = os.getenv("DB_HOST")
    
    # Let user select preview size
    preview_size = select_preview_size()
    print(f"\nSelected preview size: {preview_size}x{preview_size}")
    
    # Get the index of files to process
    df_index = get_preview_index(preview_size=preview_size, db_host=db_host)
    
    if len(df_index) == 0:
        print("No new files to process.")
        return
    
    print(f"Total files to process: {len(df_index)}")
    
    # Process in chunks of 10
    total_processed = process_in_chunks(df_index, chunk_size=10, preview_size=preview_size)
    
    print(f"\n=== Processing Complete ===")
    print(f"Total files processed: {total_processed}")


if __name__ == "__main__":
    main()

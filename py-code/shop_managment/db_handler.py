"""
Database handler for the Shop Management app.
Provides functions for database connections and queries.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table, select, insert, delete, update, func
from sqlalchemy.types import Integer
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from io import BytesIO
from PIL import Image


def create_db_connection():
    """
    Create a database connection using environment variables.
    
    Returns:
        sqlalchemy.engine.Engine: Database engine connection with connection pooling
    """
    load_dotenv()
    DB_HOST = os.getenv("DB_HOST")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    engine = create_engine(
        f'postgresql+pg8000://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}',
        pool_size=5,
        max_overflow=10,
        pool_recycle=3600,
        pool_pre_ping=True
    )
    return engine


# ============================================================================
# GENERIC CRUD FUNCTIONS
# ============================================================================

def get_all_entities(table_name: str, id_column: str, name_column: str) -> pd.DataFrame:
    """
    Generic function to fetch all entities from a table.
    
    Parameters:
        table_name (str): Name of the database table
        id_column (str): Name of the ID column
        name_column (str): Name of the name column
        
    Returns:
        pd.DataFrame: DataFrame with id and name columns
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the table
    table = Table(table_name, metadata, autoload_with=engine)
    
    # Get column references
    id_col = table.c[id_column]
    name_col = table.c[name_column]
    
    # Build column names for DataFrame
    df_columns = [id_column, name_column]
    
    query = select(id_col, name_col)
    
    with engine.begin() as connection:
        result = connection.execute(query)
        rows = result.fetchall()
    
    if rows:
        df = pd.DataFrame(rows, columns=df_columns)
    else:
        df = pd.DataFrame(columns=df_columns)
    return df


def add_entity(table_name: str, id_column: str, name_column: str, name_value: str) -> int:
    """
    Generic function to add a new entity to a table.
    
    Parameters:
        table_name (str): Name of the database table
        id_column (str): Name of the ID column
        name_column (str): Name of the name column
        name_value (str): Name value to add
        
    Returns:
        int: The ID of the added/existing entity
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the table
    table = Table(table_name, metadata, autoload_with=engine)
    
    # Get column references
    id_col = table.c[id_column]
    name_col = table.c[name_column]
    
    with engine.begin() as connection:
        # Get max ID
        result = connection.execute(select(func.max(id_col)))
        max_id = result.scalar() or 0
        
        # Check if entity already exists by name
        result = connection.execute(select(name_col).where(name_col == name_value))
        existing = result.scalar()
        
        if existing:
            # Entity already exists, return the actual id of the existing entity
            result = connection.execute(select(id_col).where(name_col == name_value))
            return result.scalar()
        else:
            # Entity is new, find the smallest available ID (reuse gaps)
            # Get all existing IDs
            result = connection.execute(select(id_col))
            existing_ids = set(row[0] for row in result.fetchall())
            
            # Find the first missing ID starting from 1
            new_id = 1
            while new_id in existing_ids:
                new_id += 1
            
            # If no gaps found, use max_id + 1
            if new_id > max_id:
                new_id = max_id + 1
            
            values = {id_column: new_id, name_column: name_value}
            connection.execute(insert(table).values(**values))
            return new_id


def remove_entity(table_name: str, id_column: str, id_value: int) -> bool:
    """
    Generic function to remove an entity from a table.
    
    Parameters:
        table_name (str): Name of the database table
        id_column (str): Name of the ID column
        id_value (int): ID value to remove
        
    Returns:
        bool: True if entity was removed, False if not found
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the table
    table = Table(table_name, metadata, autoload_with=engine)
    
    # Get column reference
    id_col = table.c[id_column]
    
    # Delete entity
    with engine.begin() as connection:
        result = connection.execute(delete(table).where(id_col == id_value))
        return result.rowcount > 0


def update_entity(table_name: str, id_column: str, name_column: str,
                  id_value: int, new_name: str) -> bool:
    """
    Generic function to update an entity's name in a table.
    
    Parameters:
        table_name (str): Name of the database table
        id_column (str): Name of the ID column
        name_column (str): Name of the name column
        id_value (int): ID value to update
        new_name (str): New name value
        
    Returns:
        bool: True if entity was updated, False if not found
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the table
    table = Table(table_name, metadata, autoload_with=engine)
    
    # Get column references
    id_col = table.c[id_column]
    name_col = table.c[name_column]
    
    # Update entity name
    with engine.begin() as connection:
        result = connection.execute(
            update(table).where(id_col == id_value).values(**{name_column: new_name})
        )
        return result.rowcount > 0


# ============================================================================
# SHOP CRUD FUNCTIONS (using generic functions)
# ============================================================================

def get_all_shops():
    """
    Fetch all shops from the bre_shops table.
    
    Returns:
        pandas.DataFrame: DataFrame with shop_id and shop_name columns
    """
    return get_all_entities('bre_shops', 'shop_id', 'shop_name')


def add_shop(shop_name: str) -> int:
    """
    Add a new shop to the bre_shops table.
    
    Parameters:
        shop_name (str): Name of the shop to add
        
    Returns:
        int: The shop_id of the newly added shop
    """
    return add_entity('bre_shops', 'shop_id', 'shop_name', shop_name)


def remove_shop(shop_id: int) -> bool:
    """
    Remove a shop from the bre_shops table.
    
    Parameters:
        shop_id (int): ID of the shop to remove
        
    Returns:
        bool: True if shop was removed, False if not found
    """
    return remove_entity('bre_shops', 'shop_id', shop_id)


def update_shop(shop_id: int, new_shop_name: str) -> bool:
    """
    Update a shop's name in the bre_shops table.
    
    Parameters:
        shop_id (int): ID of the shop to update
        new_shop_name (str): New name for the shop
        
    Returns:
        bool: True if shop was updated, False if not found
    """
    return update_entity('bre_shops', 'shop_id', 'shop_name', shop_id, new_shop_name)


def get_all_accounts() -> pd.DataFrame:
    """
    Fetch all accounts from the bre_shop_account table.
    
    Returns:
        pandas.DataFrame: DataFrame with account_id and account_name columns
    """
    return get_all_entities('bre_shop_account', 'account_id', 'account_name')


def add_account(account_name: str) -> int:
    """
    Add a new account to the bre_shop_account table.
    
    Parameters:
        account_name (str): Name of the account to add
        
    Returns:
        int: The account_id of the newly added account
    """
    return add_entity('bre_shop_account', 'account_id', 'account_name', account_name)


def link_account_to_shop(shop_id: int, account_id: int) -> bool:
    """
    Link an account to a shop in the bre_shop_account_matrix table.
    
    Parameters:
        shop_id (int): ID of the shop
        account_id (int): ID of the account
        
    Returns:
        bool: True if linked successfully, False otherwise
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the new matching table
    bre_shop_account_matrix = Table('bre_shop_account_matrix', metadata, autoload_with=engine)
    
    with engine.begin() as connection:
        # Check if already linked
        result = connection.execute(
            select(bre_shop_account_matrix.c.account_id).where(
                bre_shop_account_matrix.c.shop_id == shop_id,
                bre_shop_account_matrix.c.account_id == account_id
            )
        )
        existing = result.scalar()
        
        if existing:
            return True
        
        # Link account to shop
        connection.execute(
            insert(bre_shop_account_matrix).values(shop_id=shop_id, account_id=account_id)
        )
        return True


def remove_account_from_shop(shop_id: int, account_id: int) -> bool:
    """
    Remove an account from a shop in the bre_shop_account_matrix table.
    
    Parameters:
        shop_id (int): ID of the shop
        account_id (int): ID of the account
        
    Returns:
        bool: True if removed, False if not found
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the new matching table
    bre_shop_account_matrix = Table('bre_shop_account_matrix', metadata, autoload_with=engine)
    
    with engine.begin() as connection:
        result = connection.execute(
            delete(bre_shop_account_matrix).where(
                bre_shop_account_matrix.c.shop_id == shop_id,
                bre_shop_account_matrix.c.account_id == account_id
            )
        )
        return result.rowcount > 0


def link_file_to_account(file_id: int, account_id: int) -> bool:
    """
    Link a file to an account in the bre_account_index table.
    
    Parameters:
        file_id (int): ID of the file to link
        account_id (int): ID of the account to link to
        
    Returns:
        bool: True if link was created, False if already exists or error
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the table
    bre_account_index = Table('bre_account_index', metadata, autoload_with=engine)
    
    # Check if link already exists
    check_query = select(bre_account_index.c.file_id).where(
        bre_account_index.c.file_id == file_id,
        bre_account_index.c.account_id == account_id
    )
    
    with engine.begin() as connection:
        existing = connection.execute(check_query).fetchone()
        if existing:
            return False
        
        # Insert new link
        result = connection.execute(
            insert(bre_account_index).values(file_id=file_id, account_id=account_id)
        )
        return result.rowcount > 0


def unlink_file_from_account(file_id: int, account_id: int) -> bool:
    """
    Remove a file link from an account in the bre_account_index table.
    
    Parameters:
        file_id (int): ID of the file to unlink
        account_id (int): ID of the account to unlink from
        
    Returns:
        bool: True if link was removed, False if not found
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the table
    bre_account_index = Table('bre_account_index', metadata, autoload_with=engine)
    
    # Delete link
    with engine.begin() as connection:
        result = connection.execute(
            delete(bre_account_index).where(
                bre_account_index.c.file_id == file_id,
                bre_account_index.c.account_id == account_id
            )
        )
        return result.rowcount > 0


def get_accounts_for_shop(shop_id: int) -> pd.DataFrame:
    """
    Get all accounts linked to a specific shop using the bre_shop_account_matrix table.
    
    Parameters:
        shop_id (int): ID of the shop
        
    Returns:
        pandas.DataFrame: DataFrame with account_id and account_name columns
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the tables
    bre_shop_account_matrix = Table('bre_shop_account_matrix', metadata, autoload_with=engine)
    bre_shop_account = Table('bre_shop_account', metadata, autoload_with=engine)
    
    # Query all data - join the matrix table with the account table
    query = select(
        bre_shop_account_matrix.c.account_id,
        bre_shop_account.c.account_name
    ).join(
        bre_shop_account,
        bre_shop_account_matrix.c.account_id == bre_shop_account.c.account_id
    ).where(
        bre_shop_account_matrix.c.shop_id == shop_id
    )
    
    with engine.begin() as connection:
        result = connection.execute(query)
        rows = result.fetchall()
    
    if rows:
        df = pd.DataFrame(rows, columns=['account_id', 'account_name'])
    else:
        df = pd.DataFrame(columns=['account_id', 'account_name'])
    return df





def get_file_count_for_shop(shop_id: int) -> int:
    """
    Get the total number of files linked to a specific shop.
    
    Parameters:
        shop_id (int): ID of the shop
        
    Returns:
        int: Number of files linked to the shop
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the table
    bre_shops_index = Table('bre_shops_index', metadata, autoload_with=engine)
    
    # Count files for shop
    query = select(func.count()).select_from(
        select(bre_shops_index.c.id).where(bre_shops_index.c.shop_id == shop_id).subquery()
    )
    
    with engine.begin() as connection:
        result = connection.execute(query).fetchone()
        return result[0] if result else 0


def get_files_for_shop(shop_id: int, page_size: int = 20, offset: int = 0) -> tuple:
    """
    Fetch files linked to a specific shop with pagination.
    
    Parameters:
        shop_id (int): ID of the shop
        page_size (int): Number of files per page
        offset (int): Number of files to skip (for pagination)
        
    Returns:
        tuple: (files_df, total_count) where files_df is a DataFrame with file info
               and total_count is the total number of files for this shop
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the tables
    bre_shops_index = Table('bre_shops_index', metadata, autoload_with=engine)
    bre_advance_index = Table('bre_advance_index', metadata, autoload_with=engine)
    bre_account_index = Table('bre_account_index', metadata, autoload_with=engine)
    
    # Build query with pagination - cast id to Integer for proper type matching
    subquery = select(bre_shops_index.c.id.cast(Integer).label('id')).where(
        bre_shops_index.c.shop_id == shop_id
    ).limit(page_size).offset(offset).subquery()
    
    # Join with bre_account_index to get account_id for each file
    query = select(
        subquery.c.id.label('file_id'),
        bre_advance_index.c.name.label('filename'),
        bre_advance_index.c.preview_url.label('preview_url'),
        bre_advance_index.c.path.label('webdav_path'),
        bre_account_index.c.account_id.label('account_id')
    ).join(
        bre_advance_index,
        subquery.c.id == bre_advance_index.c.fileid.cast(Integer)
    ).join(
        bre_account_index,
        subquery.c.id == bre_account_index.c.file_id.cast(Integer),
        isouter=True  # Left join to include files without account links
    )
    
    with engine.begin() as connection:
        result = connection.execute(query)
        rows = result.fetchall()
    
    if rows:
        df = pd.DataFrame(rows, columns=['file_id', 'filename', 'preview_url', 'webdav_path', 'account_id'])
    else:
        df = pd.DataFrame(columns=['file_id', 'filename', 'preview_url', 'webdav_path', 'account_id'])
    
    # Get total count
    total_count = get_file_count_for_shop(shop_id)
    
    return df, total_count


def link_file_to_shop(file_id: int, shop_id: int) -> bool:
    """
    Link a file to a shop in the bre_shops_index table.
    
    Parameters:
        file_id (int): ID of the file to link
        shop_id (int): ID of the shop to link to
        
    Returns:
        bool: True if link was created, False if already exists or error
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the table
    bre_shops_index = Table('bre_shops_index', metadata, autoload_with=engine)
    
    # Check if link already exists
    check_query = select(bre_shops_index.c.id).where(
        bre_shops_index.c.id == file_id,
        bre_shops_index.c.shop_id == shop_id
    )
    
    with engine.begin() as connection:
        existing = connection.execute(check_query).fetchone()
        if existing:
            return False
        
        # Insert new link
        result = connection.execute(
            insert(bre_shops_index).values(id=file_id, shop_id=shop_id)
        )
        return result.rowcount > 0


def unlink_file_from_shop(file_id: int, shop_id: int) -> bool:
    """
    Remove a file link from a shop in the bre_shops_index table.
    
    Parameters:
        file_id (int): ID of the file to unlink
        shop_id (int): ID of the shop to unlink from
        
    Returns:
        bool: True if link was removed, False if not found
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the table
    bre_shops_index = Table('bre_shops_index', metadata, autoload_with=engine)
    
    # Delete link
    with engine.begin() as connection:
        result = connection.execute(
            delete(bre_shops_index).where(
                bre_shops_index.c.id == file_id,
                bre_shops_index.c.shop_id == shop_id
            )
        )
        return result.rowcount > 0


def get_all_file_ids() -> list:
    """
    Get all available file IDs from the bre_advance_index table.
    
    Returns:
        list: List of file IDs
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the table
    bre_advance_index = Table('bre_advance_index', metadata, autoload_with=engine)
    
    query = select(bre_advance_index.c.fileid)
    
    with engine.begin() as connection:
        result = connection.execute(query).fetchall()
        return [row[0] for row in result]


def get_all_file_ids_with_info() -> pd.DataFrame:
    """
    Get all available file IDs with their info from the bre_advance_index table.
    
    Returns:
        pandas.DataFrame: DataFrame with file_id, filename, and preview_url columns
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the table
    bre_advance_index = Table('bre_advance_index', metadata, autoload_with=engine)
    
    query = select(
        bre_advance_index.c.fileid.label('file_id'),
        bre_advance_index.c.name.label('filename'),
        bre_advance_index.c.preview_url
    )
    
    with engine.begin() as connection:
        result = connection.execute(query).fetchall()
        if result:
            df = pd.DataFrame(result, columns=['file_id', 'filename', 'preview_url'])
        else:
            df = pd.DataFrame(columns=['file_id', 'filename', 'preview_url'])
        return df


def get_file_info(file_id: int) -> dict:
    """
    Get information about a specific file.
    
    Parameters:
        file_id (int): ID of the file
        
    Returns:
        dict: File information or empty dict if not found
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the table
    bre_advance_index = Table('bre_advance_index', metadata, autoload_with=engine)
    
    query = select(
        bre_advance_index.c.fileid,
        bre_advance_index.c.name,
        bre_advance_index.c.preview_url,
        bre_advance_index.c.path
    ).where(bre_advance_index.c.fileid == file_id)
    
    with engine.begin() as connection:
        result = connection.execute(query).fetchone()
        if result:
            return {
                'file_id': result.fileid,
                'filename': result.name,
                'preview_url': result.preview_url,
                'webdav_path': result.path
            }
        return {}


def get_files_for_shop_account(shop_id: int, account_id: int) -> pd.DataFrame:
    """
    Get all files linked to a specific account for a specific shop.
    Files are linked to accounts via the bre_account_index table with columns 'file_id' and 'account_id'.
    
    Parameters:
        shop_id (int): ID of the shop
        account_id (int): ID of the account
        
    Returns:
        pandas.DataFrame: DataFrame with file_id, filename, and preview_url columns
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the tables
    bre_account_index = Table('bre_account_index', metadata, autoload_with=engine)
    bre_advance_index = Table('bre_advance_index', metadata, autoload_with=engine)
    
    # Query files for the account - join bre_account_index with bre_advance_index
    query = select(
        bre_account_index.c.file_id.label('file_id'),
        bre_advance_index.c.name.label('filename'),
        bre_advance_index.c.preview_url.label('preview_url')
    ).join(
        bre_advance_index,
        bre_advance_index.c.fileid.cast(Integer) == bre_account_index.c.file_id.cast(Integer)
    ).where(
        bre_account_index.c.account_id == account_id
    )
    
    with engine.begin() as connection:
        result = connection.execute(query)
        rows = result.fetchall()
    
    if rows:
        df = pd.DataFrame(rows, columns=['file_id', 'filename', 'preview_url'])
    else:
        df = pd.DataFrame(columns=['file_id', 'filename', 'preview_url'])
    return df


def get_files_for_shop_account_paginated(shop_id: int, account_id: int, page_size: int = 20, offset: int = 0) -> tuple:
    """
    Get all files linked to a specific account for a specific shop with pagination.
    Files are linked to accounts via the bre_account_index table with columns 'file_id' and 'account_id'.
    
    Parameters:
        shop_id (int): ID of the shop
        account_id (int): ID of the account
        page_size (int): Number of files per page
        offset (int): Number of files to skip (for pagination)
        
    Returns:
        tuple: (files_df, total_count) where files_df is a DataFrame with file info
               and total_count is the total number of files for this shop-account combination
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the tables
    bre_account_index = Table('bre_account_index', metadata, autoload_with=engine)
    bre_advance_index = Table('bre_advance_index', metadata, autoload_with=engine)
    
    # Get total count first
    count_query = select(func.count()).select_from(
        select(bre_account_index.c.file_id).where(
            bre_account_index.c.account_id == account_id
        ).subquery()
    )
    
    with engine.begin() as connection:
        total_result = connection.execute(count_query).fetchone()
        total_count = total_result[0] if total_result else 0
    
    # Build query with pagination
    subquery = select(bre_account_index.c.file_id).where(
        bre_account_index.c.account_id == account_id
    ).limit(page_size).offset(offset).subquery()
    
    query = select(
        subquery.c.file_id.label('file_id'),
        bre_advance_index.c.name.label('filename'),
        bre_advance_index.c.preview_url.label('preview_url')
    ).join(
        bre_advance_index,
        bre_advance_index.c.fileid.cast(Integer) == subquery.c.file_id.cast(Integer)
    )
    
    with engine.begin() as connection:
        result = connection.execute(query)
        rows = result.fetchall()
    
    if rows:
        df = pd.DataFrame(rows, columns=['file_id', 'filename', 'preview_url'])
    else:
        df = pd.DataFrame(columns=['file_id', 'filename', 'preview_url'])
    
    return df, total_count


def get_all_hashes_from_db() -> pd.DataFrame:
    """
    Get all perceptual hashes from the bre_hashes table along with file info.
    
    Returns:
        pandas.DataFrame: DataFrame with id, filename, w_hash, a_hash, p_hash,
                         preview_url, and webdav_path columns (matching fingerprinting module)
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the tables
    bre_hashes = Table('bre_hashes', metadata, autoload_with=engine)
    bre_advance_index = Table('bre_advance_index', metadata, autoload_with=engine)
    
    # Query all data with file info using INNER JOIN on fileid = id
    query = select(
        bre_hashes.c.id.label('id'),
        bre_hashes.c.w_hash,
        bre_hashes.c.a_hash,
        bre_hashes.c.p_hash,
        bre_advance_index.c.name.label('filename'),
        bre_advance_index.c.preview_url.label('preview_url'),
        bre_advance_index.c.path.label('webdav_path')
    ).join(
        bre_advance_index,
        bre_hashes.c.id == bre_advance_index.c.fileid
    )
    
    with engine.begin() as connection:
        result = connection.execute(query).fetchall()
        if result:
            df = pd.DataFrame(result, columns=['id', 'w_hash', 'a_hash', 'p_hash',
                                                'filename', 'preview_url', 'webdav_path'])
        else:
            df = pd.DataFrame(columns=['id', 'w_hash', 'a_hash', 'p_hash',
                                       'filename', 'preview_url', 'webdav_path'])
        return df


# In-memory cache for downloaded images (file_id -> PIL Image)
image_cache = {}


def get_preview_image(file_id: int, preview_url: str, db_host: str = None) -> Image.Image:
    """
    Download and cache a preview image from Nextcloud.
    
    Parameters:
        file_id (int): ID of the file
        preview_url (str): Relative preview URL from database
        db_host (str): Database host for URL construction
        
    Returns:
        PIL.Image: Resized image (540x540) or None if failed
    """
    if db_host is None:
        load_dotenv()
        db_host = os.getenv("DB_HOST", "192.168.0.150")
    
    nc_acc = os.getenv("NC_ACC")
    nc_pass = os.getenv("NC_PASS")
    
    # Check cache first
    if file_id in image_cache:
        return image_cache[file_id]
    
    # Construct full preview URL
    if preview_url.startswith('/core/preview'):
        full_url = f"http://{db_host}:8080{preview_url.replace('{prevsize}', 'x=540&y=540')}"
    else:
        full_url = preview_url
    
    # Send a GET request to download the preview
    response = requests.get(full_url, auth=HTTPBasicAuth(nc_acc, nc_pass), stream=True)
    
    try:
        if response.status_code == 200:
            file_in_memory = BytesIO()
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file_in_memory.write(chunk)
            file_in_memory.seek(0)
            img = Image.open(file_in_memory)
            img = img.resize((540, 540))
            image_cache[file_id] = img  # Cache the image
            return img
        elif response.status_code == 404:
            # Fall back to WebDAV if needed
            webdav_base_url = f'http://{db_host}:8080/remote.php/dav/files/{nc_acc}'
            webdav_file_url = f'{webdav_base_url}{preview_url}'
            
            try:
                webdav_response = requests.get(webdav_file_url, auth=HTTPBasicAuth(nc_acc, nc_pass), stream=True)
                if webdav_response.status_code == 200:
                    file_in_memory = BytesIO()
                    for chunk in webdav_response.iter_content(chunk_size=1024):
                        if chunk:
                            file_in_memory.write(chunk)
                    file_in_memory.seek(0)
                    source_img = Image.open(file_in_memory)
                    img = source_img.resize((540, 540))
                    image_cache[file_id] = img
                    return img
            except Exception as e:
                print(f"Error downloading via WebDAV for file {file_id}: {e}")
        else:
            print(f"Failed to download file. Status code: {response.status_code}")
        return None
    except Exception as e:
        print(f"Error downloading file {file_id}: {e}")
        return None

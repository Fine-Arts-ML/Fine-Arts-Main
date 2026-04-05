"""
Database handler for the Shop Management app.
Provides functions for database connections and queries.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table, select, insert, delete, update, func
import pandas as pd


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


def get_all_shops():
    """
    Fetch all shops from the bre_shops table.
    
    Returns:
        pandas.DataFrame: DataFrame with shop_id and shop_name columns
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the table
    bre_shops = Table('bre_shops', metadata, autoload_with=engine)
    
    # Query all data - use column names from the actual table
    shop_id_col = bre_shops.c.shop_id
    shop_name_col = bre_shops.c.shop_name
    
    query = select(shop_id_col, shop_name_col)
    
    with engine.begin() as connection:
        result = connection.execute(query)
        rows = result.fetchall()
    
    if rows:
        df = pd.DataFrame(rows, columns=['shop_id', 'shop_name'])
    else:
        df = pd.DataFrame(columns=['shop_id', 'shop_name'])
    print(df)
    return df


def add_shop(shop_name: str) -> int:
    """
    Add a new shop to the bre_shops table.
    
    Parameters:
        shop_name (str): Name of the shop to add
        
    Returns:
        int: The shop_id of the newly added shop
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the table
    bre_shops = Table('bre_shops', metadata, autoload_with=engine)
    
    # Step 1: Get the table from the db
    with engine.begin() as connection:
        # Step 2: Count the entries (get max shop_id)
        result = connection.execute(
            select(func.max(bre_shops.c.shop_id))
        )
        max_shop_id = result.scalar() or 0
        
        # Step 3: Check if the shop is already present in the db
        result = connection.execute(
            select(bre_shops.c.shop_name).where(bre_shops.c.shop_name == shop_name)
        )
        existing_shop = result.scalar()
        
        # Step 4: If shop is new, then append it with a new id
        if existing_shop:
            # Shop already exists, return its id
            return max_shop_id
        else:
            # Shop is new, assign new id (max_shop_id + 1)
            new_shop_id = max_shop_id + 1
            connection.execute(
                insert(bre_shops).values(shop_id=new_shop_id, shop_name=shop_name)
            )
            return new_shop_id


def remove_shop(shop_id: int) -> bool:
    """
    Remove a shop from the bre_shops table.
    
    Parameters:
        shop_id (int): ID of the shop to remove
        
    Returns:
        bool: True if shop was removed, False if not found
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the table
    bre_shops = Table('bre_shops', metadata, autoload_with=engine)
    
    # Delete shop
    with engine.begin() as connection:
        result = connection.execute(
            delete(bre_shops).where(bre_shops.c.shop_id == shop_id)
        )
        return result.rowcount > 0


def update_shop(shop_id: int, new_shop_name: str) -> bool:
    """
    Update a shop's name in the bre_shops table.
    
    Parameters:
        shop_id (int): ID of the shop to update
        new_shop_name (str): New name for the shop
        
    Returns:
        bool: True if shop was updated, False if not found
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the table
    bre_shops = Table('bre_shops', metadata, autoload_with=engine)
    
    # Update shop name
    with engine.begin() as connection:
        result = connection.execute(
            update(bre_shops).where(bre_shops.c.shop_id == shop_id).values(shop_name=new_shop_name)
        )
        return result.rowcount > 0


def get_all_accounts() -> pd.DataFrame:
    """
    Fetch all accounts from the bre_shop_account table.
    
    Returns:
        pandas.DataFrame: DataFrame with account_id and account_name columns
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    try:
        # Reflect the table
        bre_shop_account = Table('bre_shop_account', metadata, autoload_with=engine)
        
        # Query all data
        account_id_col = bre_shop_account.c.account_id
        account_name_col = bre_shop_account.c.account_name
        
        query = select(account_id_col, account_name_col)
        
        with engine.begin() as connection:
            result = connection.execute(query)
            rows = result.fetchall()
        
        if rows:
            df = pd.DataFrame(rows, columns=['account_id', 'account_name'])
        else:
            df = pd.DataFrame(columns=['account_id', 'account_name'])
        return df
    except Exception as e:
        print(f"Error fetching accounts: {e}")
        return pd.DataFrame(columns=['account_id', 'account_name'])


def add_account(account_name: str) -> int:
    """
    Add a new account to the bre_shop_account table.
    
    Parameters:
        account_name (str): Name of the account to add
        
    Returns:
        int: The account_id of the newly added account
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the table
    bre_shop_account = Table('bre_shop_account', metadata, autoload_with=engine)
    
    with engine.begin() as connection:
        # Get max account_id
        result = connection.execute(
            select(func.max(bre_shop_account.c.account_id))
        )
        max_account_id = result.scalar() or 0
        
        # Check if account already exists
        result = connection.execute(
            select(bre_shop_account.c.account_name).where(bre_shop_account.c.account_name == account_name)
        )
        existing_account = result.scalar()
        
        if existing_account:
            return max_account_id
        else:
            new_account_id = max_account_id + 1
            connection.execute(
                insert(bre_shop_account).values(account_id=new_account_id, account_name=account_name)
            )
            return new_account_id


def link_account_to_shop(shop_id: int, account_id: int) -> bool:
    """
    Link an account to a shop in the bre_shop_account table.
    
    Parameters:
        shop_id (int): ID of the shop
        account_id (int): ID of the account
        
    Returns:
        bool: True if linked successfully, False otherwise
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the table
    bre_shop_account = Table('bre_shop_account', metadata, autoload_with=engine)
    
    with engine.begin() as connection:
        # Check if already linked
        result = connection.execute(
            select(bre_shop_account.c.account_id).where(
                bre_shop_account.c.shop_id == shop_id,
                bre_shop_account.c.account_id == account_id
            )
        )
        existing = result.scalar()
        
        if existing:
            return True
        
        # Link account to shop
        connection.execute(
            insert(bre_shop_account).values(shop_id=shop_id, account_id=account_id)
        )
        return True


def remove_account_from_shop(shop_id: int, account_id: int) -> bool:
    """
    Remove an account from a shop in the bre_shop_account table.
    
    Parameters:
        shop_id (int): ID of the shop
        account_id (int): ID of the account
        
    Returns:
        bool: True if removed, False if not found
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the table
    bre_shop_account = Table('bre_shop_account', metadata, autoload_with=engine)
    
    with engine.begin() as connection:
        result = connection.execute(
            delete(bre_shop_account).where(
                bre_shop_account.c.shop_id == shop_id,
                bre_shop_account.c.account_id == account_id
            )
        )
        return result.rowcount > 0


def get_accounts_for_shop(shop_id: int) -> pd.DataFrame:
    """
    Get all accounts linked to a specific shop.
    
    Parameters:
        shop_id (int): ID of the shop
        
    Returns:
        pandas.DataFrame: DataFrame with account_id and account_name columns
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the tables
    bre_shop_account = Table('bre_shop_account', metadata, autoload_with=engine)
    
    # Query all data
    account_id_col = bre_shop_account.c.account_id
    account_name_col = bre_shop_account.c.account_name
    
    query = select(account_id_col, account_name_col).where(
        bre_shop_account.c.shop_id == shop_id
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
    
    # Build query with pagination
    subquery = select(bre_shops_index.c.id).where(
        bre_shops_index.c.shop_id == shop_id
    ).limit(page_size).offset(offset).subquery()
    
    query = select(
        subquery.c.id.label('file_id'),
        bre_advance_index.c.name.label('filename'),
        bre_advance_index.c.preview_url.label('preview_url'),
        bre_advance_index.c.path.label('webdav_path')
    ).join(
        bre_advance_index,
        subquery.c.id == bre_advance_index.c.fileid
    )
    
    with engine.begin() as connection:
        result = connection.execute(query)
        rows = result.fetchall()
    
    if rows:
        df = pd.DataFrame(rows, columns=['file_id', 'filename', 'preview_url', 'webdav_path'])
    else:
        df = pd.DataFrame(columns=['file_id', 'filename', 'preview_url', 'webdav_path'])
    
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

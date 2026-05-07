"""
Database handler for the Image Fingerprinting app.
Provides functions for database connections and queries.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table, select
import pandas as pd


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


def get_tags_for_file(file_id):
    """
    Fetch tags for a specific file from the bre_search_index_live table.
    
    Parameters:
        file_id (int): The file ID to fetch tags for
        
    Returns:
        str: Comma-separated tag names, or empty string if no tags
    """
    engine = create_db_connection()
    metadata = MetaData()
    
    # Reflect the table
    bre_search_index_live = Table('bre_search_index_live', metadata, autoload_with=engine)
    
    # Build the query
    query = select(
        bre_search_index_live.c.tag_name.label('tag_name'),
    ).where(
        bre_search_index_live.c.objectid == file_id
    )
    
    with engine.connect() as connection:
        result = connection.execute(query)
        tags = [{'tag_name': row.tag_name} for row in result]
    
    tag_names = [tag['tag_name'] for tag in tags]
    return ', '.join(tag_names) if tag_names else ''

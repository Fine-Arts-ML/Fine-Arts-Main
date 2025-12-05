import pg8000
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, MetaData, Table, select, insert
from sqlalchemy.exc import SQLAlchemyError
load_dotenv()
import pandas as pd



def create_db_connection():
    load_dotenv()
    DB_HOST = os.getenv("DB_HOST")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    engine = create_engine('postgresql+pg8000://'+DB_USER+':'+DB_PASSWORD+'@'+DB_HOST+':5432/'+DB_NAME)
    return engine

def get_file_ids_of_tagged_images():
    try:
        engine = create_db_connection()
        metadata = MetaData()

        # Reflect the oc_systemtag_object_mapping table
        oc_systemtag_object_mapping = Table('oc_systemtag_object_mapping', metadata, autoload_with=engine)

        # Query to fetch all file IDs that have tags
        stmt = select(oc_systemtag_object_mapping.c.objectid).where(
            oc_systemtag_object_mapping.c.objecttype == 'files'
        ).distinct()

        with engine.connect() as conn:
            result = conn.execute(stmt)
            file_ids = [row[0] for row in result.fetchall()]

        print(f"Found {len(file_ids)} tagged images.")
        return file_ids

    except Exception as e:
        print(f"An error occurred: {e}")


def get_tags_for_id(id):
    engine = create_db_connection()
    metadata = MetaData()

    # Reflect the tables
    oc_systemtag = Table('oc_systemtag', metadata, autoload_with=engine)
    oc_systemtag_object_mapping = Table('oc_systemtag_object_mapping', metadata, autoload_with=engine)

    # Build the query
    query = select(
        oc_systemtag.c.id.label('tag_id'),
        oc_systemtag.c.name.label('tag_name')
    ).join(
        oc_systemtag_object_mapping,
        oc_systemtag_object_mapping.c.systemtagid == oc_systemtag.c.id
    ).where(
        oc_systemtag_object_mapping.c.objectid == id
    )

    with engine.connect() as connection:
            result = connection.execute(query)
            tags = [{'tag_id': row.tag_id, 'tag_name': row.tag_name} for row in result]

    return tags



def get_hypo_search(id):
    engine = create_db_connection()
    df_hypo = pd.read_sql(f'''
        SELECT *
        FROM bre_advance_search
        WHERE bre_advance_search.id = '{id}'
    ''', engine)
    return df_hypo

def get_preview_index(preview_size, DB_HOST) :
    engine = create_db_connection()
    metadata = MetaData()

    # Reflect the tables
    Index_table = Table('bre_advance_index', metadata, autoload_with=engine)
    query = select(Index_table)
    with engine.connect() as connection:
        df_index = pd.DataFrame(connection.execute(query).fetchall())

        # Set column names
        df_index.columns = Index_table.columns.keys()


    for index, row in df_index.iterrows():
        prev_url = row['preview_url']
        prev_url = f'''http://{DB_HOST}:8080{prev_url.replace('{prevsize}', f'''x={preview_size}&y={preview_size}''')}'''
        df_index.loc[index, 'preview_url'] = prev_url

    return df_index



import os
import pg8000
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, MetaData, Table, select, insert
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
import subprocess
import os
from tqdm import tqdm
import uniqid

load_dotenv()



def create_db_connection():
    DB_HOST = os.getenv("DB_HOST")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    engine = create_engine('postgresql+pg8000://'+DB_USER+':'+DB_PASSWORD+'@'+DB_HOST+':5432/'+DB_NAME)
    return engine


def insert_tags_and_assign_to_files(file_list):
    try:
        engine = create_db_connection()
        metadata = MetaData()

        # Reflect the tables only once
        oc_systemtag = Table('oc_systemtag', metadata, autoload_with=engine)
        oc_systemtag_object_mapping = Table('oc_systemtag_object_mapping', metadata, autoload_with=engine)

        #print("Columns in oc_systemtag:", oc_systemtag.columns.keys())

        with engine.connect() as conn:
            for file_info in tqdm(file_list):
                file_id = file_info['fileid']
                tags_str = file_info['tags']
                tags = [tag.strip() for tag in tags_str.split(';')]

                # Step 1: Insert tags into oc_systemtag and collect tag_ids
                tag_ids = []
                for tag_name in tags:
                    # Check if the tag already exists
                    stmt = select(oc_systemtag.c.id).where(oc_systemtag.c.name == tag_name)
                    result = conn.execute(stmt)
                    row = result.fetchone()

                    if row:
                        tag_id = row[0]
                    else:
                        # Insert the new tag
                        insert_data = {'name': tag_name}
                        if 'user_visible' in oc_systemtag.columns:
                            insert_data['user_visible'] = True
                        if 'user_assignable' in oc_systemtag.columns:
                            insert_data['user_assignable'] = True

                        stmt = insert(oc_systemtag).values(**insert_data).returning(oc_systemtag.c.id)
                        result = conn.execute(stmt)
                        tag_id = result.fetchone()[0]

                    tag_ids.append(tag_id)

                # Step 2: Assign tags to the file in oc_systemtag_object_mapping
                for tag_id in tag_ids:
                    # Check if the mapping already exists
                    stmt = select(oc_systemtag_object_mapping).where(
                        oc_systemtag_object_mapping.c.systemtagid == tag_id,
                        oc_systemtag_object_mapping.c.objecttype == 'files',
                        oc_systemtag_object_mapping.c.objectid == file_id
                    )
                    result = conn.execute(stmt)
                    if not result.fetchone():
                        # Insert the mapping
                        stmt = insert(oc_systemtag_object_mapping).values(
                            systemtagid=tag_id,
                            objecttype='files',
                            objectid=file_id
                        )
                        conn.execute(stmt)

                #print(f"Tags inserted and assigned successfully for {file_info['name']}!")

            # Commit the transaction once for all files
            conn.commit()

    except SQLAlchemyError as e:
        print(f"An error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    
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
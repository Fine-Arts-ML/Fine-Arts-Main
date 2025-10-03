import os
import pg8000
from dotenv import load_dotenv
import os
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy import inspect
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

def get_file_locs(engine, SELECT, FROM, LIKE, ORDER, LIMIT):



    Querry_string = f"SELECT {SELECT} FROM {FROM} WHERE path like {LIKE} ORDER BY {ORDER} DESC LIMIT {LIMIT}"
    
    try:
        df_file_loc = pd.read_sql_query(sqlalchemy.text(Querry_string), engine)
        print("got file paths")
    except Exception as e:
        print("Error:", e)
    
    Querry_string_user = f"SELECT * FROM public.oc_storages ORDER BY numeric_id ASC LIMIT {LIMIT}"
    try:
        df_user_loc = pd.read_sql_query(sqlalchemy.text(Querry_string_user), engine)
        print("done")
    except Exception as e:
        print("Error:", e)
    
    df_user_loc['id_clean'] = df_user_loc['id'].str.replace('(home::|local::)', '', regex=True)
    df_file_loc = pd.merge(df_file_loc, df_user_loc[['numeric_id', 'id_clean']], 
          left_on='storage', 
          right_on='numeric_id', 
          how='left')
         
    df_file_loc['full_path'] = df_file_loc['id_clean'].astype(str) + '/' + df_file_loc['path'].astype(str)

    return df_file_loc



def get_files(df_file_loc):
    # Base remote path
    remote_base = os.getenv("REMOTE_BASE_PATH")

    # password and user
    password = os.getenv("SSHPASS")
    ssh_user = os.getenv("SSHUSER")
    ssh_ip = os.getenv("SSHIP")

    # Create a cache directory if it doesn't exist
    cache_dir = os.getenv("CACHE_DIR")
    os.makedirs(cache_dir, exist_ok=True)
    print(f"found {len(df_file_loc)} files to copy")
    # SSH command to list files
    for i in tqdm(range(len(df_file_loc))):
        path = df_file_loc.iloc[i]['full_path']
        # Clean the path (remove 'files/' prefix)
        full_path = f"{remote_base}{path}"
        # Escape spaces in the path for shell commands
        escaped_path = full_path.replace(' ', '\\ ')
        
        # Execute SSH command with sudo and provide password through stdin
        cmd = f'''sshpass -p {password} ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_ip} "echo {password} | sudo -S ls -l '{full_path}'"'''
        try:
            result = subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

            # Extract the filename from the path
            filename = os.path.basename(path)
            local_path = os.path.join(cache_dir, filename)

            # Use sudo with SCP to copy the file
            scp_cmd = f'''sshpass -p {password} ssh -o StrictHostKeyChecking=no {ssh_user}@{ssh_ip} "echo {password} | sudo -S cat '{full_path}'" > "{local_path}"'''
            scp_result = subprocess.run(scp_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

            if os.path.getsize(local_path) < 1:
                print(f"Error copying file {filename}")
        except Exception as e:
            print(f"Error accessing {full_path}: {str(e)}")
        df_file_loc.at[df_file_loc.index[i],'local_path'] = local_path

    return  df_file_loc

def get_allready_tag_fileid (engine):
    QUERRY = "SELECT objectid, systemtagid FROM public.oc_systemtag_object_mapping"
    try:
        df_fileid = pd.read_sql_query(sqlalchemy.text(QUERRY), engine)
    except Exception as e:
        print("Error:", e)
    df_fileid_uniq = pd.DataFrame()
    df_fileid_uniq["objectid"] = df_fileid.objectid.unique()
    return df_fileid_uniq

def get_all_tags(engine):
    QUERRY = "SELECT * FROM public.oc_systemtag"
    try:
        df_tags = pd.read_sql_query(sqlalchemy.text(QUERRY), engine)
        print("got tags")
    except Exception as e:
        print("Error:", e)
    return df_tags


def write_tags_to_db(tags, engine):
    #get the existing tags
    existing_tags = get_all_tags(engine)
    existing_tags['name'] = existing_tags['name'].str.lower()
    # Drop duplicate tag names
    tags = tags.drop_duplicates(subset=['name'])

    # Create a new DataFrame for new tags
    new_tags = pd.DataFrame(columns=['id', 'name', 'visibility', 'editable', 'etag', "color"])
    new_tags['name'] = tags['name']

    # Filter out tags that already exist in the database
    new_tags = new_tags[~new_tags['name'].isin(existing_tags['name'])]
    if new_tags.empty:
        print("No new tags to insert into the database.")
    else:
        print(f"Inserting {len(new_tags)} new tags into the database.")

        # Ensure the 'id' column is of type int and assign new IDs
        if existing_tags.empty:
            new_tags['id'] = range(1, len(new_tags) + 1)
        else:
            new_tags['id'] = range(existing_tags['id'].max() + 1, existing_tags['id'].max() + len(new_tags) + 1)

        # Set default values for new columns
        new_tags['visibility'] = 1
        new_tags['editable'] = 1
        new_tags['etag'] = [uniqid.uniqid() for _ in range(len(new_tags))]
        new_tags['color'] = None

        # Ensure correct types
        new_tags['id'] = new_tags['id'].astype(int)
        new_tags['visibility'] = new_tags['visibility'].astype(int)
        new_tags['editable'] = new_tags['editable'].astype(int)
        new_tags.index = new_tags.id

        # Insert new tags into the database
        new_tags.to_sql('oc_systemtag', engine, if_exists='append', index=False)



def upload_new_obj_map(engine, tags, df_db):
    
    # Map tags to fileids
    df_all_tag = get_all_tags(engine)
    df_map = df_db[['fileid', 'tags']]
    df_map = df_map.assign(tags=df_map['tags'].str.split(';'))
    df_map = df_map.explode('tags')
    df_map['tags'] = df_map['tags'].str.strip()
    df_map = df_map.drop_duplicates()



    # Assuming:
    # df_all_tags has columns: id, name
    # df_source has columns: fileid, tags

    # Merge df_source with df_all_tags on tag name
    df_result = pd.merge(
        df_map,
        df_all_tag,
        left_on='tags',
        right_on='name',
        how='inner'
    )

    # Select only the columns needed
    df_result = df_result[['fileid', 'id']]
    df_result.columns = ['objectid', 'systemtagid']
    df_result['objecttype'] = "files"
    df_result.to_sql('oc_systemtag_object_mapping', engine, if_exists="append", index=False)


def cleanup_cache(cache_dir):
    #cleanup cache directory
    os.listdir(cache_dir)
    for file in tqdm(os.listdir(cache_dir)):
        file_path = os.path.join(cache_dir, file)
        if os.path.isfile(file_path) and not file.endswith('.csv'):
            os.remove(file_path)

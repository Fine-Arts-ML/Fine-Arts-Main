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


# Load environment variables from .env file
load_dotenv()

# Database connection details


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


def get_files(df_file_loc, tail):
    # Get first 10 paths from dataframe
    if tail != 0:
        paths = df_file_loc['full_path'].tail(tail).tolist()
    else:
        paths = df_file_loc['full_path'].tolist()

    # Base remote path
    remote_base = os.getenv("REMOTE_BASE_PATH")

    # password and user
    password = os.getenv("SSHPASS")
    ssh_user = os.getenv("SSHUSER")
    ssh_ip = os.getenv("SSHIP")

    # Create a cache directory if it doesn't exist
    cache_dir = os.getenv("CACHE_DIR")
    os.makedirs(cache_dir, exist_ok=True)
    print(f"found {len(paths)} files to copy")
    # SSH command to list files
    for path in tqdm(paths):
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

            

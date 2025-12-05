import streamlit as st
from psql_con import *
from webdav_handler import *
from dotenv import load_dotenv
import os
import sys

load_dotenv()
#####################
DB_HOST = os.getenv("DB_HOST")
NC_ACC = os.getenv("NC_ACC")
NC_PASS = os.getenv("NC_PASS")


def flatten_dict_to_list(data):
    result_list = []
    
    def process_dict(content):
        for key, val in content.items():
            # If it's a folder entry
            if key.endswith("/"):
                if isinstance(val, dict):
                    process_dict(val)
            # If it's a file entry with metadata
            elif isinstance(val, dict) and 'name' in val:
                result_list.append(val)
    
    # Start with the root content
    if len(data) == 1:
        first_val = next(iter(data.values()))
        content = first_val
    else:
        content = data
        
    process_dict(content)
    return result_list


def main():
    server_url = f'http://{DB_HOST}:8080/remote.php/dav/files/{NC_ACC}'
    username = NC_ACC
    password = NC_PASS
    path = "/Bre/Artwork//AI_art/"

    client = webdav_login(server_url, username, password)
    if client:
        print("Client connected")
        root_dict = {path.strip("/").split("/")[-1]: folder_to_dict_w_meta_tqdm(path, client, server_url)}
    else:
        print('Could not connect to WebDav. Check your .env file!')
        sys.exit(10)

    data_list = flatten_dict_to_list(root_dict)
    print(f'Found {len(data_list)} files in storage')

    # Get tagged file IDs from the database

    N_of_cols = st.slider('set image size',1,10,5)

    cols = st.columns(N_of_cols)

    for row in data_list:
        file_id = row['fileid']
        tags = get_tags_from_id(file_id)
        tag_names = [tag['tag_name'] for tag in tags]
        row['tagnames'] = ', '.join(tag_names)
            
    
    
  

    for idx, col in enumerate(cols):
        with col:
            len_col = len(data_list) // N_of_cols
            start_idx = idx * len_col
            end_idx = (idx + 1) * len_col if idx != N_of_cols - 1 else len(data_list)
            display_data = data_list[start_idx:end_idx]

            for row in display_data:
                try:
                    file_id = row['fileid']
                    img_path = row['path']
                    tag_names = row.get('tagnames', '')

                    st.image(get_images(file_id, img_path))
                    st.write(f"{tag_names}")

                except Exception as e:
                    continue
       #try:

           # st.write(f"hypo: ")
           # st.dataframe(get_hypo_search(file_id))
        #except Exception as e:
         #   print(f"no Preview availible for:{img_path} /n: {e}")


main()

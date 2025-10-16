import sys
import psql_handler
import image_tags
from webdav_handler import webdav_login, folder_to_dict_w_meta_tqdm, get_images
import os
from dotenv import load_dotenv
import gc
import json
from tqdm import tqdm

load_dotenv()
cache_dir = os.getenv("CACHE_DIR")

### MLX needs to be restarted after Max 10 runs, adjust if necessary ###
max_mlx_run = 10
batch_size = 20  # Number of prompts to process before inserting into the database

#####################
DB_HOST = os.getenv("DB_HOST")
NC_ACC = os.getenv("NC_ACC")
NC_PASS = os.getenv("NC_PASS")

def main():
    server_url = f'http://{DB_HOST}:8080/remote.php/dav/files/{NC_ACC}'
    username = NC_ACC
    password = NC_PASS
    path = "/Bre/Artwork/"

    client = webdav_login(server_url, username, password)
    if client:
        print("Client connected")
        root_dict = {path.strip("/").split("/")[-1]: folder_to_dict_w_meta_tqdm(path, client, server_url)}
        open("./webdav_meta.json", "w").write(json.dumps(root_dict, indent=4))
    else:
        print('Could not connect to WebDav. Check your .env file!')
        sys.exit(10)

    data_list = image_tags.flatten_dict_to_list(root_dict)
    print(f'Found {len(data_list)} files in storage')

    # Get tagged file IDs from the database
    tagged_file_ids = psql_handler.get_file_ids_of_tagged_images()

    # Filter out already tagged images
    data_list = image_tags.filter_untagged_images(data_list, tagged_file_ids)
    if len(data_list) != 0:
        print(f'Found {len(data_list)} files to process')

    prompt = "Generate Tags for the image, for selling it in artsy online stores, no other text. Return separated like: tag1;tag2;tag3. Max 15 tags. Only use lemmatized words. Always include Art-style and color composition."

    run_count = 1
    gc.collect()
    model, processor, config = image_tags.load_model_mlx()

    for i in tqdm(range(0, len(data_list), batch_size)):
        batch = data_list[i:i + batch_size]

        for item in batch:
            if run_count > max_mlx_run:
                print('Restarting MLX')
                del model, processor, config
                gc.collect()
                run_count = 1
                model, processor, config = image_tags.load_model_mlx()

            img = get_images(item['fileid'], item['path'])
            item['tags'] = image_tags.mlx_tags(img, prompt, model, processor, config)
            run_count += 1

        # Insert tags for the current batch into the database
        psql_handler.insert_tags_and_assign_to_files(batch)
        print(f'Inserted tags for batch {i//batch_size + 1}')

    # Insert any remaining items that didn't make up a full batch
    if len(data_list) % batch_size != 0:
        remaining_items = data_list[(len(data_list) // batch_size) * batch_size:]
        psql_handler.insert_tags_and_assign_to_files(remaining_items)
        print('Inserted tags for remaining items')

if __name__ == "__main__":
    main()
import sys
import psql_handler
from image_tags import get_tags_from_cache
from psql_handler import create_db_connection
import os 
from dotenv import load_dotenv
from multiprocessing import Pool
import pandas as pd

load_dotenv()
cache_dir = os.getenv("CACHE_DIR")
###Choose model###
#model_id = "LFM2"
#model_id = "Pixtral_transformer"
model_id = "Mistral_mlx"
#####################

def main():
    engine = psql_handler.create_db_connection()
    if engine is None:
        print("Failed to connect to the database.")
        sys.exit(1)
    # Define query parameters
    SELECT = "storage, fileid, path, path_hash, name, etag "
    FROM = "public.oc_filecache"
    LIKE = "'files/%' and (path LIKE '%.JPG' OR path LIKE '%.jpg') and storage = 1"
    ORDER = "fileid"
    LIMIT = 150
   
   
    # Get file locations
    df_file_loc = psql_handler.get_file_locs(engine, SELECT, FROM, LIKE, ORDER, str(LIMIT))
    #get already tagged files
    df_file_w_tag = psql_handler.get_allready_tag_fileid(engine)
    #filter out already tagged files
    df_file_loc = df_file_loc[~df_file_loc['fileid'].isin(df_file_w_tag['objectid'])]



    # Get files from the dataframe
    df_file_loc = psql_handler.get_files(df_file_loc)
    print(F"Copied {len(df_file_loc)} files to {cache_dir}")

    df_new_tags = get_tags_from_cache(df_file_loc, model_id, " Generate Tags for image, no other text. Return seperated like: tag1;tag2;tag3. Max 10 tags. only use lemmatized words.")
 
    df_file_loc.to_csv((cache_dir + "/db.csv"))
   
    tags = df_new_tags['tags']
    # Split the tags into separate rows
    tags_expanded = tags.str.split(';').explode().str.strip().replace('"', '', regex=True)
    tags_expanded = tags_expanded[tags_expanded != '']
    tags_expanded = tags_expanded.drop_duplicates()
    tags_expanded = tags_expanded.str.lower()
    tags_expanded = tags_expanded.reset_index(drop=True)
    tags = tags_expanded.to_frame(name='name')
    tags.to_csv(((cache_dir + '/tags.csv')), index=False)
   
    psql_handler.write_tags_to_db(tags, engine)

    # Map tags to fileids
    psql_handler.upload_new_obj_map(engine, tags, df_file_loc)




    # Get files from the dataframe
    df_file_loc = psql_handler.get_files(df_file_loc)
    print(F"Copied {len(df_file_loc)} files to {cache_dir}")

    df_new_tags = get_tags_from_cache(df_file_loc, model_id, " Generate Tags for image, no other text. Return seperated like: tag1;tag2;tag3. Max 10 tags. only use lemmatized words.")

    df_file_loc.to_csv((cache_dir + "/db.csv"))

    tags = df_new_tags['tags']
    # Split the tags into separate rows
    tags_expanded = tags.str.split(';').explode().str.strip().replace('"', '', regex=True)
    tags_expanded = tags_expanded[tags_expanded != '']
    tags_expanded = tags_expanded.drop_duplicates()
    tags_expanded = tags_expanded.str.lower()
    tags_expanded = tags_expanded.reset_index(drop=True)
    tags = tags_expanded.to_frame(name='name')
    tags.to_csv(((cache_dir + '/tags.csv')), index=False)

    psql_handler.write_tags_to_db(tags, engine)

    # Map tags to fileids
    psql_handler.upload_new_obj_map(engine, tags, df_file_loc)

    psql_handler.cleanup_cache(cache_dir)



if __name__ == "__main__":
    main()
import sys
import psql_handler
from psql_handler import create_db_connection
import os 
from dotenv import load_dotenv

load_dotenv()
cache_dir = os.getenv("CACHE_DIR")

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
    LIMIT = "100"
    # Get file locations
    df_file_loc = psql_handler.get_file_locs(engine, SELECT, FROM, LIKE, ORDER, LIMIT)
    if df_file_loc is None:
        print("No file locations found.")
        sys.exit(1)

    # Get files from the dataframe
    paths = psql_handler.get_files(df_file_loc, tail=30)
    print(F"Copied {len(paths)} files to {cache_dir}")

if __name__ == "__main__":
    main()
import streamlit as st
from psql_con import *
from webdav_handler import *
from dotenv import load_dotenv
from search_func import *
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from IPython.display import display, Image
from PIL import Image as PILImage
from time import sleep

load_dotenv()
#####################
DB_HOST = os.getenv("DB_HOST")
NC_ACC = os.getenv("NC_ACC")
NC_PASS = os.getenv("NC_PASS")

# Get tagged file IDs from the database
@st.cache_data(show_spinner=True)
def get_tags_from_id(df_data):
    for index, row in df_data.iterrows():
        file_id = row['fileid']
        tags = get_tags_for_id(file_id)
        tag_names = [tag['tag_name'] for tag in tags]
        df_data.loc[index,'tagnames'] = ', '.join(tag_names)
    return df_data

def main():

    settings_cols= st.columns(2)
    with settings_cols[0]:
        N_of_cols = st.slider('Number of columns to display images',1,8,4,step=1)
    with settings_cols[1]:
        preview_size = st.slider('set preview size',540,1080,1080,step=540)
    search_input = st.text_input('Search for art!',value='',key='search_input')

    df_data = get_preview_index(preview_size,DB_HOST)
    print(f'Found {len(df_data)} files in storage')
    #Gotta build a materilzed view for tag mapping later!!!
    df_data = df_data.head(300)

    df_data = get_tags_from_id(df_data)
    print("fetched tags")


    if search_input =='':
        # get 25 random files from df_data
        df_start = df_data.sample(n=25)
    else:
        output_search_str, output_aslist = modulate_search_phrase(search_input)
        if len(output_aslist) == 1:
            threshold = 1
        else:
            threshold =  len(output_aslist) * 2 // 3


        def count_matches(row_tags):
            matches = re.findall(output_search_str, row_tags)
            return len(set(matches))


        df_data['match_count'] = df_data['tagnames'].apply(count_matches)
        df_start = df_data[df_data['match_count'] >= threshold]
        df_start = df_start.sort_values(by='match_count', ascending=False).drop(columns=['match_count'])
        st.write(f'''found {len(df_start)} art pieces''')

        #df_start = df_data.loc[df_data['tagnames'].str.contains(output_search_str, flags= re.IGNORECASE, regex=True)]
        if len(df_start) ==0:
            st.write("No results found")
            sleep(5)
            search_input =''
        elif len(df_start) >100:
            df_start = df_start.sample(n=100)


    cols = st.columns(N_of_cols)


    with ThreadPoolExecutor() as executor:
        futures = []
        for _, row in df_start.iterrows():
            file_id = row["fileid"]
            file_path = row["preview_url"]
            futures.append(executor.submit(get_images, file_id, file_path))

        results = {}
        for future in as_completed(futures):
            file_id, file_in_memory = future.result()
            results[file_id] = file_in_memory

    for idx, col in enumerate(cols):
        with col:
            len_col = len(df_start) // len(cols)
            start_idx = idx * len_col
            end_idx = (idx + 1) * len_col if idx != len(cols) - 1 else len(df_start)
            display_data = df_start[start_idx:end_idx]

            for _, row in display_data.iterrows():
                file_id = row["fileid"]
                img = results.get(file_id)
                if img:
                    st.image(img.read())
                    st.write(df_start.loc[_, 'tagnames'])




main()

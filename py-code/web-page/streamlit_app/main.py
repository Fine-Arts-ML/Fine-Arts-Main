import streamlit as st
from streamlit_dynamic_filters import DynamicFilters
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


    with st.sidebar:
        settings_cols= st.columns(2)
        with settings_cols[0]:
            #N_of_cols = st.slider('Number of columns to display images',1,8,4,step=1)
            N_of_cols = st.sidebar.selectbox('columns to display', options = [2,4,8])
        with settings_cols[1]:
            #preview_size = st.slider('set preview size',540,1080,1080,step=540)
            preview_size = st.sidebar.selectbox('Image quality', options = [540,256,1080])
        df_data = get_preview_index(preview_size,DB_HOST)
        print(f'Found {len(df_data)} files in storage')
        #Gotta build a materilzed view for tag mapping later!!!
        df_data = df_data.head(200)
        df_data = get_tags_from_id(df_data)
        search_method = st.sidebar.radio('Search method', options = ['Free text','Tag filter'])
        if search_method == 'Free text':
            search_input = st.text_input('Search for art!',value='',key='search_input')
            df_start, df_data = free_text_search_func(df_data, search_input)
        elif search_method == 'Tag filter':
            df_colors = get_availible_colors()
            color_picker = DynamicFilters(df_colors, filters=['Color'])
            color_picker.display_filters()
            df_chosen_colors = color_picker.filter_df()
            search_input = df_chosen_colors["Color"]
            df_start, df_data = color_search_func(df_data, search_input)

            if len(df_start) >= 5:
                df_rest_o_tags = button_tag_list(df_start)
                tag_selection = st.pills('Tags',df_rest_o_tags, selection_mode='multi')
                if len(tag_selection) >=1:
                    search_input = df_chosen_colors["Color"].to_list()
                    search_input = search_input + tag_selection
                    df_start, df_data = color_search_func(df_data, search_input)

        else:
            st.write('Please choose a search method')
            search_input = ''

    #st.table(df_start.head(5))
   

    #df_data = get_tags_from_id(df_data)
    print("fetched tags")

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
                    with st.container():
                        st.image(img.read())
                        with st.expander("Tags"):
                            st.write(df_start.loc[_, 'tagnames'])




main()

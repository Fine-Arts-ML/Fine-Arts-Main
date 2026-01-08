import streamlit as st
from streamlit_dynamic_filters import DynamicFilters
from psql_con import *
from webdav_handler import *
from dotenv import load_dotenv
from search_func import *
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import concurrent.futures
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


def increment_counter(increment_value=0):
    st.session_state.count += increment_value
    return st.session_state.count

def decrement_counter(decrement_value=0):
	st.session_state.count -= decrement_value
	return st.session_state.count

def active_tags(tags):
    st.session_state.active_tags = tags
    return st.session_state.active_tags

def pills(avail_tags, df_start, color_selection):
    tag_selection =st.pills('Tags',avail_tags, selection_mode='multi')
    df_start, avail_tags, tag_selection = filter_fragment(df_start, color_selection ,tag_selection)
    st.write(tag_selection)
    st.write(avail_tags)
    return df_start

@st.fragment
def filter_fragment(df_start, color_selection ,tag_selection):
    avail_tags = button_tag_list(df_start)
    
    search_input = color_selection["color_name"].to_list() + tag_selection
    df_start, df_data = color_search_func(df_start, search_input)
    st.write(df_start)
    return df_start, avail_tags, tag_selection

def filter_color(df_start, color_selection):
    avail_tags = button_tag_list(df_start)
    search_input = color_selection["color_name"].to_list()
    df_start, df_data = color_search_func(df_start, search_input)
    return df_start, avail_tags

def main():

    
    if 'count' not in st.session_state:
        st.session_state.count = 0  


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
        #Gotta build a (materilzed) view for tag mapping later!!!
        #df_data = df_data.head(500)
        df_data = get_tags_from_id(df_data)
       
        search_method = st.sidebar.radio('Search method', options = ['Free text','Tag filter'])
        if search_method == 'Free text':
            search_input = st.text_input('Search for art!',value='',key='search_input')
            df_start, df_data = free_text_search_func(df_data, search_input)
        elif search_method == 'Tag filter':
            #df_colors = get_availible_colors()
            color_picker = DynamicFilters(get_availible_colors(), filters=['color_name'])
            color_picker.display_filters()
            df_chosen_colors = color_picker.filter_df()
            search_input = df_chosen_colors["color_name"]
            df_start, df_data = color_search_func(df_data, search_input)
            

            if len(df_start) >= 1:
                if color_picker:
                    df_start, avail_tags = filter_color(df_start, df_chosen_colors)

            df_start = pills(avail_tags, df_start, df_chosen_colors)
            
            #    df_start, avail_tags, tag_selection = filter_fragment(df_start, df_chosen_colors,tag_selection)
            

           # def tag_multi_select(df_start, df_chosen_colors, avail_tags):
            #    
            #    tag_selection =st.pills('Tags',avail_tags, selection_mode='multi')
            #    if tag_selection:
            #        avail_tags = button_tag_list(df_start)
            #        df_start, avail_tags = filter_fragment(df_start, df_chosen_colors,tag_selection)
            #    return df_start, avail_tags
                
            #df_start, avail_tags = tag_multi_select(df_start, df_chosen_colors, avail_tags)

            
 
            

        else:
            st.write('Please choose a search method')
            search_input = ''
  
   # st.table(df_start.head(5))
   
    #df_data = get_tags_from_id(df_data)
    print("fetched tags")

    cols = st.columns(N_of_cols)
 
    # If more than 12 images, show next button
    if len(df_start)>12:
        if st.session_state.count <12:
            with st.container(horizontal_alignment='center'):
                st_nav_left, fil1, res_counter , fill2 ,st_nav_right = st.columns(5,width='stretch')
                with res_counter:
                    st.write(f'''{st.session_state.count} :material/last_page: {st.session_state.count+12} ''')
                with st_nav_right:
                    st.button('Next :material/chevron_right:',on_click=increment_counter,
                        kwargs=dict(increment_value=12),use_container_width=True)
        else:
            with st.container(horizontal_alignment='center'):
                st_nav_left, fil1, res_counter , fill2 ,st_nav_right = st.columns(5,width='stretch')
                with st_nav_left:
                    st.button(':material/chevron_left: Previous', on_click=decrement_counter,
                        kwargs=dict(decrement_value=12),use_container_width=True)
                with res_counter:
                        st.write(f'''  {st.session_state.count} :material/last_page: {st.session_state.count+12} ''')
                with st_nav_right:
                    st.button('Next :material/chevron_right:',on_click=increment_counter,
                        kwargs=dict(increment_value=12),use_container_width=True)




    df_start_chunk = df_start[st.session_state.count:st.session_state.count+12]

    print(st.session_state.count)
 


    with ThreadPoolExecutor() as executor:
        futures = []
        for _, row in df_start_chunk.iterrows():
            file_id = row["fileid"]
            file_path = row["preview_url"]
            futures.append(executor.submit(get_images, file_id, file_path))

        results = {}
        for future in as_completed(futures):
            file_id, file_in_memory = future.result()
            results[file_id] = file_in_memory

    for idx, col in enumerate(cols):
        with col:
            len_col = len(df_start_chunk) // len(cols)
            start_idx = idx * len_col
            end_idx = (idx + 1) * len_col if idx != len(cols) - 1 else len(df_start_chunk)
            display_data = df_start_chunk[start_idx:end_idx]

            for _, row in display_data.iterrows():
                file_id = row["fileid"]
                img = results.get(file_id)
                if img:
                    with st.container():
                        st.caption(f'''{df_start_chunk.loc[_, 'name'].replace('.jpg', '')}''')
                        st.image(img.read())        
                        
                        with st.expander("Details"):
                   
                            with st.expander("Tags", icon=':material/crossword:'):
                                 st.write(df_start_chunk.loc[_, 'tagnames'])
                            st.link_button(
                            url=make_img_link(df_start_chunk.loc[_, 'path'],file_id),
                            type="primary",
                            icon=":material/document_search:",
                            label="Download Image",
                            width="stretch"
                            )


                        




main()

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


if "selected_tags" not in st.session_state:
    st.session_state.selected_tags = []
if "selected_color" not in st.session_state:
    st.session_state.selected_color = []
if 'avail_colors' not in st.session_state:
    st.session_state.avail_colors = []
if 'count' not in st.session_state:
    st.session_state.count = 0  

def main():

    with st.sidebar:
        settings_cols= st.columns(2)
        with settings_cols[0]:
            N_of_cols = st.sidebar.selectbox('columns to display', options = [2,4,8])
        with settings_cols[1]:
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
            #show reset button when filters get populated > 1
            if len(st.session_state.selected_color) or len(st.session_state.selected_tags) >=1:
                #st.button('Reset Search',on_click=reset_search, icon=':material/reset_settings:')
                st.pills('',[':material/reset_settings: Reset Search'],on_change=reset_search)

            #get all colors from db as set  
            set_all_colors = get_availible_colors()
            #initial loading of dataset
            df_start = filter_for_color(df_data, st.session_state.selected_color)

            #load availible tags from either initial dataset or filtered dataset
            set_start_tags = set()
            if st.session_state.selected_color ==[]:
                for col in df_data.tagnames:
                    set_start_tags.update(col.split(','))
            else:
                for col in df_start.tagnames:
                     set_start_tags.update(col.split(','))
            #clean up set, so it can  be used for comparison functions
            set_start_tags = {item.strip(',').strip()for item in set_start_tags}
            #get all colors from dataset, either initial or filtered dataset
            st.session_state.avail_colors = set_all_colors.intersection(set_start_tags)
            st.session_state.selected_color = [color for color in st.session_state.selected_color if color in set_all_colors]
            #actual Pills for color, adjusment for whats displayed is on the fly via st.session_state
            st.pills(":material/filter_b_and_w: Colors", st.session_state.avail_colors, selection_mode="multi", key="selected_color")


            #get available tags from filtered DataFrame, basically same as above
            df_start = filter_for_tags(df_start, st.session_state.selected_tags)
            avail_tags_uniq = button_tag_list(df_start)
            avail_tags_uniq = set(avail_tags_uniq).difference(st.session_state.avail_colors)         
            #remove any selected tags that are no longer available
            st.session_state.selected_tags = [tag for tag in st.session_state.selected_tags if tag in avail_tags_uniq]

            #pills widget with dynamic options & limit to only selected pills when only one file is left in dataset
            if len(df_start)>1:
                st.pills(":material/crossword: Tags", avail_tags_uniq, selection_mode="multi", key="selected_tags")
            else:
                st.pills(":material/crossword: Tags", st.session_state.selected_tags, selection_mode="multi", key="selected_tags")

       
           
 
            

        else:
            st.write('Please choose a search method')
            search_input = ''
    st.header(f'''Found {len(df_start)} art pieces''',text_alignment='center',divider='rainbow')

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
                        st.write(f'''{st.session_state.count} :material/last_page: {st.session_state.count+12 if len(df_start) >st.session_state.count+12 else len(df_start)}''')
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

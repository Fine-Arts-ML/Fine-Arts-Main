import regex as re
from nltk.corpus import stopwords
import spacy
from time import sleep
import streamlit as st
import pandas as pd


try:
    nlp = spacy.load("en_core_web_trf")
except:
    print('failed to load spacy lemmatizer')
    print('stopping execution')
    sleep(10)

try:
    stop_words = set(stopwords.words('english'))
    stop_words.update(['art','color','colorcomposition'])
except:
    print('failed to load nltk stopwords')
    print('stopping execution')
    sleep(10)


def modulate_search_phrase(input_str):
    input_str = re.sub('[^A-Za-z0-9]+', ' ', input_str)
    input_list = input_str.split()
    input_lemma_list = []
    for word in input_list:
        doc = nlp(word)
        input_lemma_list.append(" ".join([token.lemma_ for token in doc]))
    input_lemma_no_stop = [word for word in input_lemma_list if word not in stop_words]
    output_search_str = '|'.join(input_lemma_no_stop)
   # return input_lemma_no_stop
    return output_search_str, input_lemma_no_stop

def free_text_search_func(df_data, search_input):

    if search_input =='':
        # get 24 random files from df_data
        df_start = df_data.sample(n=24)
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
        #elif len(df_start) >50:
        #    df_start = df_start.head(50)

    return df_start, df_data


def color_search_func(df_data, search_input):
    #print(search_input)
    if len(search_input) == 0 or len(search_input) == 38:
        # get 24 random files from df_data
        df_start = df_data
    else:
        escaped_colors = [re.escape(color) for color in search_input]
        lookaheads = ''.join([f'(?=.*\\b{color}\\b)' for color in escaped_colors])
        pattern = f'\\b{lookaheads}'
        df_start = df_data[df_data['tagnames'].str.contains(pattern, case=False, regex=True)]

        df_start = df_start.sort_values(by='tagnames', ascending=False)

        # Display the number of results found
        print(f"Found {len(df_start)} art pieces")
  
        # Handle edge cases
        if len(df_start) == 0:
            print("No results found")
            df_start = pd.DataFrame()  # Return empty DataFrame
        #elif len(df_start) > 50:
        #    df_start = df_start.head(50)  # Limit to 100 random results

    return df_start, df_data

def button_tag_list(df_start):
    df_rest_o_tags = df_start['tagnames'].str.split(',').explode()
    df_rest_o_tags = df_rest_o_tags.unique()
    df_rest_o_tags = [x.strip(' ') for x in df_rest_o_tags]
    return df_rest_o_tags


def filter_for_tags(df, selected_tags):
    if not selected_tags:
        return df

    else:
        output_search_str = '|'.join(selected_tags)
        def count_matches(row_tags):
            matches = re.findall(output_search_str, row_tags)
            return len(set(matches))
        
        if len(selected_tags) == 1:
            threshold = 1
        else:
            threshold =  len(selected_tags) * 3 // 3
        df['match_count'] = df['tagnames'].apply(count_matches)
        df = df[df['match_count'] >= threshold]
        df = df.sort_values(by='match_count', ascending=False).drop(columns=['match_count'])
        return df




def filter_for_color(df, selected_tags):
    if not selected_tags:
        print('returning df1')
        return df

    else:
        output_search_str = '|'.join(selected_tags)
        def count_matches(row_tags):
            matches = re.findall(output_search_str, row_tags)
            return len(set(matches))
        if len(selected_tags) >=1:
            threshold =1
        else:
            threshold = len(selected_tags)
        threshold =  1
        df['match_count'] = df['tagnames'].apply(count_matches)
        df = df[df['match_count'] >= threshold]
        df = df.sort_values(by='match_count', ascending=False).drop(columns=['match_count'])
        return df


def reset_search():
    st.session_state.selected_tags = []
    st.session_state.selected_color = []
    st.session_state.avail_colors = []



def filter_color(df_start, color_selection):
    avail_tags = button_tag_list(df_start)
    search_input = color_selection["color_name"].to_list()
    df_start, df_data = color_search_func(df_start, search_input)
    return df_start
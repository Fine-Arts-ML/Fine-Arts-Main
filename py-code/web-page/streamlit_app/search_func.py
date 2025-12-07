import regex as re
from nltk.corpus import stopwords
import spacy
from time import sleep


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


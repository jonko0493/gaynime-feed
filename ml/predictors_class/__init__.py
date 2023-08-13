import spacy
from sklearn.base import TransformerMixin
import re
import string

nlp = spacy.load('en_core_web_lg')

# Create list of punctuation marks
punctuations = string.punctuation

stopwords = spacy.lang.en.stop_words.STOP_WORDS

def remove_urls(text):
    text = re.sub(r"\S*https?:\S*", "", text, flags=re.MULTILINE)
    return text

# Creat tokenizer function
def spacy_tokenizer(sentence):
    # Create token object from spacy
    sent_nlp = nlp(sentence)
    # Lemmatize each token and convert each token into lowercase
    tokens = [word.lemma_.lower().strip() if word.lemma_ != "PROPN" else word.lower_ for word in sent_nlp]
    # Remove stopwords
    tokens = [word for word in tokens if word not in stopwords and word not in punctuations]
    # Remove links
    tokens = [remove_urls(word) for word in tokens]
    # Remove bad words
    bad_words = []
    with open("data/filter_slurs.txt", "r") as slur_filter:
        bad_words = [line.rstrip() for line in slur_filter]
    tokens = [token for token in tokens if token not in bad_words]
    for ent in [ent for ent in sent_nlp.ents if ent.label_ != 'CARDINAL' and ent.label_ != 'MONEY' and ent.label_ != 'TIME' and ent.label_ != 'PERCENT' and ent.label_ != 'QUANTITY' and ent.label_ != 'ORDINAL']:
        if ent.text.lower() not in tokens:
            tokens.append(ent.text.lower())
    # return preprocessed list of tokens
    return tokens

def clean_text(text):
    return text.strip().lower()

class predictors(TransformerMixin):
    def transform(self, X, **transform_params):
        # Implement clean_text
        return [clean_text(text) for text in X]
    def fit(self, X, y=None, **fit_params):
        return self
    def get_params(self, deep=True):
        return {}
import pandas as pd
import spacy
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.pipeline import Pipeline
import re
import string
import os
import joblib
from discord_webhook import DiscordWebhook

nlp = spacy.load('en_core_web_sm')

# Create list of punctuation marks
punctuations = string.punctuation

stopwords = spacy.lang.en.stop_words.STOP_WORDS

def remove_urls(text):
    text = re.sub(r"\S*https?:\S*", "", text, flags=re.MULTILINE)
    return text

# Creat tokenizer function
def spacy_tokenizer(sentence):
    # Create token object from spacy
    tokens = nlp(sentence)
    # Lemmatize each token and convert each token into lowercase
    tokens = [word.lemma_.lower().strip() if word.lemma_ != "PROPN" else word.lower_ for word in tokens]
    # Remove stopwords
    tokens = [word for word in tokens if word not in stopwords and word not in punctuations]
    # Remove links
    tokens = [remove_urls(word) for word in tokens]
    # Remove bad words
    bad_words = []
    with open("data/filter_slurs.txt", "r") as slur_filter:
        bad_words = [line.rstrip() for line in slur_filter]
    tokens = [token for token in tokens if token not in bad_words]
    # return preprocessed list of tokens
    return tokens

def clean_text(text):
    return text.strip().lower()

from predictors_class import predictors

bow_vector = CountVectorizer(tokenizer = spacy_tokenizer, ngram_range=(1,1))

from sklearn.svm import SVC
classifier = SVC()

webhook_url = os.environ['DISCORD_WEBHOOK_URL']

all_df = pd.read_json("data/data.json", lines=False)

train_df, test_df = train_test_split(all_df, test_size = 0.01)

X_train = train_df.text
X_test = test_df.text
Y_train = train_df.id
Y_test = test_df.id

pipe_SVM = None
pipe_SVM = Pipeline([("cleaner", predictors()),
            ('vectorizer', bow_vector),
            ('classifier', classifier)])

print("Beginning training")
try:    
    pipe_SVM.fit(X_train, Y_train)

    joblib.dump(pipe_SVM, "model.pkl")

    from sklearn.metrics import classification_report
    predicted = pipe_SVM.predict(X_test)
    print(classification_report(Y_test, predicted))

    webhook = DiscordWebhook(url=webhook_url, content=f"SVM training complete!")
    webhook.execute()
except Exception as e:
    webhook = DiscordWebhook(url=webhook_url, content=f"SVM training failed with: {e}")
    webhook.execute()

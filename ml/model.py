import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.pipeline import Pipeline
import os
import joblib
from discord_webhook import DiscordWebhook

from predictors_class import predictors, spacy_tokenizer

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

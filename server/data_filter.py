from atproto import models
from spacy_langdetect import LanguageDetector
import spacy

from server.logger import logger
from server.database import db, Post
from pymongo import MongoClient
import os

dbhost = "localhost" if os.environ['DB_HOST'] is None else os.environ['DB_HOST']
client = MongoClient(dbhost, 27017)
gaydb = client.gaynime
gaynimes = gaydb.gaynimes

# Needed for unpickling
from predictors_class import predictors, spacy_tokenizer

import joblib
model = joblib.load('/model/model.pkl')

lang_detect = spacy.load('en_core_web_sm')
lang_detect.add_pipe(LanguageDetector(), name='language_detector', last=True)

def get_prediction_below_threshold(tweet):
    probs = model.predict_proba([tweet])[0]
    threshold = float(os.environ['MODEL_THRESHOLD']) if 'MODEL_THRESHOLD' in os.environ else 0.0015
    if any(p > threshold for p in probs):
        return model.classes_[max(enumerate(probs),key=lambda x: x[1])[0]]
    else:
        return 0

def operations_callback(ops: dict) -> None:
    posts_to_create = []
    for created_post in ops['posts']['created']:
        record = created_post['record']
        if record.langs is not None and 'en' in record.langs:
            lang = lang_detect(record.text)._.language
            if lang['language'] == 'en' and lang['score'] > 0.95:
                gay = gaynimes.find_one({"id": int(get_prediction_below_threshold(record.text))})
                if gay and not gay['isAdult']:
                    logger.info(f'Added record containing "{gay["title_romaji"]}"')
                    reply_parent = None
                    if record.reply and record.reply.parent.uri:
                        reply_parent = record.reply.parent.uri

                    reply_root = None
                    if record.reply and record.reply.root.uri:
                        reply_root = record.reply.root.uri

                    post_dict = {
                        'uri': created_post['uri'],
                        'cid': created_post['cid'],
                        'reply_parent': reply_parent,
                        'reply_root': reply_root,
                    }
                    posts_to_create.append(post_dict)

    posts_to_delete = [p['uri'] for p in ops['posts']['deleted']]
    if posts_to_delete:
        Post.delete().where(Post.uri.in_(posts_to_delete))
        logger.info(f'Deleted from feed: {len(posts_to_delete)}')

    if posts_to_create:
        with db.atomic():
            for post_dict in posts_to_create:
                Post.create(**post_dict)
        logger.info(f'Added to feed: {len(posts_to_create)}')

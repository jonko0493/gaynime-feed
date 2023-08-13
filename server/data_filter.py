from atproto import models

from server.logger import logger
from server.database import db, Post
from pymongo import MongoClient
import os

dbhost = "localhost" if os.environ['DB_HOST'] is None else os.environ['DB_HOST']
client = MongoClient(dbhost, 27017)
gaydb = client.gaynime
gaynimes = gaydb.gaynimes

from predictors_class import predictors

import joblib
model = joblib.load('C:/Users/jonko/source/repos/gaynime-feed/data/model.pkl')

def operations_callback(ops: dict) -> None:
    posts_to_create = []
    for created_post in ops['posts']['created']:
        record = created_post['record']
        if record.langs is not None and 'en' in record.langs:
            gay = gaynimes.find_one({"id": model.predict([record.text])[0]})
            if gay:
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

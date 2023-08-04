import regex
import spacy

from atproto import models

from server.logger import logger
from server.database import db, Post
from server.anilist_scraper import gaynimes

sp_en = spacy.load('en_core_web_trf')

def operations_callback(ops: dict) -> None:
    posts_to_create = []
    for created_post in ops['posts']['created']:
        record = created_post['record']
        tweet_en = sp_en(record.text)
        for gay in gaynimes:
            if (
                record.langs is not None and 'en' in record.langs and (gay in [ent.text.lower() for ent in tweet_en.ents if ent.label_ == 'WORK_OF_ART'] or (gay in [token.text.lower() for token in tweet_en if token.pos_ == 'PROPN']))
               ):
                logger.info(f'Added record containing "{gay}"')
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
                break

    posts_to_delete = [p['uri'] for p in ops['posts']['deleted']]
    if posts_to_delete:
        Post.delete().where(Post.uri.in_(posts_to_delete))
        logger.info(f'Deleted from feed: {len(posts_to_delete)}')

    if posts_to_create:
        with db.atomic():
            for post_dict in posts_to_create:
                Post.create(**post_dict)
        logger.info(f'Added to feed: {len(posts_to_create)}')

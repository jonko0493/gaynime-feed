import regex

from atproto import models

from server.logger import logger
from server.database import db, Post
from server.anilist_scraper import gaynimes
from english_words import get_english_words_set

def operations_callback(ops: dict) -> None:
    english_words = get_english_words_set(['web2'], alpha=True, lower=True)
    posts_to_create = []
    for created_post in ops['posts']['created']:
        record = created_post['record']
        for gay in gaynimes:
            if (
                    regex.search(fr"(^|[ ""'\(]){gay}($|[ \.,;:""'\)])", record.text.lower()) and record.langs is not None and len(record.langs) > 0 and
                    (('en' in record.langs and ((gay not in english_words and not (len(gay.split(' ')) == 2 and all(gay_word in english_words for gay_word in gay.split(' '))) and not gay.isdigit()) or ("anime" in record.text.lower() or "manga" in record.text.lower())))
                    or ('ja' in record.langs and len(gay) >= 3 and record.embed is not None))
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

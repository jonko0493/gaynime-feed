from atproto import models

from server.logger import logger
from server.database import db, Post
from server.anilist_scraper import gaynimes, WeightedAttribute
from server.nlp import sp_en

weight_threshold = 3.0

hardcoded_weights = [
    WeightedAttribute('yuri', 100.0),
    WeightedAttribute('yaoi', 100.0),
    WeightedAttribute('boys\' love', 100.0),
    WeightedAttribute('girls\' love', 100.0),
    WeightedAttribute('anime', 30.0),
    WeightedAttribute('manga', 30.0)
    ]

def operations_callback(ops: dict) -> None:
    posts_to_create = []
    for created_post in ops['posts']['created']:
        record = created_post['record']
        if 'gaynime' in record.text:
            logger.info(f"{tweet_en.text}\t{tweet_en.ents}\t{', '.join(token.pos_ for token in tweet_en)}")
        if record.langs is not None and 'en' in record.langs: # (gay in [ent.text.lower() for ent in tweet_en.ents if ent.label_ == 'WORK_OF_ART' or ent.label_ == 'PRODUCT'] or (gay in [token.text.lower() for token in tweet_en if token.pos_ == 'PROPN' and not token.is_oov and len(token.text) > 2]))
            tweet_en = sp_en(record.text)
            text_ents = [ent.text.lower() for ent in tweet_en.ents if ent.label_ != 'CARDINAL' and ent.label_ != 'DATE' and ent.label_ != 'MONEY' and ent.label_ != 'TIME' and ent.label_ != 'PERCENT' and ent.label_ != 'QUANTITY' and ent.label_ != 'ORDINAL']
            for gay in gaynimes.find():
                weight = 0
                if gay['title_romaji']['item'] is not None and ((len(gay['title_romaji']['item'].strip().split(' ')) > 1 and gay['title_romaji']['item'] in record.text.lower()) or gay['title_romaji']['item'] in [token.text.lower() for token in tweet_en]):
                        weight += gay['title_romaji']['weight']
                        logger.info(f"Found {gay['title_romaji']}, new weight {weight}")
                if gay['title_english']['item'] is not None and ((len(gay['title_english']['item'].strip().split(' ')) > 1 and gay['title_english']['item'] in record.text.lower()) or gay['title_english']['item'] in [token.text.lower() for token in tweet_en]):
                    weight += gay['title_english']['weight']
                    logger.info(f"Found {gay['title_english']}, new weight {weight}")
                for hashtag in gay['hashtags']:
                    if hashtag['item'] is not None and hashtag['item'].lower() in record.text.lower():
                        weight += hashtag['weight']
                        logger.info(f"Found {hashtag}, new weight {weight}")
                for synonym in gay['synonyms']:
                    if synonym['item'] is not None and (synonym['item'].lower() in text_ents or synonym['item'].lower() in [token.text.lower() for token in tweet_en if token.pos_ == 'NOUN' or token.pos_ == 'PROPN']):
                        weight += synonym['weight']
                        logger.info(f"Found {synonym} new weight {weight}")
                for ent in gay['entities']:
                    if ent['item'] is not None and ent['item'].lower() in text_ents:
                        weight += ent['weight']
                        logger.info(f"Found {ent}, new weight {weight}")
                for character in gay['characters']:
                    if character['name']['item'] is not None and character['name']['item'].lower() in text_ents:
                        weight += character['name']['weight']
                        logger.info(f"Found {character['name']}, new weight {weight}")
                    if character['name_first']['item'] is not None and character['name_first']['item'].lower() in text_ents:
                        weight += character['name_first']['weight']
                        logger.info(f"Found {character['name_first']}, new weight {weight}")
                    if character['name_last']['item'] is not None and character['name_last']['item'].lower() in text_ents:
                        weight += character['name_last']['weight']
                        logger.info(f"Found {character['name_last']}, new weight {weight}")
                    if character['name_pref']['item'] is not None and character['name_pref']['item'].lower() in text_ents:
                        weight += character['name_pref']['weight']
                        logger.info(f"Found {character['name_pref']}, new weight {weight}")
                    
                if weight > weight_threshold:
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

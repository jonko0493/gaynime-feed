import os
from pymongo import MongoClient
import logging
import time
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from gql.transport.requests import log as gql_logger
from tmdbv3api import Movie, Season, Discover

if __name__ == '__main__':
    import spacy
    sp_en = spacy.load('en_core_web_trf')
else:
    from server.nlp import sp_en
    from server.logger import logger

dbhost = "localhost" if os.environ['DB_HOST'] is None else os.environ['DB_HOST']
client = MongoClient(dbhost, 27017)
gaydb = client.gaynime
gaynimes = gaydb.gaynimes

baddb = client.baddb
badmovies = baddb.movies
badtv = baddb.tv
badanime = baddb.anime

transport = RequestsHTTPTransport(url="https://graphql.anilist.co", verify=True, retries=3)
gql_logger.setLevel(logging.WARNING)
client = Client(transport=transport, fetch_schema_from_transport=True)

class WeightedAttribute:
    def __init__(self, item, weight):
        self.item = item
        self.weight = weight   
    def db(self):
        return {
            "item": self.item,
            "weight": self.weight,
        }

class Character:
    def __init__(self, character):
        self.name = WeightedAttribute(None, 0.0) if character['name']['full'] is None or character['name']['full'] == '' else WeightedAttribute(character['name']['full'].lower(), 100.0)
        self.name_first = WeightedAttribute(None, 0.0) if character['name']['first'] is None or character['name']['first'] == '' else WeightedAttribute(character['name']['first'].lower(), 100.0)
        self.name_last = WeightedAttribute(None, 0.0) if character['name']['last'] is None or character['name']['last'] == '' else WeightedAttribute(character['name']['last'].lower(), 100.0)
        self.name_pref = WeightedAttribute(None, 0.0) if character['name']['userPreferred'] is None or character['name']['userPreferred'] == '' else WeightedAttribute(character['name']['userPreferred'].lower(), 100.0)
    def db(self):
        return {
            "name": self.name.db(),
            "name_first": self.name_first.db(),
            "name_last": self.name_last.db(),
            "name_pref": self.name_pref.db(),
        }

class Gaynime:
    def __init__(self, media):
        self.id = media['id']
        self.title_romaji =  WeightedAttribute(None, 0.0) if media['title']['romaji'] is None or media['title']['romaji'] == '' else WeightedAttribute(media['title']['romaji'].strip().lower(), 100.0)
        self.title_english = WeightedAttribute(None, 0.0) if media['title']['english'] is None or media['title']['english'] == '' else WeightedAttribute(media['title']['english'].strip().lower(), 100.0)
        self.title_native = WeightedAttribute(None, 0.0) if media['title']['native'] is None or media['title']['native'] == '' else WeightedAttribute(media['title']['native'].strip().lower(), 100.0)
        self.hashtags = [WeightedAttribute(None, 0.0)] if media['hashtag'] is None else [WeightedAttribute(hashtag.strip()[1:].lower(), 100.0) for hashtag in media['hashtag'].split(' ') if hashtag.strip() != '']
        self.synonyms = [WeightedAttribute(synonym.strip().lower(), 100.0) for synonym in media['synonyms'] if len(synonym) > 2]
        if self.title_english.item is not None and len(self.title_english.item.split(':')) > 1:
            self.synonyms.append(WeightedAttribute(self.title_english.item.split(':')[-1].strip().lower(), 100.0))
        self.entities = []
        self.characters = []
        for character in media['characters']['nodes']:
            self.characters.append(Character(character))
        if media['description'] is not None:
            nlp_desc = sp_en(media['description'])
            for ent in nlp_desc.ents:
                if ent.label_ != 'CARDINAL' and ent.label_ != 'DATE' and ent.label_ != 'MONEY' and ent.label_ != 'TIME' and ent.label_ != 'PERCENT' and ent.label_ != 'QUANTITY' and ent.label_ != 'ORDINAL' and ent.text not in [item.item for item in self.entities] and ent.text not in [char.name for char in self.characters] and ent.text not in [char.name_first for char in self.characters] and ent.text not in [char.name_last for char in self.characters] and ent.text not in [char.name_pref for char in self.characters]:
                    self.entities.append(WeightedAttribute(ent.text.lower(), 50.0))
    def db(self):
        return {
            "id": self.id,
            "title_romaji": self.title_romaji.db(),
            "title_english": self.title_english.db(),
            "title_native": self.title_native.db(),
            "hashtags": [hashtag.db() for hashtag in self.hashtags],
            "synonyms": [synonym.db() for synonym in self.synonyms],
            "entities": [ent.db() for ent in self.entities],
            "characters": [character.db() for character in self.characters]
        }

def scrape():
    tags_to_scrape = [ "Yuri", "Boys' Love" ]
    for tag in tags_to_scrape:
        page = 1
        hasNextPage = True
        while hasNextPage:
            query = gql(
            """
            query ($tag: String!, $page: Int)
            {
                Page(page: $page, perPage: 50)
                {
                    pageInfo
                    {
                        hasNextPage
                    }
                    media (tag_in: [$tag], minimumTagRank: 50, popularity_greater: 99)
                    {
                        id
                        title
                        {
                            romaji
                            english
                            native
                        }
                        hashtag
                        description
                        synonyms
                        characters
                        {
                            nodes
                            {
                                name
                                {
                                    full
                                    first
                                    last
                                    userPreferred
                                }
                                description
                            }
                        }
                    }
                }
            }
            """
            )
            params = { "tag": tag, "page": page }
            data = client.execute(query, params)
            hasNextPage = data['Page']['pageInfo']['hasNextPage']
            for media in data['Page']['media']:
                if not gaynimes.find_one({'id': media['id']}):
                    if len(media['characters']['nodes']) > 0:
                        gaynime = Gaynime(media)
                        gaynimes.insert_one(gaynime.db())
                        log_mes = f"Added {media['title']}"
                        if __name__ == '__main__':
                            print(log_mes)
                        else:
                            logger.info(log_mes)
            log_mes = f"Scraped page {page} of tag {tag}..."
            if __name__ == '__main__':
                print(log_mes)
            else:
                logger.info(log_mes)
            page += 1
            time.sleep(1)

def scrape_bad():
    discover = Discover()
    discover.api_key = os.environ['TMDB_API_KEY']
    discover.language = 'en'
    discover.debug = True
    movie_search = Movie()
    movie_search.api_key = os.environ['TMDB_API_KEY']
    movie_search.language = 'en'
    movie_search.debug = True
    for page in range(1, 51):
        movies = discover.discover_movies({
            'page': page,
            'without_keywords': 'anime',
            'sort_by': 'popularity.desc',
        })
        for movie in movies:
            if not badmovies.find_one({'id': movie.id}):
                credits = movie_search.credits(movie.id)
                nlp_desc = sp_en(movie.overview)
                characters = [credit.character.lower() for credit in credits if hasattr(credit, 'character')]
                badmovies.insert_one({
                    "id": movie.id,
                    "title": movie.title.lower(),
                    "characters": characters,
                    "entities": [ent.text.lower() for ent in nlp_desc.ents if ent.label_ != 'CARDINAL' and ent.label_ != 'DATE' and ent.label_ != 'MONEY' and ent.label_ != 'TIME' and ent.label_ != 'PERCENT' and ent.label_ != 'QUANTITY' and ent.label_ != 'ORDINAL' and ent.text.lower() not in characters]
                })
        log_mes = f"Finished scraping movies page {page}"
        if __name__ == '__main__':
            print(log_mes)
        else:
            logger.info(log_mes)
    tv_search = Season()
    tv_search.api_key = os.environ['TMDB_API_KEY']
    tv_search.language = 'en'
    tv_search.debug = True
    for page in range(1, 51):
        tvs = discover.discover_tv_shows({
            'page': page,
            'with_original_language': 'en',
            'without_keywords': 'anime',
            'sort_by': 'popularity.desc',
        })
        for tv in tvs:
            if not badtv.find_one({'id': tv.id}):
                nlp_desc = sp_en(tv.overview)
                characters = []
                try:
                    credits = tv_search.credits(tv.id, 1)
                    characters = [credit.character.lower() for credit in credits if hasattr(credit, 'character')]
                except:
                    log_mes = f"No season found for show {tv.name}"
                    if __name__ == '__main__':
                        print(log_mes)
                    else:
                        logger.info(log_mes)
                badtv.insert_one({
                    "id": tv.id,
                    "title": tv.name.lower(),
                    "characters": characters,
                    "entities": [ent.text.lower() for ent in nlp_desc.ents if ent.label_ != 'CARDINAL' and ent.label_ != 'DATE' and ent.label_ != 'MONEY' and ent.label_ != 'TIME' and ent.label_ != 'PERCENT' and ent.label_ != 'QUANTITY' and ent.label_ != 'ORDINAL' and ent.text.lower() not in characters]
                })
        log_mes = f"Finished scraping TV page {page}"
        if __name__ == '__main__':
            print(log_mes)
        else:
            logger.info(log_mes)  
    for page in range(1, 51):
        query = gql(
        """
        query ($page: Int)
        {
            Page(page: $page, perPage: 50)
            {
                pageInfo
                {
                    hasNextPage
                }
                media (tag_not_in: ["Yuri", "Boys' Love"], minimumTagRank: 50, popularity_greater: 1999)
                {
                    id
                    title
                    {
                        romaji
                        english
                        native
                    }
                    hashtag
                    description
                    synonyms
                    characters
                    {
                        nodes
                        {
                            name
                            {
                                full
                                first
                                last
                                userPreferred
                            }
                            description
                        }
                    }
                }
            }
        }
        """
        )
        params = { "page": page }
        data = client.execute(query, params)
        for media in data['Page']['media']:
            if not badanime.find_one({'id': media['id']}):
                if len(media['characters']['nodes']) > 0:
                    banime = Gaynime(media)
                    badanime.insert_one(banime.db())
        log_mes = f"Scraped anime page {page}..."
        if __name__ == '__main__':
            print(log_mes)
        else:
            logger.info(log_mes)

def weight():
    other_tokens = []
    for movie in badmovies.find():
        other_tokens.append(movie['title'])
        for character in movie['characters']:
            other_tokens.append(character)
        for entity in movie['entities']:
            other_tokens.append(entity)
    for tv in badtv.find():
        other_tokens.append(tv['title'])
        for character in tv['characters']:
            other_tokens.append(character)
        for entity in tv['entities']:
            other_tokens.append(entity)
    for anime in badanime.find():
        other_tokens.append(anime['title_romaji']['item'])
        if anime['title_english'] is not None:
            other_tokens.append(anime['title_english']['item'])
        for hashtag in anime['hashtags']:
            if hashtag['item'] is not None:
                other_tokens.append(hashtag['item'].lower())
        for synonym in anime['synonyms']:
            other_tokens.append(synonym['item'].lower())
        for character in anime['characters']:
            if character['name']['item'] is not None:
                other_tokens.append(character['name']['item'].lower())
            if character['name_first']['item'] is not None:
                other_tokens.append(character['name_first']['item'].lower())
            if character['name_last']['item'] is not None:
                other_tokens.append(character['name_last']['item'].lower())
            if character['name_pref']['item'] is not None:
                other_tokens.append(character['name_pref']['item'].lower())
    log_mes = "Finished adding other tokens to check"
    if __name__ == '__main__':
        print(log_mes)
    else:
        logger.info(log_mes)   
    for gay in gaynimes.find():
        if gay['title_romaji']['item'] in other_tokens:
            gay['title_romaji']['weight'] /= 2
        else:
            gay['title_romaji']['weight'] *= 2
        if gay['title_english']['item'] is not None:
            if gay['title_english']['item'] in other_tokens:
                gay['title_english']['weight'] /= 2
            else:
                gay['title_english']['weight'] *= 2
        for hashtag in gay['hashtags']:
            if hashtag['item'] is not None:
                if hashtag['item'].lower() in other_tokens:
                    hashtag['weight'] /= 2
                else:
                    hashtag['weight'] *= 2
        for synonym in gay['synonyms']:
            if synonym['item'] is not None:
                if synonym['item'].lower() in other_tokens:
                    synonym['weight'] /= 2
                else:
                    synonym['weight'] *= 2
        for character in gay['characters']:
            if character['name']['item'] is not None:
                if character['name']['item'].lower() in other_tokens:
                    character['name']['weight'] /= 2
                else:
                    character['name']['weight'] *= 2
            if character['name_first']['item'] is not None:
                if character['name_first']['item'].lower() in other_tokens:
                    character['name_first']['weight'] /= 2
                else:
                    character['name_first']['weight'] *= 2
            if character['name_last']['item'] is not None:
                if character['name_last']['item'].lower() in other_tokens:
                    character['name_last']['weight'] /= 2
                else:
                    character['name_last']['weight'] *= 2
            if character['name_pref']['item'] is not None:
                if character['name_pref']['item'].lower() in other_tokens:
                    character['name_pref']['weight'] /= 2
                else:
                    character['name_pref']['weight'] *= 2
        log_mes = f"Finished weight {gay['title']}"
        if __name__ == '__main__':
            print(log_mes)
        else:
            logger.info(log_mes)

if __name__ == '__main__':
    weight()
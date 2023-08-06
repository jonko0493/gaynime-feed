import os
from pymongo import MongoClient
import logging
import time
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from gql.transport.requests import log as gql_logger

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
        self.name = WeightedAttribute(None, 0.0) if character['name']['full'] is None else WeightedAttribute(character['name']['full'].lower(), 1.0)
        self.name_first = WeightedAttribute(None, 0.0) if character['name']['first'] is None else WeightedAttribute(character['name']['first'].lower(), 1.0)
        self.name_last = WeightedAttribute(None, 0.0) if character['name']['last'] is None else WeightedAttribute(character['name']['last'].lower(), 1.0)
        self.name_pref = WeightedAttribute(None, 0.0) if character['name']['userPreferred'] is None else WeightedAttribute(character['name']['userPreferred'].lower(), 1.0)
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
        self.title_romaji =  WeightedAttribute(None, 0.0) if media['title']['romaji'] is None else WeightedAttribute(media['title']['romaji'].strip().lower(), 1.0)
        self.title_english = WeightedAttribute(None, 0.0) if media['title']['english'] is None else WeightedAttribute(media['title']['english'].strip().lower(), 1.0)
        self.title_native = WeightedAttribute(None, 0.0) if media['title']['native'] is None else WeightedAttribute(media['title']['native'].strip().lower(), 1.0)
        self.hashtags = [WeightedAttribute(None, 0.0)] if media['hashtag'] is None else [WeightedAttribute(hashtag.strip()[1:].lower(), 1.0) for hashtag in media['hashtag'].split(' ')]
        self.synonyms = [WeightedAttribute(synonym.strip().lower(), 1.0) for synonym in media['synonyms'] if len(synonym) > 2]
        self.entities = []
        self.characters = []
        if media['description'] is not None:
            nlp_desc = sp_en(media['description'])
            for ent in nlp_desc.ents:
                if ent.label_ != 'CARDINAL' and ent.label_ != 'DATE' and ent.label_ != 'MONEY' and ent.label_ != 'TIME' and ent.label_ != 'PERCENT' and ent.label_ != 'QUANTITY' and ent.label_ != 'ORDINAL' and ent.text not in [item.item for item in self.entities]:
                    self.entities.append(WeightedAttribute(ent.text.lower(), 1.0))
            for character in media['characters']['nodes']:
                self.characters.append(Character(character))
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

def weight():
    return

if __name__ == '__main__':
    scrape()
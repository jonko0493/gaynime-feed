import os
from pymongo import MongoClient
import logging
import time
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from gql.transport.requests import log as gql_logger
import csv

if __name__ != '__main__':
    from server.logger import logger

dbhost = "localhost" if os.environ['DB_HOST'] is None else os.environ['DB_HOST']
client = MongoClient(dbhost, 27017)
gaydb = client.gaynime
gaynimes = gaydb.gaynimes
anilistreviews = gaydb.anilistreviews
relations = gaydb.relations

otherdb = client.others
otheranimes = otherdb.otheranimes


transport = RequestsHTTPTransport(url="https://graphql.anilist.co", verify=True, retries=3)
gql_logger.setLevel(logging.WARNING)
client = Client(transport=transport, fetch_schema_from_transport=True)

class Character:
    def __init__(self, character):
        self.name = ""
        if character['name']['full'] is not None:
            self.name = character['name']['full']
        self.name_first = ""
        if character['name']['first'] is not None:
            self.name_first = character['name']['first'].lower()
        self.name_last = ""
        if character['name']['last'] is not None:
            self.name_last = character['name']['last'].lower()
        self.name_pref = ""
        if character['name']['userPreferred'] is not None:
            self.name_pref = character['name']['userPreferred']
    def db(self):
        return {
            "name": self.name,
            "name_first": self.name_first,
            "name_last": self.name_last,
            "name_pref": self.name_pref,
        }

class Gaynime:
    def __init__(self, media):
        self.id = media['id']
        self.idMal = media['idMal']
        self.type = media['type'].lower()
        self.isAdult = media['isAdult']
        self.title_romaji =  media['title']['romaji']
        self.title_english = media['title']['english']
        self.title_native = media['title']['native']
        if media['hashtag'] is not None:
            self.hashtags = [hashtag.strip() for hashtag in media['hashtag'].split(' ') if hashtag.strip() != '']
        else:
            self.hashtags = []
        self.synonyms = [synonym.strip() for synonym in media['synonyms'] if len(synonym) > 2]
        self.entities = []
        self.characters = []
        for character in media['characters']['nodes']:
            self.characters.append(Character(character))
        self.description = media['description']

    def db(self):
        return {
            "id": self.id,
            "idMal": self.idMal,
            "type": self.type,
            "isAdult": self.isAdult,
            "title_romaji": self.title_romaji,
            "title_english": self.title_english,
            "title_native": self.title_native,
            "hashtags": [hashtag for hashtag in self.hashtags],
            "synonyms": [synonym for synonym in self.synonyms],
            "description": self.description,
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
                        idMal
                        type
                        isAdult
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

def consolidate_collection(collection):
    already_processed = []
    types = ['anime', 'manga'] # We do it this way so that we make the anime the parent when possible
    for media_type in types:
        for media in collection.find({'type': media_type}):
            query = gql(
            """
            query ($mediaId: Int)
            {
                Page
                {
                    media(id: $mediaId)
                    {
                        id
                        idMal
                        relations
                        {
                            edges
                            {
                                relationType
                                node
                                {
                                    id
                                    idMal
                                }
                            }
                        }
                    }
                }
            }
            """
            )
            params = { "mediaId": media['id'] }
            data = client.execute(query, params)
            if any(relation['relationType'] == 'PARENT' for relation in data['Page']['media'][0]['relations']['edges']):
                continue
            pid = media['id']
            pidMal = media['idMal']
            if relations.find_one({"cid": pid}):
                pidMal = relations.find_one({"cid": pid})['pidMal']
                pid = relations.find_one({"cid": pid})['pid']
            for relation in data['Page']['media'][0]['relations']['edges']:
                if relation['node']['id'] not in already_processed:
                    already_processed.append(relation['node']['id'])
                    relations.insert_one({"pid": pid, "pidMal": pidMal, "cid": relation['node']['id'], "cidMal": relation['node']['idMal']})
            time.sleep(1)
            print(f"Consolidated collection for {media['title_romaji']}")

def scrape_reviews(collection):
    for media in collection.find():
        page = 1
        hasNextPage = True
        while hasNextPage:
            query = gql(
            """
            query ($page: Int, $mediaId: Int)
            {
                Page(page: $page, perPage: 50)
                {
                    pageInfo
                    {
                        hasNextPage
                    }
                    reviews(mediaId: $mediaId)
                    {
                        id
                        body
                    }
                }
            }
            """
            )
            params = { "page": page, "mediaId": media['id'] }
            data = client.execute(query, params)
            hasNextPage = data['Page']['pageInfo']['hasNextPage']
            for review in data['Page']['reviews']:
                anilistreviews.insert_one({"media": media['id'], "review": review['body']})
            page += 1
            time.sleep(1)
        print(f"Scraped reviews for {media['title_romaji']}")

def scrape_from_mal(mal_csv):
    animes_csv = csv.reader(open(mal_csv, 'r', encoding='utf-8'))
    for anime in animes_csv:
        if anime[0] != 'uid':
            query = gql(
            """
            query ($idMal: Int)
            {
                Media(idMal: $idMal, type: ANIME)
                {
                    id
                    idMal
                    popularity
                    title
                    {
                        romaji
                    }
                }
            }
            """
            )
            params = { "idMal": int(anime[0]) }
            try:
                data = client.execute(query, params)
                otheranimes.insert_one({ "id": data['Media']['id'], "idMal": data['Media']['idMal'], "popularity": data['Media']['popularity'] })
                print(f"Added anime reference for {data['Media']['title']['romaji']}")
            except:
                print(f"Couldn't find anime {anime[1]}")
            time.sleep(1)

if __name__ == '__main__':
    scrape_from_mal('data/animes.csv')
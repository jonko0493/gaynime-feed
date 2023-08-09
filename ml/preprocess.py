import csv
import json
from pymongo import MongoClient

client = MongoClient()
anilistreviews = client.gaynime.anilistreviews
gaynimes = client.gaynime.gaynimes
relations = client.gaynime.relations

reviews_json = json.load(open('data/reviews.json', 'r'))
animes_json = json.load(open('data/animes.json', 'r'))
reviews_csv = csv.reader(open('data/reviews.csv', 'r', encoding='utf-8'))
animes_csv = csv.reader(open('data/animes.csv', 'r', encoding='utf-8'))
generic_csv = csv.reader(open('data/tweets_generic.csv', encoding='utf-8'))
movies_csv = csv.reader(open('data/tweets_movies.csv', encoding='utf-8'))

review_data = []
mal_review_uids = []

def consolidate_id(idMal):
    relation = relations.find_one({"cidMal": idMal})
    if relation and relation['pidMal'] is not None:
        return relation['pidMal']
    else:
        return idMal

for review in anilistreviews.find():
    idMal = gaynimes.find_one({"id": review['media']})["idMal"]
    if idMal != None:
        review_data.append({"idMal": consolidate_id(int(idMal)), "text": review["review"]})
print("AniList reviews")
for review in reviews_json:
    review_data.append({"idMal": consolidate_id(int(review["anime_uid"])), "text": review["text"]})
    mal_review_uids.append(int(review["uid"]))
print("MAL reviews (gaynime)")
for anime in animes_json:
    if anime["synopsis"] != "":
        review_data.append({"idMal": consolidate_id(int(anime["uid"])), "text": anime["synopsis"]})
print("Mal summaries (gaynime)")
for gaynime in gaynimes.find():
    if gaynime["idMal"] != None:
        review_data.append({"idMal": consolidate_id(gaynime["idMal"]), "text": ' '.join([entities['item'] for entities in gaynime["entities"]])})
print("Anilist summaries")
for review in reviews_csv:
    if review[0] not in mal_review_uids and review[2] != "anime_uid":
        review_data.append({"idMal": consolidate_id(int(review[2])), "text": review[3]})
print("MAL reviews (generic)")
for anime in animes_csv:
    if not gaynimes.find_one({"idMal": anime[0]}) and anime[0] != 'uid':
        review_data.append({"idMal": consolidate_id(int(anime[0])), "text": anime[2]})
print("MAL summaries (generic)")
for tweet in generic_csv:
    if tweet[0] != "textID":
        review_data.append({"idMal": 0, "text": tweet[1]})
print("Tweets generic")
for tweet in movies_csv:
    if tweet[0] != "Tweets":
        review_data.append({"idMal": 0, "text": tweet[0]})
print("Tweets movies")

json.dump(review_data, open('data/data.json', 'w'))
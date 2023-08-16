import csv
import json
from pymongo import MongoClient

client = MongoClient()
anilistreviews = client.gaynime.anilistreviews
gaynimes = client.gaynime.gaynimes
relations = client.gaynime.relations
otheranimes = client.others.otheranimes

reviews_json = json.load(open('data/reviews.json', 'r'))
animes_json = json.load(open('data/animes.json', 'r'))
reviews_csv = csv.reader(open('data/reviews.csv', 'r', encoding='utf-8'))
animes_csv = csv.reader(open('data/animes.csv', 'r', encoding='utf-8'))
generic_csv = csv.reader(open('data/tweets_generic.csv', encoding='utf-8'))
movies_csv = csv.reader(open('data/tweets_movies.csv', encoding='utf-8'))
rt_csv = csv.reader(open('data/rotten_tomatoes_critic_reviews.csv', encoding='utf-8'))
wikipedia_csv = csv.reader(open('data/wikipedia.csv', encoding='utf-8'))
steam_csv = csv.reader(open('data/steam.csv', encoding='utf-8'))
bsky_csv = csv.reader(open('data/bsky_false_positives.csv', encoding='utf-8'))

review_data = []
mal_review_uids = []
mal_review_counts = {}
rt_review_counts = {}

def consolidate_id(id):
    relation = relations.find_one({"cid": id})
    if relation and relation['pid'] is not None:
        return relation['pid']
    else:
        return id

for review in anilistreviews.find():
    if review['media'] != None:
        review_data.append({"id": consolidate_id(review['media']), "text": review["review"]})
print("AniList reviews")
for review in reviews_json:
    anilist_entry = gaynimes.find_one({"idMal": int(review["anime_uid"])})
    if anilist_entry is not None:
        review_data.append({"id": consolidate_id(anilist_entry['id']), "text": review["text"]})
        mal_review_uids.append(int(review["uid"]))
print("MAL reviews (gaynime)")
for anime in animes_json:
    if anime["synopsis"] != "":
        anilist_entry = gaynimes.find_one({"idMal": int(anime["uid"])})
        if anilist_entry:
            if anilist_entry['id'] not in mal_review_counts.keys():
                mal_review_counts[anilist_entry['id']] = 0
            if mal_review_counts[anilist_entry['id']] < 20:
                mal_review_counts[anilist_entry['id']] += 1
                review_data.append({"id": consolidate_id(anilist_entry['id']), "text": anime["synopsis"]})
print("Mal summaries (gaynime)")
for gaynime in gaynimes.find():
    if gaynime["id"] != None:
        review_data.append({"id": consolidate_id(gaynime["id"]), "text": ' '.join([entities['item'] for entities in gaynime["entities"]])})
print("Anilist summaries")
for review in reviews_csv:
    if review[0] not in mal_review_uids and review[2] != "anime_uid":
        anilist_entry = otheranimes.find_one({"idMal": int(review[2])})
        if anilist_entry and anilist_entry['popularity'] > 100000:
            if anilist_entry['id'] not in mal_review_counts.keys():
                mal_review_counts[anilist_entry['id']] = 0
            if mal_review_counts[anilist_entry['id']] < 20:
                mal_review_counts[anilist_entry['id']] += 1
                review_data.append({"id": consolidate_id(anilist_entry['id']), "text": review[3]})
print("MAL reviews (generic)")
for anime in animes_csv:
    if not gaynimes.find_one({"idMal": anime[0]}) and anime[0] != 'uid':
        anilist_entry = otheranimes.find_one({"idMal": int(anime[0])})
        if anilist_entry and anilist_entry['popularity'] > 100000:
            review_data.append({"id": consolidate_id(anilist_entry['id']), "text": anime[2]})
print("MAL summaries (generic)")
for tweet in generic_csv:
    if tweet[0] != "textID":
        review_data.append({"id": 0, "text": tweet[1]})
print("Tweets generic")
for tweet in movies_csv:
    if tweet[0] != "Tweets":
        review_data.append({"id": 0, "text": tweet[0]})
print("Tweets movies")
for review in rt_csv:
    if review[0] != "rotten_tomatoes_link":
        if review[0] not in mal_review_counts.keys():
            mal_review_counts[review[0]] = 0
        if mal_review_counts[review[0]] < 5:
            mal_review_counts[review[0]] += 1
            review_data.append({"id": 0, "text": review[7]})
print("Rotten Tomatoes reviews")
for wiki in wikipedia_csv:
    review_data.append({"id": 0, "text": wiki[0]})
print("Wikipedia articles")
for steam in steam_csv:
    review_data.append({"id": 0, "text": steam[0]})
print("Steam reviews")
for bsky in bsky_csv:
    review_data.append({"id": 0, "text": bsky[0]})
print("Bsky false positives")

json.dump(review_data, open('data/data.json', 'w'), indent=4)
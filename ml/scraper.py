import wikipediaapi
import steamreviews
import csv
import time

def scrape_wikpedia(pages):
    wiki = wikipediaapi.Wikipedia("Gaynime-Feed (jonko0493@protonmail.com)", "en")
    writer = csv.writer(open("data/wikipedia.csv", "w", encoding='utf-8'))
    for page in pages:
        writer.writerow([wiki.page(page).text])
        print(f"Scraped page {page}")
        time.sleep(1)

def scrape_steam_reviews(app_ids):
    writer = csv.writer(open("data/steam.csv", "w", encoding='utf-8'))
    for id in app_ids:
        request_params = {"filter": "all", "day_range": 28, "total_reviews": 10, "language": "english"}
        review_dict, query_count = steamreviews.download_reviews_for_app_id(id, chosen_request_params=request_params)
        for review in review_dict['reviews']:
            writer.writerow([review_dict['reviews'][review]['review']])

if __name__ == '__main__':
    scrape_wikpedia([
        "Lynx",
        "Ash",
        "Fraxinus",
        "Ash Ketchum",
        "Dragon",
        "How To Train Your Dragon",
        "Sigmund Freud",
        "Banana",
        "Tusk",
        
        ])
    # scrape_steam_reviews([
    #     2232840
    # ])
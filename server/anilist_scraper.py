import time
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
from english_words import get_english_words_set

gaynimes = []

transport = AIOHTTPTransport(url="https://graphql.anilist.co")
client = Client(transport=transport, fetch_schema_from_transport=True)

def scrape():
    new_gaynimes = []
    english_words = get_english_words_set(['web2'], alpha=True, lower=True)
    
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
                        currentPage
                        lastPage
                        hasNextPage
                        perPage
                    }
                    media (tag_in: [$tag])
                    {
                        id
                        title
                        {
                            romaji
                            english
                            native
                        }
                        hashtag
                        synonyms
                    }
                }
            }
            """
            )
            params = { "tag": tag, "page": page }
            data = client.execute(query, params)
            hasNextPage = data['Page']['pageInfo']['hasNextPage']
            for media in data['Page']['media']:
                if media['title']['romaji'] is not None:
                    new_gaynimes.append(media['title']['romaji'])
                if media['title']['english'] is not None:
                    new_gaynimes.append(media['title']['english'])
                if media['title']['native'] is not None:
                    new_gaynimes.append(media['title']['native'])
                if media['hashtag'] is not None:
                    new_gaynimes.append(media['hashtag'][1:])
                for synonym in media['synonyms']:
                    if str.lower(synonym) not in english_words: # We exclude synonyms that are just English words
                        new_gaynimes.append(synonym)
            print(f"Scraped page {page} of tag {tag}...")
            page += 1
            time.sleep(2)
    gaynimes[:] = new_gaynimes[:]

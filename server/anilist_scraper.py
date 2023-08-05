import time
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

gaynimes = []

transport = RequestsHTTPTransport(url="https://graphql.anilist.co", verify=True, retries=3)
client = Client(transport=transport, fetch_schema_from_transport=True)

def scrape():
    new_gaynimes = []    
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
                    media (tag_in: [$tag], popularity_greater: 99)
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
                        popularity
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
                    new_gaynimes.append(str.strip(media['title']['romaji']).lower())
                if media['title']['english'] is not None:
                    new_gaynimes.append(str.strip(media['title']['english']).lower())
                if media['title']['native'] is not None:
                    new_gaynimes.append(str.strip(media['title']['native']).lower())
                if media['hashtag'] is not None:
                    new_gaynimes.append(str.strip(media['hashtag'][1:]).lower())
                for synonym in media['synonyms']:
                    if len(synonym) > 2:
                        new_gaynimes.append(str.strip(synonym.lower()))
            print(f"Scraped page {page} of tag {tag}...")
            page += 1
            time.sleep(1)
    gaynimes[:] = list(filter(None, new_gaynimes))

from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests, datetime, os, sys, time, httpx, asyncio
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.env_utils import load_env


def guarded(fn, default="NULL"):
    try:
        return fn()
    except:
        return default


rate_map = {
    "One" : 1,
    "Two" : 2,
    "Three" : 3,
    "Four" : 4,
    "Five" : 5
}

load_env()

index_url = os.getenv("INDEX_URL")
initial_link_for_books = os.getenv("INITIAL_URL")



class BookMetadata(BaseModel):
    timestamp : str
    status : int
    source_url : str


class Book(BaseModel):
    name : str
    description : str
    category : str
    euro_price_with_tax : float
    euro_price_without_tax : float
    availability : str
    review_count : int
    image_url : str
    star_rating : int
    metadata : BookMetadata

    def __str__(self):
        return f"Name : {self.name}\ncategory : {self.category}\nprice : {self.euro_price_without_tax}\nrating : {self.star_rating}\nreviews : {self.review_count}"
    


class MyCrawler():
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        pass


    async def get_soup(self, webpage_link: str, parser: str = 'lxml'):
        response = await self.client.get(webpage_link)
        return BeautifulSoup(response.text, parser), response.status_code, str(response.url)


    async def extract_book_links_from_a_webpage(self, page_link: str):
        page_soup = (await self.get_soup(page_link))[0]
        all_books = page_soup.find('ol', class_='row').find_all('li')
        book_links = []
        
        for book in all_books:
            link = book.find('h3').find('a')['href']
            book_links.append(urljoin(page_link, link))

        return page_soup, book_links


    async def get_book_data_from_book_link(self, book_link: str) -> Book:
        book_soup, status, url = await self.get_soup(book_link)
        other_product_info = guarded(lambda: book_soup.find('table').find_all('tr'))

        book = Book(
            name = guarded(lambda: book_soup.find('div', class_='col-sm-6 product_main').find('h1').text.strip()),
            description = guarded(lambda: book_soup.find('p', class_= None).text.strip()),
            category = guarded(lambda: book_soup.find('ul', class_='breadcrumb').find_all('li')[2].text.strip()),
            euro_price_with_tax = float(guarded(lambda: other_product_info[3].find('td').text[2:])),
            euro_price_without_tax = float(guarded(lambda: other_product_info[2].find('td').text[2:])),
            availability = guarded(lambda: other_product_info[5].find('td').text.strip()),
            review_count = int(guarded(lambda: other_product_info[6].find('td').text.strip())),
            image_url = urljoin(index_url, guarded(lambda: book_soup.find('div', class_='item active').find('img')['src'])),
            star_rating = rate_map[guarded(lambda: book_soup.find('div', class_='col-sm-6 product_main').find_all('p')[2]['class'][1])],

            metadata = BookMetadata(
                timestamp = datetime.datetime.now().__str__(),
                status = status,
                source_url = url
            )
        )

        print(f"{book.name} : Information extraction done.")
        return book



# A function for collecting all the book data
async def collect_all_book_data(crawler: MyCrawler) -> list[Book]:  
    all_book_data = []
    page_link = os.getenv("INITIAL_URL") + "page-1.html"
    start_time = time.time()

    # pages_to_work_with = 3

    while True:
        page_soup, book_links = await crawler.extract_book_links_from_a_webpage(page_link)
        books_per_page = await asyncio.gather(*(crawler.get_book_data_from_book_link(book_link) for book_link in book_links))
        all_book_data.extend(books_per_page)

        next_page_availabe = page_soup.find('li', class_='next')
        if next_page_availabe is None:
            break

        page_link = os.getenv("INITIAL_URL") + next_page_availabe.find('a')['href']
        # print(f"next page to crawl : {page_link}")
        pass

    
    # all_page_links = [(initial_link_for_books + f"page-{page_number + 1}.html") for page_number in range(pages_to_work_with)]
    
    # book_links_per_page = await asyncio.gather(*(crawler.extract_book_links_from_a_webpage(page_link) for page_link in all_page_links))
    # book_links = []
    # for page in book_links_per_page:
    #     for book_link in page:
    #         book_links.append(book_link)


    print("="*60)

    end_time = time.time()

    print(f"\n{'*'*10} Took around {(end_time - start_time):.3f} seconds to crawl. {'*'*10}\n")
    return all_book_data



async def main_func():
    async_client = httpx.AsyncClient()
    crawler = MyCrawler(async_client)

    index_soup_task = asyncio.create_task(crawler.get_soup(index_url))
    book_collecting_task = asyncio.create_task(collect_all_book_data(crawler))

    index_soup = (await index_soup_task)[0]

    all_books_count = int(index_soup.find('form').find_all('strong')[0].text)
    max_books_per_page =  int(index_soup.find('form').find_all('strong')[2].text)
    total_pages = int(index_soup.find('ul', class_='pager').find('li').text.replace("\n", '').strip().split(' ')[-1])
    # print(f"Showing {max_books_per_page} books among {all_books_count} books. There are {total_pages} pages in total.\n")

    all_book_data = await book_collecting_task
    print(len(all_book_data))


if __name__ == "__main__":
    asyncio.run(main_func())
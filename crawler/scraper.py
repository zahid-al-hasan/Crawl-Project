from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests, datetime


def get_soup(webpage_link: str, parser: str = 'lxml'):
    response = requests.get(webpage_link)
    return BeautifulSoup(response.text, parser), response.status_code, response.url


def guarded(fn, default="NULL"):
    try:
        return fn()
    except:
        return default


index_url = "https://books.toscrape.com/"
initial_link_for_books = "https://books.toscrape.com/catalogue/"


index_soup = get_soup(index_url)[0]
all_books_count = int(index_soup.find('form').find_all('strong')[0].text)
max_books_per_page =  int(index_soup.find('form').find_all('strong')[2].text)
total_pages = int(index_soup.find('ul', class_='pager').find('li').text.replace("\n", '').strip().split(' ')[-1])
print(f"Showing {max_books_per_page} books among {all_books_count} books. There are {total_pages} pages in total.\n")



def extract_book_links_from_a_webpage(page_link: str) -> list[str]:
    page_soup = get_soup(page_link)[0]
    all_books = page_soup.find('ol', class_='row').find_all('li')
    book_links = []
    
    for book in all_books:
        href = book.find('h3').find('a')['href']
        book_links.append(urljoin(page_link, href))

    return book_links
    pass



def get_book_data_from_book_link(book_link: str) -> dict:
    book_soup, status, url = get_soup(book_link)
    other_product_info = guarded(lambda: book_soup.find('table').find_all('tr'))

    book_data = {
        "name" : guarded(lambda: book_soup.find('div', class_='col-sm-6 product_main').find('h1').text.strip()),
        "description" : guarded(lambda: book_soup.find('p', class_= None).text.strip()),
        "category" : guarded(lambda: book_soup.find('ul', class_='breadcrumb').find_all('li')[2].text.strip()),
        "euro_price_with_tax" : guarded(lambda: other_product_info[3].find('td').text[2:]),
        "euro_price_without_tax" : guarded(lambda: other_product_info[2].find('td').text[2:]),
        "availability" : guarded(lambda: other_product_info[5].find('td').text.strip()),
        "review_count" : guarded(lambda: other_product_info[6].find('td').text.strip()),
        "image_url" : urljoin(index_url, guarded(lambda: book_soup.find('div', class_='item active').find('img')['src'])),
        "star_rating" : guarded(lambda: book_soup.find('div', class_='col-sm-6 product_main').find_all('p')[2]['class'][1]),

        "metadata" : {
            "timestamp" : datetime.datetime.now().__str__(),
            "status" : status,
            "source_url" : url
        }
    }

    print(f"{book_data["name"]} : Information extraction done.")
    return book_data


def collect_all_book_data() -> list[dict]:  
    all_book_data = []
    pages_to_work_with = 1
    for page_number in range(pages_to_work_with):
        print(f"\nCurrently Working with page {page_number + 1} : \n")
        current_page_link = initial_link_for_books + f"page-{page_number + 1}.html"
        book_links = extract_book_links_from_a_webpage(current_page_link)
        for book_link in book_links:
            book_data = get_book_data_from_book_link(book_link)
            all_book_data.append(book_data)

        print(f"\nExtracted all book data from page {page_number + 1}")
        print("="*60)

    return all_book_data


if __name__ == "__main__":
    all_book_data = collect_all_book_data()
    for book_data in all_book_data:
        print(book_data)
        print()
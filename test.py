import requests
from bs4 import BeautifulSoup
import pandas as pd
headers = {
    'User-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
}

base_url = f"https://books.toscrape.com/"

# Send an HTTP GET request to the URL
response = requests.get(base_url, headers={'User-Agent': 'Mozilla/5.0'})

# Check if the request was successful
if response.status_code == 200:
    # Parse the page content with BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all book containers (each book is represented by a 'article' tag)
    books = soup.find_all('article', class_='product_pod')
    final_books = []
    # Loop through each book and extract the title, rating, and price
    for book in books:
        # Extract book title
        title = book.find('h3').find('a')['title']

        # Extract book rating (ratings are stored as a class name, so we check for a specific class)
        rating_class = book.find('p', class_='star-rating')['class'][1]  # rating is the second class in this list

        # Extract book price
        price = book.find('p', class_='price_color').text

        final_books.append({"Title" : title.text.strip(), "Rating":rating_class.text.strip(), "Price" : price[2:].text.strip()})
        # Print the book title, rating, and price

    for elem in final_books:
        print(elem['Title'])

    df = pd.DataFrame(final_books)

    # Remove duplicates based on 'Title' column
    df.drop_duplicates(subset="Title", inplace=True)
    print(df)
else:
    print("Failed to retrieve the page")


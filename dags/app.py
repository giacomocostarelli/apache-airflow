
#dag - directed acyclic graph

#tasks : 1) fetch amazon data (extract) 2) clean data (transform) 3) create and store data in table on postgres (load)
#operators : Python Operator and PostgresOperator
#hooks - allows connection to postgres
#dependencies

from datetime import datetime, timedelta
from airflow import DAG
import requests
import pandas as pd
from bs4 import BeautifulSoup
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

#1) fetch amazon data (extract) 2) clean data (transform)

headers = {
    "Referer": 'https://www.amazon.com/',
    "Sec-Ch-Ua": "Not_A Brand",
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": "macOS",
    'User-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
}


def get_amazon_data_books(ti):
    # Base URL of the Amazon search results for data science books
    base_url = f"https://books.toscrape.com/"

    # Send an HTTP GET request to the URL
    response = requests.get(base_url, headers={'User-Agent': 'Mozilla/5.0'})
    
    final_books = []

    if response.status_code == 200:
        # Parse the page content with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all book containers (each book is represented by a 'article' tag)
        books = soup.find_all('article', class_='product_pod')

        # Loop through each book and extract the title, rating, and price
        for book in books:
            # Extract book title
            title = book.find('h3').find('a')['title']

            # Extract book rating (ratings are stored as a class name, so we check for a specific class)
            rating_class = book.find('p', class_='star-rating')['class'][1]  # rating is the second class in this list

            # Extract book price
            price = book.find('p', class_='price_color').text

            final_books.append({"Title" : title, "Rating":rating_class, "Price" : price[2:]})
            # Print the book title, rating, and price

    # Convert the list of dictionaries into a DataFrame
    df = pd.DataFrame(final_books)
    
    # Remove duplicates based on 'Title' column
    df.drop_duplicates(subset="Title", inplace=True)
    
    # Push the DataFrame to XCom
    ti.xcom_push(key='book_data', value=df.to_dict('records'))

#3) create and store data in table on postgres (load)
    
def insert_book_data_into_postgres(ti):
    book_data = ti.xcom_pull(key='book_data', task_ids='fetch_book_data')
    print(book_data)
    if not book_data:
        raise ValueError("No book data found")

    postgres_hook = PostgresHook(postgres_conn_id='books_connection')
    insert_query = """
    INSERT INTO books_2 (title, rating, price)
    VALUES (%s, %s, %s)
    """
    for book in book_data:
        postgres_hook.run(insert_query, parameters=(book['Title'], book['Rating'], book['Price']))


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 6, 20),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'fetch_and_store_amazon_books',
    default_args=default_args,
    description='A simple DAG to fetch book data from Amazon and store it in Postgres',
    schedule_interval=timedelta(days=1),
)

#operators : Python Operator and PostgresOperator
#hooks - allows connection to postgres


fetch_book_data_task = PythonOperator(
    task_id='fetch_book_data',
    python_callable=get_amazon_data_books,
    dag=dag,
)

create_table_task = PostgresOperator(
    task_id='create_table',
    postgres_conn_id='books_connection',
    sql="""
    CREATE TABLE IF NOT EXISTS books_2 (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        rating TEXT,
        price TEXT
    );
    """,
    dag=dag,
)

insert_book_data_task = PythonOperator(
    task_id='insert_book_data',
    python_callable=insert_book_data_into_postgres,
    dag=dag,
)

#dependencies

fetch_book_data_task >> create_table_task >> insert_book_data_task
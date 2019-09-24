
'''Import books.csv into books table.'''
import csv
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker

# Set up database connection
engine = create_engine(os.getenv("DATABASE_URL"), echo=True)
db = scoped_session(sessionmaker(bind=engine))


def main():
    with open("books.csv", "r") as books:
        reader = csv.DictReader(books, fieldnames=['isbn', 'title', 'author', 'year'])
        # Skip header
        next(reader)
        # Insert CSV data into table
        statement = text("INSERT INTO books(isbn, title, author, year) VALUES(:isbn, :title, :author, :year)")
        for row in reader:
            row['year'] = int(row['year'])
            db.execute(statement, row)
        db.commit()


if __name__ == "__main__":
    main()
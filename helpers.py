from flask import redirect, render_template, session
from functools import wraps
from sqlalchemy import text


# Create tables if not exists
def create_tables(db):
    exists = text("SELECT EXISTS (SELECT table_name FROM information_schema.tables WHERE table_name = :table_name)")

    # Users table
    if not db.execute(exists, {"table_name": 'users'}).first()["exists"]:
        db.execute("CREATE TABLE users(id SERIAL PRIMARY KEY, " +
                                       "username VARCHAR(255) UNIQUE NOT NULL, " + 
                                       "hash VARCHAR(255) NOT NULL);")
        db.commit()

    # Books table
    if not db.execute(exists, {"table_name": 'books'}).first()["exists"]:
        db.execute("CREATE TABLE books(id SERIAL PRIMARY KEY, " +
                                       "isbn CHAR(10) UNIQUE NOT NULL, " +
                                       "title VARCHAR(255) NOT NULL, " +
                                       "author VARCHAR(255) NOT NULL, " +
                                       "year INTEGER NOT NULL);")
        db.commit()

    # Reviews table
    if not db.execute(exists, {"table_name": 'reviews'}).first()["exists"]:
        db.execute("CREATE TABLE reviews(user_id INTEGER REFERENCES users(id) NOT NULL, " +
                                         "book_id INTEGER REFERENCES books(id) NOT NULL, " +
                                         "rating INTEGER CHECK (rating > 0 AND rating <= 5) NOT NULL, " +
                                         "description VARCHAR(1023), " + 
                                         "PRIMARY KEY (user_id, book_id));")
        db.commit()
    db.commit()

# Error handler
def error(description, code):
    return render_template("error.html", description= description, code=code)

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function
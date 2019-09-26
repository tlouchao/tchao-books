import string
import os
import requests

from flask import Flask, redirect, render_template, request, session, url_for
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import create_tables, error, login_required

app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Check for environment variables
if not os.getenv("API_KEY"):
    raise RuntimeError("API_KEY is not set")
if not os.getenv("SECRET_KEY"):
    raise RuntimeError("SECRET_KEY is not set")
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

# Set up database connection
engine = create_engine(os.getenv("DATABASE_URL"), 
                       connect_args={"application_name": "application.py"}, 
                       echo=True)
db = scoped_session(sessionmaker(bind=engine))

# Create tables if not exists
create_tables(db)

# NOTE: Run import.py to populate books table
# TODO: Add timestamp column to reviews table
# TODO: Optional: Handle search routing with query parameters

# Routing
@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST" and request.form.get("submit") == "search":
        # Build select statement
        search_keys = ["isbn", "title", "author"]
        search_like = []
        search_params = {}
        for k in search_keys:
            if request.form.get(k):
                # Match substrings
                search_like.append("{} ILIKE :{}".format(k, k))
                search_params[k] = "%{}%".format(request.form.get(k))
        # No matches returned if form fields are empty
        if not search_params:
                return render_template("index.html", matches=0,
                                                     items={})
        # Execute select statement
        search_statement = text("SELECT * FROM books WHERE " + " AND ".join(search_like))
        search_result = db.execute(search_statement, search_params).fetchall()
        db.commit()
        matches = len(search_result)
        items = {k: v[1:-1] for k, v in search_params.items()}
        # No matches returned if row count == 0
        if matches == 0:
            return render_template("index.html", matches=matches,
                                                 items=items)
        # Show table if matches returned
        else:
            headers = search_keys[:]
            headers.append("year")
            return render_template("index.html", matches=matches,
                                                 items=items,
                                                 headers=headers,
                                                 result=search_result)
    elif request.method == "POST" and request.form.get("submit") == "review":
        isbn = request.form.get("radio")
        if not isbn:
            return error("Please select a book to review", 403)
        else:
            return redirect('/review/' + isbn)
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("index.html", items={}, alert=request.args.get("alert"))

@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    return redirect(url_for('index'))

@app.route("/review/<string:isbn>", methods=["GET", "POST"])
@login_required
def review(isbn):

    # Select book from database
    book_statement = text("SELECT * FROM books WHERE isbn = :isbn")
    book_statement = book_statement.bindparams(isbn=isbn)

    # Assume that ISBN is unique
    book_result = db.execute(book_statement).first()
    db.commit()
    if not book_result:
        return error("Book with ISBN: {} does not exist".format(isbn), 403)

    # Handle form submission
    if request.method == 'POST':
        if not request.form.get("review"):
            return error('Please submit a review', 400)
        if not request.form.get("rating"):
            return error('Please select a rating', 400)

        # Check if review already exists
        exists_statement = text("SELECT COUNT(*) FROM reviews WHERE user_id = :user_id and book_id = :book_id")
        exists_statement = exists_statement.bindparams(user_id=session["user_id"], book_id=book_result["id"])
        exists_result = db.execute(exists_statement).first()
        db.commit()

        if exists_result["count"] == 1:
            return error('Review already submitted for this book', 403)

        # Submit review if not exists
        review_statement = text("INSERT INTO reviews(user_id, book_id, rating, description) " + 
                                "VALUES(:user_id, :book_id, :rating, :description)")
        review_statement = review_statement.bindparams(user_id=session["user_id"], 
                                                       book_id=book_result["id"],
                                                       rating=request.form.get("rating"),
                                                       description=request.form.get("review"))
        review_result = db.execute(review_statement)
        db.commit()
        return redirect(url_for('index', alert="Success!"))

    # User reached route via GET (as by clicking a link or via redirect)
    else:

        # Select reviews of this book from database
        reviews_statement = text("select username, rating, description FROM users " + 
                                "JOIN (SELECT * FROM books JOIN reviews ON (books.id = reviews.book_id) " +
                                "WHERE books.id = :id) AS books_reviews ON (users.id = books_reviews.user_id)")
        reviews_statement = reviews_statement.bindparams(id=book_result["id"])
        reviews_result = db.execute(reviews_statement).fetchall()
        db.commit()

        if len(reviews_result) == 0:
            reviews_message = "There doesn't seem to be anything here."
        else:
            reviews_message = "See what other readers have to say about {} :)".format(book_result["title"])

        # Send request to Goodreads API
        res = requests.get("https://www.goodreads.com/book/review_counts.json", \
                            params={"key": os.getenv("API_KEY"), "isbns": isbn})
        if res.status_code == 404:
            average_rating, total_ratings = "unavailable", "unavailable"
        else:
            book_json = res.json()["books"][0]
            average_rating, total_ratings = book_json["average_rating"], book_json["ratings_count"]
        
        # Display page
        return render_template("review.html", isbn=isbn, 
                                              title=book_result["title"], 
                                              author=book_result["author"],
                                              year=book_result["year"],
                                              average_rating=average_rating,
                                              total_ratings=total_ratings,
                                              reviews_message=reviews_message,
                                              reviews=reviews_result)

@app.route("/logout", methods=["GET"])
@login_required
def logout():

    # Forget user
    session["user_id"] = None
    session["user_username"] = None

    return redirect(url_for('login'))

@app.route("/login", methods=["GET", "POST"])
def login():

    # Forget user
    session["user_id"] = None
    session["user_username"] = None

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return error("must provide username", 400)

        # Ensure password was submitted
        if not request.form.get("password"):
            return error("must provide password", 400)

        # Query database for user
        # Assume that one entry is returned, since username is unique
        statement = text("SELECT * FROM users WHERE username = :username")
        statement = statement.bindparams(username=request.form.get("username"))
        result = db.execute(statement).first()
        db.commit()

        # Ensure username exists and password is correct
        if not result or not check_password_hash(result["hash"], request.form.get("password")):
            return error("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = result["id"]
        session["user_username"] = result["username"]

        # Redirect user to home page
        return redirect(url_for('index'))

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html", alert=request.args.get("alert"))

@app.route("/register", methods=["GET", "POST"])
def register():
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return error("must provide username", 400)

        # Ensure password and confirmation were submitted
        if not request.form.get("password"):
            return error("must provide password", 400)
        elif not request.form.get("confirmation"):
            return error("must provide confirmation", 400)

        # Ensure password and confirmation match
        if request.form.get("password") != request.form.get("confirmation"):
            return error("password and confirmation do not match", 400)

        # Ensure that username contains alphanumeric characters
        if not request.form.get("username").isalnum():
            return error("username must contain alphanumeric characters", 403)

        # Ensure that password does not contains whitespace
        for p in request.form.get("password"):
            if p in string.whitespace:
                return error("password cannot contain whitespace", 403)

        # Query database for user
        # Assume that one entry is returned, since username is unique
        statement = text("SELECT * FROM users WHERE username = :username")
        statement = statement.bindparams(username=request.form.get("username"))
        result = db.execute(statement).first()
        db.commit()

        # Ensure username is available
        if result:
            return error("username is taken", 403)
        
        # Register user
        statement = text("INSERT INTO users(username, hash) VALUES(:username, :hash)")
        statement = statement.bindparams(username=request.form.get("username"),
                                         hash=generate_password_hash(request.form.get("password")))     
        db.execute(statement)
        db.commit()

        # Redirect user to login page
        return redirect(url_for('login', alert="Success!"))
    else:
        # User reached route via GET (as by clicking a link or via redirect)
        return render_template("register.html")

# Handle errors
def errorhandler(e):
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return error(e.name, e.code)

# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
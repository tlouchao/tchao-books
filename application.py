import os

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
if not os.getenv("SECRET_KEY"):
    raise RuntimeError("SECRET_KEY is not set")
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

# Set up database connection
engine = create_engine(os.getenv("DATABASE_URL"), echo=True)
db = scoped_session(sessionmaker(bind=engine))

# Create tables if not exists
create_tables(db)

# NOTE: Run import.py to populate books table

# Routing
@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    # Query database for user
    # Assume that one entry is returned, since username is unique
    user_statement = text("SELECT * FROM users WHERE id = :id")
    user_statement = user_statement.bindparams(id=session["user_id"])
    user_result = db.execute(user_statement).first()
    if request.method == "POST":
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
                return render_template("index.html", username=user_result["username"], 
                                                     matches=0,
                                                     items={})
        # Execute select statement
        search_statement = text("SELECT * FROM books WHERE " + " AND ".join(search_like))
        search_result = db.execute(search_statement, search_params).fetchall()
        matches = len(search_result)
        items = {k: v[1:-1] for k, v in search_params.items()}
        # No matches returned if row count == 0
        if matches == 0:
            return render_template("index.html", username=user_result["username"],
                                                 matches=matches,
                                                 items=items)
        # Show table if matches returned
        else:
            headers = search_keys[:]
            headers.append("year")
            return render_template("index.html", username=user_result["username"],
                                                 matches=matches,
                                                 items=items,
                                                 headers=headers,
                                                 result=search_result)
    else:
    # User reached route via GET (as by clicking a link or via redirect)
        return render_template("index.html", username=user_result["username"], items={})

@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    return redirect('/')

@app.route("/review", methods=["GET", "POST"])
@login_required
def review():
    return render_template("review.html")

@app.route("/logout", methods=["GET"])
@login_required
def logout():

    # Forget any user_id
    session["user_id"] = None

    return redirect('/login')

@app.route("/login", methods=["GET", "POST"])
def login():

    # Forget any user_id
    session["user_id"] = None

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

        # Ensure username exists and password is correct
        if not result or not check_password_hash(result["hash"], request.form.get("password")):
            return error("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = result["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

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

        # Query database for user
        # Assume that one entry is returned, since username is unique
        statement = text("SELECT * FROM users WHERE username = :username")
        statement = statement.bindparams(username=request.form.get("username"))
        result = db.execute(statement).first()

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
        return redirect("/login")
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
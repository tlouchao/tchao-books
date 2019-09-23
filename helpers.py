from flask import redirect, render_template, session
from functools import wraps



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
# Project 1

Web app that allows users to login with credentials and review books.

## Setup
run `git clone --branch web50/projects/2019/x/1 https://github.com/me50/tlouchao.git`      
run `pip install -r requirements.txt` . 
set environment variable `FLASK_APP` to `application.py`  
set environment variable `SECRET_KEY` to a random string (EX: import os module, then run `os.urandom(12).hex()`)  
set environment variable `DATABASE_URL` to database URI credential provided by Heroku  
set environment variable `API_KEY` to GoodReads API key  
run `flask run` to start the application  
run `python3 import.py` to import book data into database  

## Summary

### Register & Login
Create a username/password pair and login with your credentials. Username should only contain alphanumeric characters.  

NOTE: Do NOT use a real password as this web app does not enforce a minimum character count.  

### Search
Enter an ISBN number, book title, and/or book author. If at least one field is provided a list of books will be returned   which match the criteria. Matching is case-insensitive and a partial ISBN, title, and/or author is acceptable.      

Select a book and press the "Review" button to navigate to that book's webpage.  

### Review
Submit a review of this book and give this book a rating from 1-5. View reviews and ratings from other users.  

### API Access
Send a GET request to the web app's `/api/<isbn>` route, where `<isbn>` is an ISBN number, in order to retrieve a JSON response:  

```
{
  "isbn": "0340839937", 
  "title": "Dune", 
  "author": "Frank Herbert", 
  "year": 1965, 
  "review_count": 3, 
  "average_score": "4.33"
}
```




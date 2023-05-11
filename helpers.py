# helping functions for the final CS50 project

import locale
import datetime
import calendar
import random
import string
from cs50 import SQL
from datetime import datetime, timedelta
from flask import render_template, session, redirect
from functools import wraps

# connect to budio6.db
db = SQL("sqlite:///budio6.db")

def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def apology(message, code=400):
    return render_template("apology.html", top='Da ist was schiefgelaufen :(', bottom=message)

# Return Austrian month name as str
def currentmonth():
    locale.setlocale(locale.LC_TIME, "de_AT.UTF-8")
    current_month = datetime.now()
    current_month = current_month.strftime('%B')
    return current_month

# Return Austrian month name as str
def nextmonth():
    locale.setlocale(locale.LC_TIME, "de_AT.UTF-8")
    next_month = datetime.now() + timedelta(days=32)
    next_month = next_month.strftime('%B')
    return next_month

# return current year as string
def currentyear():
    locale.setlocale(locale.LC_TIME, "de_AT.UTF-8")
    current_time = datetime.now()
    current_year = current_time.strftime('%Y')
    return current_year

# Return number of days of current month
#def monthdays():
#    daynum = calendar.monthrange(datetime.now().year, datetime.now().month)
#    return daynum[1]

def monthdays(month):
    daynum = calendar.monthrange(datetime.now().year, month)
    return daynum[1]

# Create a hash symbol
def hashit():
    letters = string.ascii_lowercase
    LETTERS = string.ascii_uppercase
    numbs = string.digits
    chars = [letters, LETTERS, numbs]
    hash = []
    for i in range(0,8):
        x = random.choice(chars)
        hash.append(random.choice(x))
    return ''.join(hash)

# Check weekday for date --> 0 = Monday
def wochentag(Datum):
    date_object = datetime.strptime(Datum, '%d.%m.%Y').date()
    return date_object.weekday()

# Choose random person of those available on the day and not already working
"""def rand(day):
    current_month = currentmonth()
    current_abw = f"abw_{datetime.now().year}_{datetime.now().month:02d}"
    available_persons = db.execute(f'SELECT handle FROM ? WHERE ("day {day}" NOT LIKE "x" AND handle NOT IN (SELECT Besetzung FROM ? WHERE Datum LIKE ? AND Besetzung IS NOT null GROUP BY Besetzung));', current_abw, f"sendungen_{current_month}", f"{day+1:02d}.{datetime.now().month:02d}.{datetime.now().year}")
    prob = []

    for person in available_persons:
        prob.append((db.execute("SELECT workload FROM users WHERE handle LIKE ?;", person['handle']))[0]['workload'] / db.execute("SELECT SUM(workload) FROM users;")[0]['SUM(workload)'])

    return (random.choices(available_persons, weights=prob))[0]"""

def rand(available_persons):
    # set probability according to workload
    prob = []
    for person in available_persons:
        prob.append((db.execute("SELECT workload FROM users WHERE handle LIKE ?;", person['handle']))[0]['workload'] / db.execute("SELECT SUM(workload) FROM users;")[0]['SUM(workload)']) 
    person = random.choices(available_persons, weights=prob)[0]
    available_persons.remove(person)
    return person['handle']

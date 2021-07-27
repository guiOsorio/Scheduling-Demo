import os
import sqlite3

from flask import Flask, flash, redirect, render_template, session, request
from flask_session import Session
from flask_wtf import FlaskForm
from wtforms.fields.html5 import DateField
from wtforms import StringField, SelectField
from datetime import datetime
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required, validateReservation

# Initialize app
app = Flask(__name__)

# Configure for flask_wtf
app.config["SECRET_KEY"] = "secret"

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Arrays for SelectField choices
numofpeople = ["2", "3", "4"]
courts = ["1", "2", "3"]
possibletimes = ["Choose a time",
    "09:00", "09:30",
    "10:00", "10:30",
    "11:00", "11:30",
    "12:00", "12:30",
    "13:00", "13:30",
    "14:00", "14:30",
    "15:00", "15:30",
    "16:00", "16:30",
    "17:00", "17:30",
    "18:00", "18:30",
    "19:00", "19:30",
    "20:00", "20:30",
    "21:00"
]
possibletimesweekend = ["Choose a time",
    "09:00", "09:30",
    "10:00", "10:30",
    "11:00", "11:30",
    "12:00", "12:30",
    "13:00", "13:30",
    "14:00", "14:30",
    "15:00", "15:30",
    "16:00", "16:30",
    "17:00", "17:30",
    "18:00", "18:30",
    "19:00"
]

# Reservation Form
class ReservationForm(FlaskForm):
    people = SelectField('Number of people', choices=numofpeople)
    court = SelectField('Court', choices=courts)
    date = DateField('Date', format='%Y-%m-%d', default=datetime.now())
    time = SelectField('Time (open from 09:00 to 22:00)', choices=possibletimes, default="Choose a time")



@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    return render_template("index.html")


@app.route("/reservation", methods=["GET", "POST"])
@login_required
def reservation():
    # Initialize form
    form = ReservationForm()

    # if request is POST and form fields are validated
    if form.validate_on_submit():
        people = form.people.data # string
        court = form.court.data # string
        date = form.date.data # datetime.date
        time = form.time.data # string

        if validateReservation(people, court, date, time, numofpeople, courts, possibletimesweekend, possibletimes):
            user_id = session["user_id"]
            return render_template("data.html", people=people, court=court, date=date, time=time, user_id=user_id)


    return render_template("reservation.html", form=form)



@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        # Ensure username was submitted
        if not username:
            flash("Must have a username")
            return render_template("login.html")

        # Ensure password was submitted
        elif not password:
            flash("Must have a password")
            return render_template("login.html")

        # Connect to database
        con = sqlite3.connect("scheduling.db")
        cur = con.cursor()

        cur.execute("SELECT * FROM users WHERE username = :username", {"username": username})
        user = cur.fetchone()

        if not user:
            flash("Username doesn't exist")
            return render_template("login.html")

        # Ensure username exists and password is correct
        table_hash = user[2]
        if not check_password_hash(table_hash, password):
            flash("Invalid password")
            return render_template("login.html")

        # Get id of user who logged in to store in the session
        cur.execute("SELECT * FROM users WHERE username = :username", {"username": username})
        id = cur.fetchone()[0]

        # Greet user
        flash(f"Welcome, {username} !!")

        # Remember which user has logged in
        session["user_id"] = id

        return redirect("/")

    return render_template("login.html")



@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("pswdconf")

        # Connect to database
        con = sqlite3.connect("scheduling.db")
        cur = con.cursor()

        cur.execute("SELECT username FROM users")
        usernames = cur.fetchall()

        # VALIDATION

        # Handles username already existing
        for user in usernames:
            if username in user:
                flash("This username is already taken")
                return render_template("register.html")

        # Handles username or password fields being blank
        if username.strip() == "" or password.strip() == "" or confirmation.strip() == "":
            flash("All items need a value")
            return render_template("register.html")
        
        # Handles password and password confirmation not matching
        elif password != confirmation:
            flash("Password and confirmation fields need to match")
            return render_template("register.html")

        # Successful registering
        else:
            hashed_password = generate_password_hash(password) # hash password
            cur.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", {"username": username, "hash": hashed_password})
            con.commit()
            flash("Account successfully created!")

            # Get id of user who logged in to store in the session
            cur.execute("SELECT * FROM users WHERE username = :username", {"username": username})
            id = cur.fetchone()[0]

            # Remember which user has logged in
            session["user_id"] = id

            return redirect("/")

    return render_template("register.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/login")


# REQUIREMENTS
    # simplify app.py
    # form 
        # displays a calendar daypicker but with invalid dates disabled (already past dates, days where club is closed, days more than a month from today)
        # displays only options of valid times (from 09:00 to 22:00, with a step of 30 minutes) (only enable to pick available times for the specific court)
        # if reservation is for Saturday or Sunday, possibletimes are until 20:00 only (use possibletimesweekend array for choices)
        # validation with date and time restrictions included (reservations need to be made a minimum of 30 minutes before playing time)
        # reservations can only be made for the current and the next month
    # database
        # define schema (consider admin type)
        # create tables
        # insert SQL statements in app.py, where needed
        # a booking is for 1 hour (after booking is done, make the time for that specific day and court unavailable)
        # have action for user to cancel booking, which makes the times of it available again
        # maximum of 2 reservations per day per person (2 hours) (except for admin)
        # create indexes where useful
    # admin page
        # admin needs to login in order to access this page
        # show all reservations for each court for the selected day (default for today)
        # admin has the ability to delete any reservation for any day and to book a court for an extended period of time (more than 1 hour)
        # admin has the ability to close club for a certain period of time desired
    # more
        # send me an email when an appointment or cancellation is made, with the action's info
        # if there are appointments in the next hour, send me an email with all the appointments
        # schedule Python code to run every 6 months to remove bookings from database and other features if needed
        # page which shows all current reservations for the logged in account


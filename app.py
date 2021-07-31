import os
import sqlite3

from flask import Flask, flash, redirect, render_template, session, request
from flask_session import Session
from flask_wtf import FlaskForm
from wtforms.fields.html5 import DateField
from wtforms import SelectField
from datetime import datetime
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
# Own helper funcs
from helpers.funcs.actions.creates import createIndex, createBooking, createUser, createAccount, bookAllDay
from helpers.funcs.actions.deletes import deleteBookings
from helpers.funcs.actions.gets import getDayBookingsCount, getUserType, getAllUsernames, getCurrDate, getCurrTime, getUpcomingUserBookings, getUserBookingsData, \
    getBookingsData, getDayBookingsCount, getAllBookingsCount
from helpers.funcs.others import isDatePast
from helpers.funcs.validations import validateBooking, validateLogin, validateEmail, validateRegistration, validateIndex, validateDate
from helpers.funcs.requireds import login_required, admin_required
# Own helper lists
from helpers.variables.lists import numofpeople, courts, courts_all, possibletimes, possibletimesweekend

# Initialize app
app = Flask(__name__)

# Configure for flask_wtf
app.config["SECRET_KEY"] = "secret"

# Get environment variables
ADMIN_SECRET_PASSWORD = os.environ.get('ADMIN_SECRET_PASSWORD')

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# FLASK-WTF FORMS
# Booking form
class BookingForm(FlaskForm):
    people = SelectField('Number of people', choices=numofpeople)
    court = SelectField('Court', choices=courts)
    date = DateField('Date', format='%Y-%m-%d', default=datetime.now())
    time = SelectField('Time (open from 09:00 to 22:00)', choices=possibletimes, default="Choose a time")

# Check bookings form
class CheckBookingsForm(FlaskForm):
    date = DateField('Date', format='%Y-%m-%d', default=datetime.now())

# Admin book a court for a day form
class CourtDateForm(FlaskForm):
    court = SelectField('Court', choices=courts_all)
    date = DateField('Date', format='%Y-%m-%d', default=datetime.now())



@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    return render_template("index.html")


@app.route("/booking", methods=["GET", "POST"])
@login_required
def booking():

    # Initialize form
    form = BookingForm()

    # if request is POST and form fields are validated
    if form.validate_on_submit():
        user_id = session["user_id"] # store current user's id
        people = form.people.data # string
        court = form.court.data # string
        date = form.date.data # datetime.date
        selected_date = date.strftime("%Y-%m-%d") # string
        time = form.time.data # string

        if validateBooking(people, court, date, time, numofpeople, courts, possibletimesweekend, possibletimes, user_id):

            createBooking(date, user_id, selected_date, time, court, people)
        
            return redirect("/booking")


    return render_template("booking.html", form=form)



@app.route("/login", methods=["GET", "POST"])
def login():

    # Forget any user_id
    session.clear()

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if not validateLogin(username, password):
            return render_template("login.html")
        
        id = createUser(username)

        # Remember which user has logged in
        session["user_id"] = id

        type = getUserType(id)

        # if user is of admin type, set isAdmin to true, else set it to false
        if type == "admin":
            session["isAdmin"] = True
        else:
            session["isAdmin"] = False

        return redirect("/")

    return render_template("login.html")



@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("pswdconf")
        email = request.form.get("email")

        usernames = getAllUsernames()

        if not validateRegistration(usernames, username, password, confirmation, email):
            return render_template("register.html")

        # Successful registering
        else:
            id = createAccount(password, username, email)

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


@app.route("/mybookings", methods=["GET", "POST"])
@login_required
def mybookings():

    # Initialize form
    form = CheckBookingsForm()

    user_id = session["user_id"] # store current user's id

    current_date_str = getCurrDate()

    upcoming_user_bookings = getUpcomingUserBookings(user_id, current_date_str)

    # check if there are any upcoming bookings, if not, return no upcoming bookings for {user}
    if upcoming_user_bookings == 0:
        msg = "You have no upcoming bookings"
        return render_template("mybookings.html", form=form, msg=msg)

    if "show_day" in request.form and form.validate_on_submit():
        date = form.date.data # datetime.date
        selected_date = date.strftime("%Y-%m-%d") # string

        # Get data for all of the user's bookings in the selected day 
        bookings_data = getUserBookingsData(user_id, selected_date)

        if not bookings_data:
            msg = f"You have no bookings for {date}"
            return render_template("mybookings.html", form=form, msg=msg)
        else:
            return render_template("mybookings.html", form=form, bd=bookings_data)

    if "show_upcoming" in request.form:
        # Get user data for all of the user's upcoming bookings
        showAll = True
        selected_date = None
        bookings_data = getUserBookingsData(user_id, selected_date, showAll)

        if not bookings_data:
            msg = "You have no upcoming bookings"
            return render_template("mybookings.html", form=form, msg=msg)
        else:
            return render_template("mybookings.html", form=form, bd=bookings_data)
    
    if "delete_booking" in request.form and request.method == "POST":
        booking_id = request.form.get("id")
        deleteBookings(booking_id)

        type = getUserType(user_id)

        if type == "admin":
            return redirect("/admin")
        else:
            return redirect("/mybookings")
    
    if "delete_day" in request.form and form.validate_on_submit:
        date = form.date.data # datetime.date
        selected_date = date.strftime("%Y-%m-%d") # string

        deleteBookings(None, user_id, selected_date)

        return render_template("mybookings.html", form=form)
    
    if "delete_all" in request.form:
        deleteBookings(None, user_id)

        return render_template("mybookings.html", form=form)
    
    return render_template("mybookings.html", form=form)


@app.route("/admin", methods=["GET", "POST"])
@login_required
@admin_required
def admin():

    # Initialize forms
    form_court_date = CourtDateForm()

    user_id = session["user_id"] # store current user's id

    # Connect to database
    con = sqlite3.connect("scheduling.db")
    cur = con.cursor()
    
    # POST request for searching bookings for a certain day (default for today)
    if "show_day" in request.form and form_court_date.validate_on_submit():
        court = form_court_date.court.data
        date = form_court_date.date.data # datetime.date
        selected_date = date.strftime("%Y-%m-%d") # string

        bookings_data = getBookingsData(court, selected_date)

        if not bookings_data:
            if court == "All courts":
                msg = "No bookings for the selected day"
                return render_template("admin.html", form_court_date=form_court_date, courts_all=courts_all, msg=msg)
            else:
                msg = "No bookings for this court on the selected day"
                return render_template("admin.html", form_court_date=form_court_date, courts_all=courts_all, msg=msg)
        else:
            return render_template("admin.html", form_court_date=form_court_date, courts_all=courts_all, bd=bookings_data)

    if "delete_booking" in request.form and request.method == "POST":
        booking_id = request.form.get("id")
        deleteBookings(booking_id)

        # get type - if type is admin, redirect to admin, if not, redirect to homepage
        type = getUserType(user_id)
        if type == "admin":
            return redirect("/admin")
        else:
            return redirect("/mybookings")

    if "create_index" in request.form and request.method == "POST":
        name = request.form.get("name")
        table = request.form.get("table")
        columns_input = request.form.get("columns")

        # transform columns into a list
        columns = columns_input.split(",")
        # remove whitespaces from each element of the list
        i = 0
        for column in columns:
            columns[i] = column.strip()
            i += 1

        # turn invalid SQL character into _
        k = 0
        for n in name:
            if n == " " or n == ";" or n == ">" or n == "<" or n == ">":
                name[k] = "_"
            k += 1

        if not validateIndex(name, table, columns_input, columns):
            return redirect("/admin")
        
        createIndex(columns, name, table)

        return redirect("/admin")
    
    # admin has the ability to delete bookings for the selected day (if any exists) and disable bookings for that day
    if "book_day" in request.form and form_court_date.validate_on_submit() and validateDate(form_court_date.date): 
        court = form_court_date.court.data # pass this into query
        selected_date = form_court_date.date.data
        selected_date_str = selected_date.strftime("%Y-%m-%d") # pass this into query
        selected_weekday = selected_date.strftime("%a") # pass this into query
        people = 4 # default when admin makes a booking

        if isDatePast(selected_date_str):
            return redirect("/admin")

        # Delete existing bookings and book for all possible day times
        deleteBookings(None, None, selected_date_str, court)
        bookAllDay(selected_weekday, possibletimesweekend, user_id, selected_date_str, court, people, possibletimes)

        return redirect("/admin")

    # count the number of bookings in a selected day
    if "count_day_bookings" in request.form and form_court_date.validate_on_submit():
        court = form_court_date.court.data # pass this into query
        selected_date = form_court_date.date.data
        selected_date_str = selected_date.strftime("%Y-%m-%d") # pass this into query

        day_count = getDayBookingsCount(court, selected_date_str)

        if court == "All courts":
            return render_template("admin.html", form_court_date=form_court_date, courts_all=courts_all, day_count=day_count, selected_date_str=selected_date_str)
        else:
            return render_template("admin.html", form_court_date=form_court_date, courts_all=courts_all, day_count=day_count, selected_date_str=selected_date_str, court=court)


    if "count_all_bookings" and request.method == "POST":
        
        input_range = request.form.get("range")
        court = request.form.get("court")
        current_time_str = getCurrTime()

        return_data = getAllBookingsCount(input_range, court, current_time_str)
        isRangeValid = return_data[0]
        total_count = return_data[1]

        if not isRangeValid:
            flash("Invalid range input")
            return redirect("/admin")
        
        return render_template("admin.html", form_court_date=form_court_date, courts_all=courts_all, court=court, total_count=total_count, input_range=input_range)

    # page load with GET
    return render_template("admin.html", form_court_date=form_court_date, courts_all=courts_all)


@app.route("/makeadmin", methods=["GET", "POST"])
@login_required
def makeadmin():

    if "make_admin" in request.form and request.method == "POST":
        secret_password = request.form.get("secretpassword")
        # if the secret password is correct, proceed to create new admin account
        if secret_password == ADMIN_SECRET_PASSWORD:
            admin_username = request.form.get("username")
            admin_password = request.form.get("password")
            confirmation = request.form.get("confirmation")
            email = request.form.get("email")

            usernames = getAllUsernames()

            if not validateEmail(email) or not validateRegistration(usernames, admin_username, admin_password, confirmation, email):
                return redirect("/makeadmin")
            else:
                isAdmin = True
                createAccount(admin_password, admin_username, email, isAdmin)
        else:
            flash("Invalid secret password", "danger")
            return redirect("/")

    return render_template("makeadmin.html")


# NEXT TODOS
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# show username of person who booked court on admin's bookings search
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
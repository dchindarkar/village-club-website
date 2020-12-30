from datetime import datetime

from tempfile import mkdtemp

from cs50 import SQL

from flask_session import Session

from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   session)

from werkzeug.exceptions import (HTTPException, InternalServerError,
                                 default_exceptions)
from werkzeug.security import check_password_hash, generate_password_hash

from . import app

from helpers import (apology, fdate, login_required, send_notification,
                     status_msg, usd)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///villageclub.db")

@app.route("/")
def index():
    """Show Welcome pageALL events and allow players to register for an event"""
    return render_template("welcome.html")

@app.route("/contact", methods=["GET","POST"])
def contact():
    #"""Show ALL events """
    if request.method == "GET":
        return render_template("contact.html")
    else:
        if not request.form.get("name"):
            return apology("please enter name", 403)

        elif not request.form.get("email"):
                return apology("please enter email", 403)

        elif not request.form.get("comments"):
            return apology("please enter email", 403)

        name = request.form.get("name")
        email = request.form.get("email")
        comments = request.form.get("comments")

        rtn_id = db.execute("INSERT INTO logbook (name, email, comments) VALUES(:name, :email, :comments)",
                    name=name, email=email, comments=comments)

        if rtn_id == 0:
            return status_msg("Sorry, Contact support - code 503","Contact us", 101)
        else:
            return status_msg("Thanks for visiting, Village CLUB","Contact us", 100)

@app.route("/activity")
def activity():
    """Show contact page"""
    return render_template("activity.html")

@app.route("/eventview", methods=["GET","POST"])
@login_required
def event_view():
    #"""Show ALL events """
    # show future events from current time
    if request.method == "GET":
        return render_template("view.html")
    else:
        if not request.form.get("type"):
            return apology("Select type of event", 403)

        type = request.form.get("type")
        current_time = datetime.now()

        if type == "All":
            future_events = db.execute("SELECT * FROM schedule WHERE start_time >= :current_time",
                    current_time=current_time)
        else:
            future_events = db.execute("SELECT * FROM schedule WHERE type=:type and start_time >= :current_time",
                type=type, current_time=current_time)

        if len(future_events) < 1:
            return apology("No events to show", 403)

        # convert system date to DD-MONTH-YY format
        for event in future_events:
            # Date conversion routine from YYYY-MM-DD to Day Month Day Year

            event.update({"date":fdate(event["start_time"]) })

        return render_template("viewresult.html", events=future_events)

@app.route("/details", methods=["GET","POST"])
@login_required
def event_detail():
    if request.method == "POST":
        event_id = request.form.get("event")

        if not request.form.get("event"):
            return apology("select event", 403)
        # slow event information
        # Query events database for all players registered for events.
        persons = db.execute("SELECT * FROM players JOIN events ON players.id=events.player_id JOIN schedule ON events.event_id=schedule.id WHERE event_id=:event_id ORDER BY first"
            ,event_id=event_id)

        if len(persons) == 0:
            # no player info, so event details withougt player info
            persons = db.execute("SELECT * FROM schedule WHERE id=:event_id"
                ,event_id=event_id)

        if len(persons) == 0:
            return apology("No event Info", 403)
        else:
        # convert system date to DD-MONTH-YY format
            for person in persons:
                # Date conversion routine from YYYY-MM-DD to Day Month Day Year
                person.update({"date":fdate(person["start_time"]) })

                return render_template("details.html", persons=persons)

@app.route("/eventmanage", methods=["GET","POST"])
@login_required
def event_manage():
    if request.method == "GET":
        return render_template("view.html", value="manage")
    else:
        #"""Show ALL events and allow players to register / cancel registration of an event"""
        # show future events from current time
        if not request.form.get("type"):
            return apology("Select type of event", 403)

        type = request.form.get("type")
        current_time = datetime.now()

        if type == "All":
            future_events = db.execute("SELECT * FROM schedule WHERE start_time >= :current_time",
                    current_time=current_time)
        else:
            future_events = db.execute("SELECT * FROM schedule WHERE type=:type and start_time >= :current_time",
                type=type, current_time=current_time)

        if len(future_events) < 1:
            return apology("No events to show", 403)

        # convert system date to DD-MONTH-YY format
        for event in future_events:
            # Date conversion routine from YYYY-MM-DD to Day Month Day Year

            event.update({"date":fdate(event["start_time"]) })

            # Find if user has already checked in / registered for event.
            rows = db.execute("SELECT rowid FROM events WHERE event_id=:event_id and player_id=:player_id",
                event_id=event["id"], player_id=session["user_id"])

            if len(rows) != 0:
                event.update({"status": "confirmed"})
            else:
                event.update({"status": "unconfirmed"})

        return render_template("emanage.html", events=future_events)

@app.route("/event_registration", methods=["GET","POST"])
@login_required
def event_registration():
    event_id = request.form.get("event")
    if not request.form.get("event"):
        return apology("select event", 403)

    player_id = userid=session["user_id"]
    # Check players table if user information present
    player = db.execute("SELECT * FROM players WHERE id=:player_id",
        player_id=player_id)

    # Ask user to update personal info before registering for an event.
    if len(player) == 0:
        return apology("Update your profile to register for an event", 403)

    # Query events database if player has already registered for this event.
    rows = db.execute("SELECT * FROM events WHERE player_id=:player_id and event_id=:event_id",
        player_id=player_id, event_id=event_id)
    if len(rows) == 0:
        # if not already register add the entry to events table
        rtn_id = db.execute("INSERT INTO events (event_id, player_id) VALUES(:event_id, :player_id)",
            player_id=player_id, event_id=event_id)

        if rtn_id != 0:
        # Query events database for all players registered for events.
            persons = db.execute("SELECT * FROM players JOIN events ON players.id=events.player_id JOIN schedule ON events.event_id=schedule.id WHERE event_id=:event_id ORDER BY first"
                ,event_id=event_id)
            if len(persons) == 0:
                return apology("No event Info", 403)
            else:
                # convert system date to DD-MONTH-YY format
                for person in persons:
                    # Date conversion routine from YYYY-MM-DD to Day Month Day Year
                    person.update({"date":fdate(person["start_time"]) })
                return render_template("details.html", persons=persons)
    else:
        success = True
        return status_msg("User already registered for Event","Event registration", 102)

@app.route("/canregi", methods=["GET","POST"])
@login_required
def cancel_registration():
    if request.method == "POST":
        event_id = request.form.get("event")
        if not request.form.get("event"):
            return apology("select event", 403)

        player_id = userid=session["user_id"]

        # Query events database to find item in the table events
        rows = db.execute("SELECT rowid FROM events WHERE event_id=:event_id and player_id=:player_id",
            event_id=event_id, player_id=player_id)
        # If item found Deletew the item

        if len(rows) !=0:
            db.execute("DELETE FROM events WHERE rowid=:rowid",
                rowid=rows[0]["rowid"])

            return status_msg("Cancelled registration for event","Cancel registration", 100)
        else:
            return status_msg("User already cancelled registration","Cancel registration", 102)

    else:
        # Redirect user to home page
        return redirect("/")

@app.route("/create", methods=["GET", "POST"])
@login_required
def event_create():
    # Allow user to create an event
    if request.method == "POST":
        if not request.form.get("type"):
            return apology("Select type of event", 403)

        elif not request.form.get("event-time"):
            return apology("Enter date and time", 403)

        elif not request.form.get("venue"):
            return apology("Enter place/venue", 403)

        type = request.form.get("type")

        st_time = request.form.get("event-time")
        # For safari and IE date-time attribute is not supoorted hence validate "event-time"

        try:
            x = datetime.strptime(st_time, '%Y-%m-%dT%H:%M')
        except ValueError as ve:
            return apology("Invalid format for date and time", 403)

        current_time = datetime.now()

        if x < current_time:
            return status_msg("Please select date and time in future","Create event", 101)

        # Query database schedule for user information
        rows = db.execute("SELECT * FROM schedule WHERE start_time = :st_time",
            st_time=st_time)

        if len(rows) == 0:                  # Free to schedule does not exist
            # Update new schedule entry into table
            type = request.form.get("type")
            venue  = request.form.get("venue")

            rtn_id = db.execute("INSERT INTO schedule (type, venue, start_time) VALUES(:type, :venue, :st_time)",
                            type=type, venue=venue, st_time=st_time)

            if rtn_id != 0:
                # Query database for username and send email notification
                players = db.execute("SELECT username FROM users")

                if len(players) == 0:
                    return status_msg("Sorry, Event email notification failed - code 501","Event Create", 101)
                else:
                    print(players)
                    send_notification(players, type)

                return status_msg("Please register for event using event/manage","Event Create", 100)
            else:
                return status_msg("Sorry Event creation unsuccessful - code 502","Event Create", 101)
    else:
        return render_template("create.html")

@app.route("/history", methods=["GET", "POST"])
@login_required
def history():
    if request.method == "GET":
        return render_template("view.html", value='history')
    else:
        if not request.form.get("type"):
            return apology("Select type of event", 403)

        type = request.form.get("type")
        current_time = datetime.now()

        if type == "All":
            future_events = db.execute("SELECT * FROM schedule")
        else:
            future_events = db.execute("SELECT * FROM schedule WHERE type=:type",
                type=type)

        if len(future_events) < 1:
            return apology("No events to show", 403)

        # convert system date to DD-MONTH-YY format
        for event in future_events:
            # Date conversion routine from YYYY-MM-DD to Day Month Day Year

            event.update({"date":fdate(event["start_time"]) })

        return render_template("viewresult.html", events=future_events)

@app.route("/visitor", methods=["GET", "POST"])
@login_required
def visitor():

    visitors = db.execute("SELECT * FROM logbook")

    if len(visitors) < 1:
        return apology("No visitor yet", 403)

    number = db.execute("SELECT count(id) AS count FROM logbook")

    print(visitors)

    return render_template("viewvisit.html", visitors=visitors, number=number)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/profileview")
@login_required
def profileview():
    """ view user profile """
    name = db.execute("SELECT username, cash FROM users WHERE users.id = :userid",
      userid=session["user_id"])

    if len(name) == 0:
        return apology("invalid user account", 403)
    else:

        cash = usd(float(name[0]["cash"]))

        player_info = db.execute("SELECT * FROM players WHERE id = :userid",
            userid=session["user_id"])
        print(player_info)
        if len(player_info) == 0:
                #email = name[0]["username"]
                return status_msg("Missing account information, Please update your account information","My profile", 102)
                #return apology("No account info", 403)
        else:
            # Update exisitng profile
            email = name[0]["username"]
            player_info[0].update({"username": email})
            player_info[0].update({"cash": cash })

            return render_template("viewprofile.html", player_info=player_info)

@app.route("/myprofile", methods=["GET", "POST"])
@login_required
def myprofile():
    """Get stock quote."""
    if request.method == "GET":
        name = db.execute("SELECT username, cash FROM users WHERE users.id = :userid",
          userid=session["user_id"])
        if len(name) == 0:
            return apology("invalid user account", 403)
        else:
            cash = float(name[0]["cash"])
            # Query database players for user information
            player_info = db.execute("SELECT * FROM players WHERE id = :userid",
                userid=session["user_id"])

            # Create new profile
            if len(player_info) == 0:
                email = name[0]["username"]
                return render_template("update.html", email=email)
            else:
                # Update exisitng profile
                email = name[0]["username"]
                player_info[0].update({"username": email})
                player_info[0].update({"cash": cash })
                return render_template("userinfo.html", player_info=player_info)
    else:
        if not request.form.get("title"):
            return apology("provide title", 403)
        elif not request.form.get("first"):
            return apology("provide first name", 403)
        elif not request.form.get("last"):
            return apology("provide last name", 403)
        elif not request.form.get("phone"):
            return apology("provide phone", 403)
        elif not request.form.get("city"):
            return apology("provide city", 403)
        elif not request.form.get("age") or int(request.form.get("age")) < 5:
            return apology("provide age, must be 5 years and older", 403)

        # Query database players for user information
        rows = db.execute("SELECT * FROM players WHERE id = :userid",
            userid=session["user_id"])
        if len(rows) == 0:                  # User info does not exist
            # Update new user info in players table
            user_id  = session["user_id"]
            title = request.form.get("title")
            first = request.form.get("first")
            last = request.form.get("last")
            phone = request.form.get("phone")
            city = request.form.get("city")
            age = request.form.get("age")

            # Validate phone as 123-456-7890.

            y = phone.split("-")
            if len(y) == 1:
                y = phone[:3] + '-' + phone[3:6] + '-'  + phone[6:]
                phone = y

            rtn_id = db.execute("INSERT INTO players (id, title, first, last, phone, city, age) VALUES(:user_id, :title, :first, :last, :phone, :city, :age)",
                              user_id=user_id, title=title, first=first, last=last, phone=phone, city=city, age=age)

            if rtn_id != 0:
                return status_msg("New account created","My profile", 100)
            else:
                return status_msg("Account creation failed, error-503","My profile", 101)

        else:
            title = request.form.get("title")
            first = request.form.get("first")
            last = request.form.get("last")
            phone = request.form.get("phone")
            uid = session["user_id"]
            city = request.form.get("city")
            age = request.form.get("age")
            ucash = request.form.get("cash")

            rtn_id = db.execute("UPDATE players SET title=:title, first=:first, last=:last, phone=:phone, city=:city, age=:age WHERE id=:id",
                              title=title, first=first, last=last, phone=phone, id=uid, city=city, age=age)

            if rtn_id != 0:
                # Update membership fees for user
                # Query database for membership fee on the account
                rows = db.execute("SELECT id, cash FROM users WHERE id = :userid",
                                userid=session["user_id"])

                # Ensure username exists and password is correct
                if len(rows) != 1:
                    return apology("User not found", 403)

                cash = rows[0]["cash"]

                cash = cash + float(ucash)

                db.execute("UPDATE users SET cash=:cash WHERE id = :userid", cash=cash, userid=session["user_id"])


                # Redirect user to home page
                return status_msg("User account updated","My profile", 100)
            else:
                return status_msg("Account update failed, error-504","My profile", 101)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was entered and submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure password was re-entered and submitted
        elif not request.form.get("confirmation"):
            return apology("must provide password", 403)

        # Ensure password and re-entered password are same.
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("must provide same password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username does not exists
        if len(rows) != 1:

            # Insert new user to users table
            name = request.form.get("username")

            newpswd = request.form.get("password")

            if newpswd.isprintable() and newpswd.isalnum():
                return apology("Password alpha-numeric + special char", 403)

            if len(newpswd) < 6:
                return apology("Password length must be minimum 6 char", 403)

            pwhash = generate_password_hash(request.form.get("password"))

            db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash) ",
                              username=name, hash=pwhash)
            # Redirect user to home page
            return status_msg("Congratulations, Welcome new member please update your Account information","Registration", 100)
            #return redirect("/")
        else:
            return apology("User Name already exist", 403)

    else:
        # User reached route via GET (as by clicking a link or via redirect)
        return render_template("register.html")

@app.route("/chgpwd", methods=["GET", "POST"])
def changepwd():
    """Change password for user"""
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was entered and submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure newpassword was entered and submitted
        elif not request.form.get("newpassword"):
            return apology("must provide new password", 403)

        # Ensure password was re-entered and submitted
        elif not request.form.get("confirmation"):
            return apology("must provide password", 403)

        # Ensure password and re-entered password are same.
        if request.form.get("newpassword") != request.form.get("confirmation"):
            return apology("must provide same password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)


        name = request.form.get("username")

        newpswd = request.form.get("newpassword")

        if newpswd.isprintable() and newpswd.isalnum():
            return apology("Password alpha-numeric + special char", 403)

        if len(newpswd) < 6:
            return apology("Password length must be minimum 6 char", 403)

        pwhash = generate_password_hash(request.form.get("newpassword"))

        db.execute("UPDATE users SET hash=:hash WHERE username = :username", hash=pwhash, username=name)

        # Redirect user to home page
        return redirect("/login")
    else:
        return render_template("chgpwd.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
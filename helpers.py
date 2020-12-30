import base64  # encode password
import os
import smtplib
import ssl
#import requests
import urllib.parse
from datetime import datetime
from functools import wraps

from flask import redirect, render_template, request, session


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"

def fdate(value):
    """Format date as Day Month Day Year."""
    y = value
    x = datetime.strptime(y, '%Y-%m-%dT%H:%M')
    date = x.strftime("%a %b %d %Y")
    return date

def status_msg(msg, title, code):
    result = {}
    result.update({"message": msg })
    result.update({"title": title })

    return render_template("status.html", code=code, result=result)

def send_notification(players, type):
    port = 465  # For SSL
    smtp_server = "smtp.gmail.com"
    sender_email = "villageclub2020@gmail.com"  # Enter your address
    #password = input("Type your password and press enter: ")
    repr = base64.b64decode(b'U3VtbWVyaW55dnIyMDIw')
    password = repr.decode('utf-8')

    message = """\n       
    Subject: ** NOTE ** Hi there FROM Village CLUB

    This message is to inform you that new %s EVENT is created.
    Please log on to Village CULB http://127.0.0.1:5000/  to register for the EVENT.""" % (type)
    

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        for player in players:
            server.sendmail(sender_email, player["username"], message)
    return

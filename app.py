# Special touch: I made password required to be at least 8 characters, have upper and lower case
# And have a special non alphbetical character.

import os

from cs50 import SQL
from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # Gives symbols of all stocks we have
    # I don't select all at once since i am doing different things to the list
    # and it should be easier this way
    symbols_list = db.execute("SELECT symbol FROM purchase \
                               WHERE id = ? GROUP BY symbol HAVING SUM(number_shares) != 0", session["user_id"])

    # Gives us all the stock numbers
    share_count = db.execute("SELECT SUM(number_shares) FROM purchase WHERE id = ? GROUP BY symbol", session["user_id"])

    # this goes and gets rid of entries with 0 stock
    share_count = [item for item in share_count if item["SUM(number_shares)"] != 0]

    # print(symbol[0]["symbol"])
    name = db.execute("SELECT name FROM purchase WHERE id = ? GROUP BY symbol HAVING SUM(number_shares) != 0", session["user_id"])


    # list where we will put our live prices in usd but string
    live_prices = []

    # this is total vlaue of each of our stocks
    totals = []

    # prices is dict. i is counter to go through the enumerate object in the for loop
    # Here we append the price of each onto the list getting it in the same order as the other lists with companies
    for i, prices in enumerate(symbols_list):
        info = lookup(prices["symbol"])

        # Gives us live prices as string we can make into usd
        live_prices.append(info["price"])

        # This is total value of number of stocks times price
        totals.append(share_count[i]["SUM(number_shares)"] * live_prices[i])

    # gives a list of dict with how much cash we have
    cash_left = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

    # This string calculated here but can't be used to calculate total since its a string
    cash_remaining = usd(cash_left[0]["cash"])

    # Gives us the total value. Our cash plus sum of stocks
    total_value = usd(cash_left[0]["cash"] + sum(totals))

    # We willl use all these variables in the html
    # Style 50 told me to make this one line
    tru = True
    return render_template('index.html', symbol=symbols_list, name=name, share_count=share_count, live_prices=live_prices, value_of_stock=totals, cash_on_hand=cash_remaining, money=total_value, tru=tru)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        # Makes sure you input a symbol
        if not request.form.get("symbol"):
            return apology("Input symbol", 400)

        # this gets input making it into an upper case
        symbol = request.form.get("symbol").upper()

        # Gets info of symbol
        stock = lookup(symbol)

        # Checks if valid symbol
        if not stock:
            return apology("Enter a valid symbol", 400)

        # this gives the name of company for our table
        name = stock["name"]

        # WE get the shares input. Done with excess checks for check50.
        share_number = request.form.get("shares")

        # Checks to see if we inputed a number. Don't know why check 50 wants this as you can't on form
        try:
            shares = float(share_number)

        except:
            return apology("Input a  number", 400)

        # check 50 is making me put in a check to see if it is int
        # But i did that in the html. You can't put in a fraction.
        # The mod checks if it is whole number and the other checks if it is negative
        if shares % 1 != 0 or shares < 1:
            return apology("Input a positive integer", 400)

        # This selects the amount of cash in a list of dict.
        amount = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

        # an int with your cash. Since amount is a dict
        cash = amount[0]["cash"]

        # current price of stock
        price = stock["price"]

        # calculates total cost of transaction, making it negative
        total_cost = -price * shares

        # Checks if you have enough money
        if cash < total_cost:
            return apology("Not enough cash!", 403)

        # variable will show how much cash left, format is to have the 0's show and not get cut
        # WE are adding a negative quantity here
        cash_left = '{:.2f}'.format(round(cash + total_cost, 2))

        # This updates the users cash value
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash_left, session["user_id"])

        # This function gets the date of transaction
        time = datetime.now()

        # adds new row with the data of purchase
        # Style50 told me to only do 3 lines I had 4 before
        db.execute("INSERT INTO purchase \
                    (id, symbol, name, number_shares, purchase_price, total_cost, cash_left, date_time) \
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?)", session["user_id"], symbol, name, shares, price, total_cost, cash_left, time)

        # Redirects to the homepage
        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    # Selects all the data we need
    all = db.execute("SELECT symbol, number_shares, purchase_price, date_time \
                      FROM purchase WHERE id = ?", session["user_id"])

    # Passes in the data to history
    return render_template("history.html", all=all)


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
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        # Gets the inputed symbol
        symbol = request.form.get("symbol")

        # Checks to see if symbol works
        if not lookup(symbol):
            return apology("Invalied Symbol!", 400)

        else:
            # Looks up the stocks info
            stock_info = lookup(symbol)

            # Passes info and the money cost into quoted.html
            return render_template("quoted.html", info=stock_info, money=usd(stock_info["price"]))

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # having all if shouldn't affect run time since we will be directed out
    # Checks to see if is POST
    if request.method == "POST":
        # Stores username input in variable
        username = request.form.get("username")

        # Checks to see if null
        if not username:
            return apology("Input a username", 400)

        # If this returns non null the username is taken so we return apology
        if db.execute("SELECT username FROM users WHERE username = ?", username):
            return apology("Username already taken", 400)

        password = request.form.get("password")
        # Gets password and checks if null
        if not password:
            return apology("Input a password", 400)

        confirmation = request.form.get("confirmation")

        # Checks if passwords match
        if confirmation != password:
            return apology("Passwords must match", 400)

        # Checks if long enough
        if len(password) < 8:
            return apology("Password must be at least 8 characters!", 400)

        # Checks if has both uppper and lower
        if password.islower() or password.isupper():
            return apology("Password must have an uppercase and lowercase!", 400)

        # Checks for special character in password
        # I could add this above but there will be too many conditions in if
        if password.isalpha():
            return apology("Password must contain at least one non alphabetical character!", 400)

        # I pass in the password variable into the hash function to get a hash of it
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, generate_password_hash(password))
        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    # I do this operation here since i use just_symbols in both if and else.
    symbols_list = db.execute("SELECT symbol FROM purchase WHERE id = ? GROUP BY symbol", session["user_id"])
    just_symbols = []

    # This will give a list of only symbols wihtout keys
    for i in range(0, len(symbols_list)):
        just_symbols.append(symbols_list[i]["symbol"])

    if request.method == "POST":
        # Checks if either are null
        symbol = request.form.get("symbol")

        if not symbol:
            return apology("Choose a stock to sell", 403)

        # Said to do this? don't think it is needed.
        if symbol not in just_symbols:
            return apology("You don't own any", 403)

        # type cast to int since its string
        shares = int(request.form.get("shares"))
        if not shares:
            return apology("Choose a number to sell", 403)

        # This will let us see how many shares owned.
        share_count = db.execute("SELECT SUM(number_shares) FROM purchase WHERE id = ? GROUP BY symbol", session["user_id"])

        # Checks to see if they tried to sell too many, looking at the index of the symbol with index method
        if shares > share_count[just_symbols.index(symbol)]["SUM(number_shares)"]:
            return apology("You don't have that many", 400)

        # Will use amount to get
        amount = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

        # current amount of cash
        cash = amount[0]["cash"]

        # Gives us the info of the stock and then the price
        stock = lookup(symbol)
        price = stock["price"]

        # Calculates total cost of the sale
        total_cost = price * shares

        # Gives us cash you now have. We round to 2 digits keeping trailing 0's
        # We are adding a positive value here
        total_new_cash = '{:.2f}'.format(round(cash + total_cost, 2))

        # Updates the cash value
        db.execute("UPDATE users SET cash = ? WHERE id = ?", total_new_cash, session["user_id"])

        # Gets time of transaction
        time = datetime.now()

        # We pass -shares in since it will need to take shares away along with all the other data
        db.execute("INSERT INTO purchase (id, symbol, number_shares, purchase_price, date_time) \
                    VALUES(?, ?, ?, ?, ?)", session["user_id"], symbol, -shares, price, time)

        return redirect("/")

    else:
        # So this is same query from buy could i make this a global variable? It didn't work for me
        # I do it here since we will only need it if get to render the template
        return render_template("sell.html", list_symbols=just_symbols)

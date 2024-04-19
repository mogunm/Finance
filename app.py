import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
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
    # flash to the user they bought the stock 
    flash('Bought!')


    # Get the stocks from database 
    stocks = db.execute("SELECT symbol, SUM(shares) shares_sum FROM transactions WHERE user_id = ? GROUP BY symbol HAVING shares_sum > 0", session['user_id'])

    # getting users current cash ammount 
    cash = float(db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]['cash']) 

    #initialize the overall total
    grand_total = cash 

    # calculate the overall total value of shares plus cash balance 
    for stock in stocks:
        quote = lookup(stock['symbol'])
        stock['price'] = quote['price']
        stock['total'] = stock['price'] * stock['shares_sum']
        grand_total += stock['total']



    return render_template("index.html", stocks=stocks, cash=cash, grand_total=grand_total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # provided stock symbol and shares from user 
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")

        # get stock price and symbol from search  
        quote = lookup(request.form.get("symbol"))

         # getting users current cash ammount 
        cash = float(db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]['cash']) 

        # check if input is blank or symbol does not exist 
        if not symbol or quote is None:
           return apology("Symbol does not Exist or No Symbol Provided", 403)
        
        # check if the number of shares is positive 
        elif not shares.isdigit() or int(shares) < 0:
            return apology("Please Provide Positive Value", 403)
        
        # current price of the stock 
        price = float(quote['price'])

        # total cost of the shares per stock 
        total_cost = price * float(shares)

        # check to see if the total cost is greater than avail cash 
        if total_cost > cash:
            return apology("Cannot afford this amount of shares")
        
        # update the users cash amount in table  
        db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", total_cost, session["user_id"])

        # INsert the transaction into the table
        db.execute("INSERT INTO transactions (symbol, shares, type, price, total, user_id) VALUES (?, ?, ?,  ?, ?, ?)", symbol, int(shares), "Buy", price, total_cost, session['user_id'] )

         # redirect the user to home page
        return redirect("/")
        
    # User reached route via GET 
    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    # query the table for transactions ordered by most recent 
    transactions = db.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY Timestamp DESC", session['user_id'])

    return render_template("history.html", transactions=transactions)


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
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
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
        # check if symbol was provided 
        if not request.form.get("symbol"):
            return apology("Must provide a ticker symbol", 403)
        
        # assigning returned value of lookup(a dict) to quotes variable  
        quotes = lookup(request.form.get("symbol"))

        # redirect to the quoted page to see all the ticket symbols 
        return render_template("quoted.html", quotes=quotes)
    return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

         # grab specific username from the database 
        user = db.execute("SELECT username FROM users WHERE username = ?", request.form.get("username"))

        # Checking to see if the username field is blank or exists 
        if not request.form.get("username") or len(user) == 1:
            return apology("username not provided or User already exists", 403)
        
        # Checking to see if the password field is blank or the password matches 
        elif not request.form.get("password") or request.form.get("password") != request.form.get("confirmation"):
            return apology("Password not provided or Passwords do not match", 403)

        # Insert the users data into the database and redirect to login. 
        db.execute("INSERT INTO users (username, hash) VALUES (?,?)", request.form.get("username"), generate_password_hash(request.form.get("password")))
        return redirect("/login")

    return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # get stocks owned from database
    stocks = db.execute("SELECT symbol, SUM(shares) shares_sum FROM transactions WHERE user_id = ? GROUP BY symbol HAVING shares_sum > 0", session['user_id'])

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        #get stock symbol and shares from user
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")
        
        # check if the user chose a stock
        if not symbol:
            return apology("No stock chosen", 403)
        
        # check if the user owns any shares in stock 
        for stock in stocks:
            
            # check to see if the user owns that many shares or provide positive number
            if symbol == stock['symbol']:
                if int(shares) > int(stock['shares_sum']) or int(shares) < 0:
                    return apology("Not enough shares or Must be positive share input", 403)
                
            # complete the sale
            quote = lookup(symbol)
            price = quote['price']
            total_sale = price * int(shares)

            # update the users table with the new cash from sold shares 
            db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", total_sale, session['user_id'])

            # insert the sale into the transactions table 
            db.execute("INSERT INTO transactions (symbol, shares, type, price, total, user_id) VALUES (?, ?, ?,  ?, ?, ?)", symbol, -int(shares), "Sell", price, total_sale, session['user_id'] )

        # redirect to home page
            return redirect("/")
            
    return render_template("sell.html", stocks=stocks)
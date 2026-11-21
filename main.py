from flask import Flask , render_template, request, redirect, url_for, flash , jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import engine
from initialize_db.models import users , products , account
from app_config import app , jwt , redis_client
from flask_jwt_extended import (
    create_access_token , set_access_cookies , jwt_required,
    unset_jwt_cookies  , get_jwt, get_jwt_identity)
import time , json
from decimal import Decimal, InvalidOperation

@app.route("/")
@jwt_required(optional=True)
def home():
    user_id = get_jwt_identity()
    return render_template("index.html", logged_in=user_id is not None)

@app.route("/orders")
@jwt_required()
def my_orders():

    return render_template("orders.html")

@app.route("/wallet" , methods = ['GET'])
@jwt_required()
def wallet_page():
    return render_template("wallet.html")

@app.route("/api/wallet" , methods = ['GET'])
@jwt_required()
def get_wallet():
    user_id = get_jwt_identity()

    from sqlalchemy import select
    stmt = select(
        account.c.balance
    ).where(account.c.user_id == int(user_id))

    with engine.begin() as connection:
        amount = connection.execute(stmt).scalar_one_or_none()


    if amount is None:
        return jsonify(error="Wallet account not found"), 404

    return jsonify({
        "balance" : str(amount),
        "currency" : "INR"
    })

@app.route("/api/wallet/deposits" , methods = ['POST'])
@jwt_required()
def add_funds():
    data = request.get_json()

    amount = data["amount"]

    try:
        amount = Decimal(str(data["amount"]))
    except (KeyError, InvalidOperation, TypeError, ValueError):
        return jsonify(error="Amount must be a valid decimal"), 400

    if not amount.is_finite() or amount <= 0:
        return jsonify(error="Amount must be greater than zero"), 400

    user_id = get_jwt_identity()
    from sqlalchemy import select, update

    update_stmt = update(
        account
        ).where(account.c.user_id == int(user_id)
        ).values(balance=account.c.balance + amount).returning(account.c.balance)

    with engine.begin() as connection:
        newBalance = connection.execute(update_stmt).scalar_one_or_none()

    return jsonify({
        "message": "Practice funds added successfully.",
        "balance": str(newBalance),
        "currency": "INR"
        })

@app.route('/api/products' , methods = ['GET'])
def get_list():

    page = int(request.args.get("page" , "1"))
    page_size = int(request.args.get("page_size" , "12"))
    category = request.args.get("category" , "All")

    if page < 1:
        return "Invalide page number."
    
    page_size = min(page_size , 12)

    allowed_categories = {
        "All",
        "Electronics",
        "Home",
        "Stationery",
        "Accessories",
    }


    if category not in allowed_categories:
        return "Invalid category or category does not exists."
    from sqlalchemy import select , func

    cnt_stmt = select(func.count()).select_from(products)

    if category != "All":
        cnt_stmt = select(func.count()).select_from(products).where(products.c.category == category)

    with engine.begin() as connection:
            total_items = connection.execute(cnt_stmt).scalar_one()

    total_pages = max(1 , (total_items + page_size-1) // page_size )
    page = min(total_pages , page)
    offset = (page - 1) * page_size

    product_stmt = select(
                products.c.product_id,
                products.c.product_name,
                products.c.category,
                products.c.price,
                products.c.stock_quantity, 
            ).where(
            ).order_by(products.c.product_id
            ).limit(page_size
            ).offset(offset)

    if category != "All":
        product_stmt = select(
            products.c.product_id,
            products.c.product_name,
            products.c.category,
            products.c.price,
            products.c.stock_quantity, 
        ).where(products.c.category == category
        ).order_by(products.c.product_id
        ).limit(page_size
        ).offset(offset)

    with engine.begin() as connection:
        rows = connection.execute(product_stmt).mappings().all()

    items = [
        {
            "product_id" : row["product_id"],
            "product_name": row["product_name"],
            "category": row["category"],
            "price": str(row["price"]),
            "stock_quantity": row["stock_quantity"],
        }
        for row in rows
    ]

    return jsonify(
        items=items,
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        )


    
# Login , singup , logout

@app.route('/login' , methods = ['GET' , 'POST'])
def login():

    if request.method == 'POST':
        from sqlalchemy import select
        email = request.form.get("email").strip().lower()
        password = request.form.get("password")

        stmt = (
            select(users.c.id , 
                   users.c.password_hash,
                   users.c.role)
            .where(users.c.email == email)
        )

        try:
            with engine.begin() as connection:
                user = connection.execute(statement=stmt).mappings().one_or_none()

            if user is None or not check_password_hash(user["password_hash"], password):
                flash("Email or password is incorrect.", "error")
                return redirect(url_for("login"))
            else:
                access_token = create_access_token(identity=str(user["id"]))
                flash("Welcome back.", "success")
                response = redirect(url_for("home"))
                set_access_cookies(response , access_token)
                return response
                       
        except Exception:
            app.logger.exception("Login failed")
            flash("We couldn't sign you in right now. Please try again.", "error")
            return redirect(url_for("login"))
        
    return render_template("login.html")


@app.route('/signup' , methods = ['GET' , 'POST'])
def signup():

    if request.method == 'POST':
        
        from sqlalchemy import insert

        stmt = (
            insert(users)
            .values(
                name=request.form.get("name").strip().lower(),
                email=request.form.get("email").strip().lower(),
                password_hash=generate_password_hash(
                    request.form.get("password")
                )
            ).returning(users.c.id)
        )

        

        try:
            with engine.begin() as connection:
                user_id = connection.execute(statement=stmt).scalar_one()
                connection.execute(insert(account).values(user_id=user_id))

            access_token = create_access_token(identity=str(user_id))
            flash("Your account was created successfully.", "success")
            response =  redirect(url_for("home"))
            set_access_cookies(response , access_token)
            return response

        except Exception:
            app.logger.exception("Signup failed")
            flash("We couldn't create your account. Check your details and try again.", "error")
            return redirect(url_for("signup"))

    return render_template("signup.html")

@app.route("/logout" , methods = ['POST'])
@jwt_required()
def logout():
    token =  get_jwt()

    ttl = max(1 , int(token["exp"] - time.time()) + 1)
    redis_client.set(f"revoked:{token['jti']}" , 1 , ex=ttl)
    response = redirect(url_for("home"))
    unset_jwt_cookies(response)
    flash("You have been logged out.", "success")
    return response

if __name__ == "__main__":
    print("listening..")
    app.run(port=5000)


from flask import Flask , render_template, request, redirect, url_for, flash , jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import engine
from initialize_db.models import users , products , account , order_items , orders
from app_config import app , jwt , redis_client
from flask_jwt_extended import (
    create_access_token , set_access_cookies , jwt_required,
    unset_jwt_cookies  , get_jwt, get_jwt_identity)
import time , json
from decimal import Decimal, InvalidOperation

# =====================================================
# Helping functions
# =====================================================
def authorizeUser(user_id : int):
    from sqlalchemy import select
    stmt = select(users.c.role).where(users.c.id == user_id)

    with engine.begin() as connection:
        role = connection.execute(stmt).scalar_one_or_none()

    if role != 'admin':
        return 0
    
    return 1

def get_page_data(page:int , page_size:int , category:str):
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



@app.route("/")
@jwt_required(optional=True)
def home():
    user_id = get_jwt_identity()
    is_admin = bool(user_id is not None and authorizeUser(int(user_id)))
    return render_template("index.html", logged_in=user_id is not None, is_admin=is_admin)

@app.route("/orders")
@jwt_required()
def my_orders():
    is_admin = bool(authorizeUser(int(get_jwt_identity())))
    return render_template("orders.html", is_admin=is_admin)

#GET /api/cart
@app.route("/api/cart" , methods = ['GET'])
@jwt_required()
def get_cart_items():

    user_id = int(get_jwt_identity())

    from sqlalchemy import select

    stmt = select(
        orders.c.order_id,
        order_items.c.quantity,
        order_items.c.unit_price,
        products.c.product_id,
        products.c.product_name,
        products.c.category
    ).select_from(
        orders
    ).join(
        order_items,
        orders.c.order_id == order_items.c.order_id
    ).join(
        products,
        order_items.c.product_id == products.c.product_id
    ).where(
        orders.c.user_id == user_id,
        orders.c.status == "cart"
    )

    bal_stmt = select(
        account.c.balance
    ).select_from(
        account
    ).where(account.c.user_id == user_id)

    with engine.begin() as connection:
        rows = connection.execute(stmt).mappings().all()
        userBalance = connection.execute(bal_stmt).scalar_one_or_none()

    items = [
        {
        "order_id": row["order_id"],
        "product_name" : row["product_name"],
        "product_id" : row["product_id"],
        "quantity" : row["quantity"],
        "unit_price" : row["unit_price"],
        "category" : row["category"]
     } for row in rows
    ]

    total_amount = 0

    for item in items:
        total_amount += Decimal((item["unit_price"] * item["quantity"]))

    return jsonify({
        "items" : items,
        "total_amount" : str(total_amount),
        "balance" : str(userBalance)
    })

#POST /api/cart/items

@app.route("/api/cart/items" , methods = ['POST'])
@jwt_required()
def add_items():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("items"), list) or not data["items"]:
        return jsonify(error="items must be a non-empty list"), 400

    requested_items = []
    seen_product_ids = set()
    for item in data["items"]:
        if not isinstance(item, dict):
            return jsonify(error="Each item must include product_id and quantity"), 400

        try:
            raw_product_id = item["product_id"]
            raw_quantity = item["quantity"]
            product_id = int(raw_product_id)
            quantity = int(raw_quantity)
        except (KeyError, TypeError, ValueError):
            return jsonify(error="product_id and quantity must be integers"), 400

        if isinstance(raw_product_id, bool) or str(raw_product_id).strip() != str(product_id):
            return jsonify(error="product_id must be a whole number"), 400
        if isinstance(raw_quantity, bool) or str(raw_quantity).strip() != str(quantity):
            return jsonify(error="quantity must be a whole number"), 400
        if product_id < 1 or quantity < 1:
            return jsonify(error="product_id and quantity must be positive"), 400
        if product_id in seen_product_ids:
            return jsonify(error="Each product may appear only once"), 400

        seen_product_ids.add(product_id)
        requested_items.append({"product_id": product_id, "quantity": quantity})

    user_id = int(get_jwt_identity())
    from sqlalchemy import insert, select

    try:
        with engine.begin() as connection:
            product_rows = connection.execute(
                select(
                    products.c.product_id,
                    products.c.price,
                    products.c.stock_quantity,
                )
                .where(products.c.product_id.in_(seen_product_ids))
                .order_by(products.c.product_id)
            ).mappings().all()
            product_by_id = {row["product_id"]: row for row in product_rows}
            missing_ids = [product_id for product_id in seen_product_ids if product_id not in product_by_id]
            if missing_ids:
                return jsonify(error="One or more products were not found", product_ids=missing_ids), 404

            for item in requested_items:
                product = product_by_id[item["product_id"]]
                if item["quantity"] > product["stock_quantity"]:
                    return jsonify(
                        error=f"Not enough stock for product {item['product_id']}",
                        product_id=item["product_id"],
                        available_stock=product["stock_quantity"],
                    ), 409

            order_id = connection.execute(
                insert(orders)
                .values(user_id=user_id, status="cart")
                .returning(orders.c.order_id)
            ).scalar_one()

            order_item_rows = [
                {
                    "order_id": order_id,
                    "product_id": item["product_id"],
                    "quantity": item["quantity"],
                    "unit_price": product_by_id[item["product_id"]]["price"],
                }
                for item in requested_items
            ]
            connection.execute(insert(order_items), order_item_rows)

        return jsonify(message="Cart created successfully", order_id=order_id), 201
    except Exception:
        app.logger.exception("Could not create cart order")
        return jsonify(error="Could not create cart order"), 500

#PATCH /api/cart/items/<product_id>

@app.route("/api/orders/<order_id>/items/<product_id>" , methods = ['PATCH'])
@jwt_required()
def update_quantity(product_id , order_id):

    user_id = int(get_jwt_identity())
    new_quantity = request.get_json()

    if product_id is None or new_quantity is None:
        return jsonify({"quantity"  : "Invalid"})

    from sqlalchemy import update

    stmt = update(order_items
            ).values(quantity = int(new_quantity["quantity"])
            ).where(order_items.c.product_id == int(product_id),
                 order_items.c.order_id == int(order_id)
            ).returning(order_items.c.quantity)

    try:
        with engine.begin() as connection:
            qt = connection.execute(stmt).scalar_one_or_none()

    except Exception as e:
        return jsonify({"quantity"  : str(e)})

    return jsonify({"quantity" : str(qt)})

# DELETE /api/orders/<order_id>/items/<product_id>

@app.route("/api/orders/<order_id>/items/<product_id>" , methods = ['DELETE'])
@jwt_required()
def delete_item(order_id , product_id):

    from sqlalchemy import delete

    stmt = delete(order_items
            ).where(order_items.c.product_id == int(product_id),
                    order_items.c.order_id == int(order_id))

    try:
        with engine.begin() as connection:
            connection.execute(stmt)

        return jsonify({"message" : "Success"})

    except Exception as e:

        return jsonify({"message" : str(e)})

@app.route("/api/orders/checkout" , methods = ['POST'])
@jwt_required()
def check_out():
    from sqlalchemy import select, update

    try:
        data = request.get_json()
        user_id = int(get_jwt_identity())
        total_amount = Decimal(str(data["total_amount"]))
        items = data["items"]
        order_ids = {int(item["order_id"]) for item in items}
        order_id = min(order_ids)

        with engine.begin() as connection:
            balance = connection.execute(
                select(account.c.balance)
                .where(account.c.user_id == user_id)
                .with_for_update()
            ).scalar_one()

            if total_amount > balance:
                return jsonify(error="Insufficient wallet balance"), 409

            connection.execute(
                update(orders)
                .where(
                    orders.c.order_id.in_(order_ids),
                    orders.c.user_id == user_id,
                    orders.c.status == "cart",
                )
                .values(status="paid")
            )

            connection.execute(
                update(account)
                .where(account.c.user_id == user_id)
                .values(balance=account.c.balance - total_amount)
            )

            for item in items:
                connection.execute(
                    update(products)
                    .where(products.c.product_id == int(item["product_id"]))
                    .values(
                        stock_quantity=(
                            products.c.stock_quantity - int(item["quantity"])
                        )
                    )
                    .returning(products.c.product_id)
                ).scalar_one()

        return jsonify(
            message="Order placed successfully",
            order_id=order_id,
            order_ids=sorted(order_ids),
            total_amount=str(total_amount),
        ), 200
    except Exception as e:
        app.logger.exception("Checkout failed")
        return jsonify(error=str(e)), 500

@app.route("/api/orders/paid", methods=["GET"])
@jwt_required()
def get_paid_orders():
    user_id = int(get_jwt_identity())
    from sqlalchemy import select

    stmt = (
        select(
            orders.c.order_id,
            orders.c.created_at,
            order_items.c.product_id,
            products.c.product_name,
            order_items.c.quantity,
            order_items.c.unit_price,
        )
        .select_from(orders)
        .join(order_items, orders.c.order_id == order_items.c.order_id)
        .join(products, order_items.c.product_id == products.c.product_id)
        .where(
            orders.c.user_id == user_id,
            orders.c.status == "paid",
        )
        .order_by(orders.c.created_at.desc(), orders.c.order_id.desc())
    )

    with engine.connect() as connection:
        rows = connection.execute(stmt).mappings().all()

    paid_orders = {}
    for row in rows:
        order_id = row["order_id"]
        order = paid_orders.setdefault(
            order_id,
            {
                "order_id": order_id,
                "created_at": row["created_at"].isoformat(),
                "items": [],
                "total_amount": Decimal("0.00"),
            },
        )
        line_total = row["unit_price"] * row["quantity"]
        order["items"].append(
            {
                "product_id": row["product_id"],
                "product_name": row["product_name"],
                "quantity": row["quantity"],
                "unit_price": str(row["unit_price"]),
                "line_total": str(line_total),
            }
        )
        order["total_amount"] += line_total

    return jsonify(
        orders=[
            {**order, "total_amount": str(order["total_amount"])}
            for order in paid_orders.values()
        ]
    )

@app.route("/wallet" , methods = ['GET'])
@jwt_required()
def wallet_page():
    is_admin = bool(authorizeUser(int(get_jwt_identity())))
    return render_template("wallet.html", is_admin=is_admin)

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

    return get_page_data(page=page , page_size=page_size , category=category)

# GET /inventory

@app.route("/inventory" , methods = ['GET'])
@jwt_required()
def inventory():
    user_id = int(get_jwt_identity())
    result = authorizeUser(user_id=user_id)

    if result == 0:
        flash("Unauthorized access" , 401)
        return redirect(url_for("login"))

    return render_template("inventory.html", is_admin=True)

# GET /api/admin/products

@app.route("/api/admin/products" , methods = ['GET'])
@jwt_required()
def get_products_admin():
    user_id = int(get_jwt_identity())
    result = authorizeUser(user_id=user_id)

    if result == 0:
        flash("Unauthorized access" , 401)
        return redirect(url_for("login"))

    page = int(request.args.get("page" , "1"))
    page_size = int(request.args.get("page_size" , "12"))
    category = request.args.get("category" , "All")
    
    return get_page_data(page=page , page_size=page_size , category=category)

# PATCH /api/admin/products/<product_id>

@app.route('/api/admin/products/<product_id>' , methods = ['PATCH'])
@jwt_required()
def update_products(product_id):

    user_id = int(get_jwt_identity())

    result = authorizeUser(user_id=user_id)
    if result == 0:
        flash("Unauthorized access" , 401)
        return redirect(url_for("login"))

    product_id = int(product_id)

    required_changes = request.get_json()

    # {"price":"125.00","stock_quantity":10}

    from sqlalchemy import update

    price = Decimal(required_changes["price"])
    stock_quantity = int(required_changes["stock_quantity"])

    stmt = update(products
            ).values(price = price ,
                    stock_quantity = stock_quantity
                    ).where(products.c.product_id == product_id)

    try:
        with engine.begin() as connection:
            connection.execute(stmt)

            return jsonify({"message":"Product updated",
                            "product":{"price":price,
                                    "stock_quantity":stock_quantity}})
        
    except Exception as e:

        return jsonify({"message" : str(e)})

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


from flask import Flask , render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database import engine
from initialize_db.models import users
from app_config import app , jwt , redis_client
from flask_jwt_extended import (
    create_access_token , set_access_cookies , jwt_required,
    unset_jwt_cookies  , get_jwt, get_jwt_identity)
import time


@app.route('/')
@jwt_required(optional=True)
def home():
    user_id = get_jwt_identity()
    return render_template("index.html", logged_in=user_id is not None)

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


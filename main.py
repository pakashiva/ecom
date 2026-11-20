from flask import Flask , render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from database import engine
from initialize_db.models import users
from app_config import app , jwt
from flask_jwt_extended import create_access_token , set_access_cookies

@app.route('/')
def home():
    return render_template("index.html")

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
                return "Invalid credentials or user does not exists"
            else:
                access_token = create_access_token(identity=str(user["id"]))
                response = redirect(url_for("home"))
                set_access_cookies(response , access_token)
                return response
                       
        except Exception as e:
            return f"Error Occured {str(e)}"
        
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
            response =  redirect(url_for("home"))
            set_access_cookies(response , access_token)
            return response

        except Exception as e:
            return f"Error Occured {str(e)}"

    return render_template("signup.html")

@app.route("/logout")
def logout():
    return "1"

if __name__ == "__main__":
    print("listening..")
    app.run(port=5000)


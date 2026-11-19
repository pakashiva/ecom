from flask import Flask , render_template, request, redirect, url_for
from sqlalchemy import URL , create_engine , text
from dotenv import load_dotenv
import os
app = Flask(__name__)

load_dotenv(override=True)

@app.route('/')
def home():
    return render_template("index.html")

print("Password loaded:", bool(os.environ.get("DBPASSWORD")))


database_url = URL.create(
    drivername="postgresql+psycopg",
    database="ecom",
    host="127.0.0.1",
    port=5432,
    username="shiva",
    password= os.getenv("DBPASSWORD")
)

engine = create_engine(
    database_url,
    pool_size=7,
    pool_recycle=1800,
    pool_pre_ping=True,
    max_overflow=3
    )


with engine.connect() as connection:
    print(connection.execute(
        text("SELECT current_user, current_database()")
    ).fetchone())


if __name__ == "__main__":
    print("listening..")
    app.run(port=5000)


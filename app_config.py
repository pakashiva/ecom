from flask import Flask
from flask_jwt_extended import JWTManager
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.config.update(
    JWT_SECRET_KEY=os.environ["JWT_SECRET_KEY"],
    JWT_TOKEN_LOCATION=["cookies"],
    JWT_COOKIE_SECURE=False,
    JWT_COOKIE_SAMESITE="Lax",
    JWT_COOKIE_CSRF_PROTECT=True,
    JWT_CSRF_CHECK_FORM=True,
    JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=15),
)

jwt = JWTManager(app)
